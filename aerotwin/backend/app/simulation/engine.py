"""
Engine Model — Master Engine Simulator
Integrates combustion, cooling, lubrication, turbo, and vibration subsystems.
This is the "actual engine" that produces physical truth values.

Physics-informed demonstrator model — NOT an exact DRDO engine model.
"""
import numpy as np
from typing import Optional

from .combustion import CombustionModel
from .cooling import CoolingModel
from .lubrication import LubricationModel
from .turbo import TurboModel
from .vibration import VibrationModel
from .environment import FlightEnvironment
from ..schemas.engine import EngineState, CylinderState
from ..config import EngineConfig


class EngineModel:
    """
    Master engine model that propagates physics through subsystems:
    
    Throttle → Airflow → F/A → Combustion → Torque + EGT + CHT → RPM
    RPM + Load → Oil System → Oil Pressure + Temperature
    RPM + Exhaust → Turbo → Boost → MAP → Air mass
    All → Vibration
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        if config is None:
            config = EngineConfig()
        
        self.config = config
        self.num_cylinders = config.num_cylinders
        
        # Subsystem models
        self.combustion = CombustionModel(
            num_cylinders=config.num_cylinders,
            displacement_cc=config.displacement_cc,
            compression_ratio=config.compression_ratio,
        )
        self.cooling = CoolingModel(num_cylinders=config.num_cylinders)
        self.lubrication = LubricationModel()
        self.turbo = TurboModel(max_boost_psi=config.turbo_max_boost_psi)
        self.vibration_model = VibrationModel(num_cylinders=config.num_cylinders)
        
        # Engine state
        self.rpm = config.idle_rpm
        self.throttle = 0.0
        self.bus_voltage = 28.0
        self.alternator_load = 30.0
        
        # RPM dynamics
        self.moment_of_inertia = 0.5  # kg·m² (flywheel + prop)
        self.prop_load_coefficient = 0.0003  # propeller drag coefficient
        self.idle_fuel = True  # idle fuel enrichment active
        
        # Fuel
        self.fuel_remaining_gal = 50.0
        self.fuel_consumed_gal = 0.0
        
        # Timestamp
        self.time = 0.0

    def step(self, dt: float, throttle: float, environment: FlightEnvironment) -> EngineState:
        """
        Advance the engine model by dt seconds.
        
        This is the main physics propagation:
        1. Turbo → boost
        2. Combustion → torque, EGT, CHT inputs
        3. RPM dynamics
        4. Cooling → CHT
        5. Lubrication → oil
        6. Vibration
        7. Electrical
        """
        self.time += dt
        self.throttle = np.clip(throttle, 0.0, 1.0)
        
        # 1. Turbocharger
        exhaust_energy = self.rpm / 5800.0 * self.throttle
        turbo_result = self.turbo.update(
            dt=dt,
            engine_rpm=self.rpm,
            exhaust_energy=exhaust_energy,
            altitude_ft=environment.altitude_ft,
            throttle=self.throttle,
            ambient_pressure_inhg=environment.ambient_pressure_inhg,
        )
        turbo_boost = turbo_result["turbo_boost_psi"]
        
        # 2. Manifold pressure
        map_inhg = self.turbo.get_manifold_pressure(environment.ambient_pressure_inhg)
        # Throttle modulates MAP
        map_inhg = map_inhg * (0.3 + 0.7 * self.throttle)
        
        # 3. Combustion
        comb_result = self.combustion.compute(
            throttle=self.throttle,
            rpm=self.rpm,
            map_inhg=map_inhg,
            ambient_temp_c=environment.ambient_temp_c,
            ambient_pressure_inhg=environment.ambient_pressure_inhg,
            density_ratio=environment.density_ratio,
            turbo_boost_psi=turbo_boost,
        )
        
        # 4. RPM dynamics
        # Constant-speed propeller governor tracks throttle demand with rotational inertia
        engine_torque = comb_result["total_torque_nm"]
        nominal_torque = 140.0 * (0.3 + 0.7 * self.throttle)
        torque_ratio = np.clip(engine_torque / max(nominal_torque, 1e-3), 0.2, 1.2)
        target_rpm = (self.config.idle_rpm + self.throttle * (self.config.max_rpm - self.config.idle_rpm)) * torque_ratio
        
        # Exponential filter for unconditionally stable integration across any dt
        tau = 0.8  # governor time constant in seconds
        filter_alpha = 1.0 - float(np.exp(-dt / tau))
        self.rpm += filter_alpha * (target_rpm - self.rpm)
        
        # Idle RPM floor (governor prevents stall when fuel is available)
        if self.fuel_remaining_gal > 0:
            self.rpm = max(self.rpm, self.config.idle_rpm)
            
        # RPM upper limit
        self.rpm = float(np.clip(self.rpm, 0.0, self.config.max_rpm * 1.05))
        
        # 5. Cooling
        # Airspeed factor for cooling: more RPM or higher flight speed = more cooling
        airspeed_factor = 0.5 + 0.3 * (self.rpm / self.config.max_rpm) + 0.2 * min(1.0, environment.altitude_ft / 15000.0)
        
        cht_values = self.cooling.update(
            dt=dt,
            cyl_heat_inputs=comb_result["cyl_chts"],
            ambient_temp_c=environment.ambient_temp_c,
            airspeed_factor=airspeed_factor,
        )
        
        # 6. Lubrication
        oil_result = self.lubrication.update(
            dt=dt,
            rpm=self.rpm,
            power_hp=comb_result["power_hp"],
            ambient_temp_c=environment.ambient_temp_c,
        )
        
        # Bearing stress affects vibration
        bearing_stress = self.lubrication.get_bearing_stress()
        
        # 7. Vibration
        vib_result = self.vibration_model.update(
            rpm=self.rpm,
            cyl_efficiencies=comb_result["cyl_efficiencies"],
            oil_pressure_psi=oil_result["oil_pressure_psi"],
            bearing_stress=bearing_stress,
        )
        
        # 8. Electrical system
        # Alternator output proportional to RPM
        rpm_factor = self.rpm / self.config.max_rpm
        self.bus_voltage = 26.0 + 3.0 * rpm_factor  # 26-29V range
        self.bus_voltage = np.clip(self.bus_voltage, 22.0, 29.5)
        
        # 9. Fuel consumption
        fuel_flow_gph = comb_result["fuel_flow_gph"]
        fuel_consumed_step = fuel_flow_gph * (dt / 3600.0)  # gallons this step
        self.fuel_consumed_gal += fuel_consumed_step
        self.fuel_remaining_gal -= fuel_consumed_step
        self.fuel_remaining_gal = max(0.0, self.fuel_remaining_gal)
        
        # Build engine state
        cylinders = []
        for i in range(self.num_cylinders):
            cylinders.append(CylinderState(
                cylinder_id=i + 1,
                egt_c=comb_result["cyl_egts"][i],
                cht_c=cht_values[i],
                combustion_efficiency=comb_result["cyl_efficiencies"][i],
                fuel_air_ratio=comb_result["cyl_fuel_air_ratios"][i],
                mixture_quality=comb_result["cyl_efficiencies"][i],
                cooling_effectiveness=self.cooling.cooling_health[i],
                misfire_probability=0.0,
            ))
        
        # Thermal margin
        max_cht = max(cht_values) if cht_values else 180.0
        thermal_margin = self.cooling.cht_redline - max_cht
        
        state = EngineState(
            timestamp=self.time,
            rpm=round(self.rpm, 1),
            throttle=self.throttle,
            manifold_pressure_inhg=round(map_inhg, 2),
            torque_nm=round(engine_torque, 2),
            power_hp=round(comb_result["power_hp"], 2),
            air_mass_flow_gs=round(comb_result["air_mass_flow_gs"], 2),
            volumetric_efficiency=round(comb_result["volumetric_efficiency"], 3),
            fuel_flow_gph=round(fuel_flow_gph, 2),
            fuel_air_ratio=comb_result["fuel_air_ratio"],
            cylinders=cylinders,
            mean_egt_c=round(float(np.mean(comb_result["cyl_egts"])), 1),
            mean_cht_c=round(float(np.mean(cht_values)), 1),
            oil_pressure_psi=oil_result["oil_pressure_psi"],
            oil_temperature_c=oil_result["oil_temperature_c"],
            oil_viscosity_factor=oil_result["oil_viscosity_factor"],
            turbo_boost_psi=turbo_result["turbo_boost_psi"],
            turbo_rpm=turbo_result["turbo_rpm"],
            turbo_efficiency=turbo_result["turbo_efficiency"],
            vibration_g=vib_result["vibration_g"],
            vibration_dominant_freq_hz=vib_result["dominant_freq_hz"],
            bus_voltage=round(self.bus_voltage, 2),
            alternator_output_a=round(self.alternator_load * rpm_factor, 1),
            specific_fuel_consumption=round(
                fuel_flow_gph / max(comb_result["power_hp"], 0.1) * 2.72, 3  # kg/hp·hr
            ) if comb_result["power_hp"] > 1 else 0.0,
            thermal_margin_c=round(thermal_margin, 1),
        )
        
        return state

    def reset(self):
        """Reset engine to initial conditions."""
        self.rpm = self.config.idle_rpm
        self.throttle = 0.0
        self.bus_voltage = 28.0
        self.fuel_remaining_gal = 50.0
        self.fuel_consumed_gal = 0.0
        self.time = 0.0
        self.combustion.reset()
        self.cooling.reset()
        self.lubrication.reset()
        self.turbo.reset()
        self.vibration_model.reset()
