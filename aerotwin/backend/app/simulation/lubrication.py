"""
Lubrication System Model
Models oil pressure and temperature as functions of RPM, load, temperature, and health.
Oil pressure loss propagates to bearing wear and vibration.
"""
import numpy as np


class LubricationModel:
    """
    Simplified oil system model:
    - Oil pressure driven by oil pump (RPM-dependent) minus leakage/wear
    - Oil temperature driven by heat absorption and oil cooler
    - Oil viscosity varies with temperature
    """

    def __init__(self):
        # Normal operating ranges
        self.nominal_pressure_psi = 60.0
        self.min_pressure_psi = 25.0
        self.max_pressure_psi = 90.0
        self.nominal_temp_c = 80.0
        self.max_temp_c = 130.0
        
        # Current state
        self.oil_pressure_psi = 60.0
        self.oil_temperature_c = 80.0
        self.oil_viscosity_factor = 1.0  # 1.0 = normal
        
        # Health factors
        self.pump_efficiency = 1.0  # degraded pump delivers less pressure
        self.leakage_rate = 0.0  # 0 = no leak, 1 = catastrophic
        self.cooler_efficiency = 1.0
        self.oil_quality = 1.0  # degrades over time

    def update(self, dt: float, rpm: float, power_hp: float,
               ambient_temp_c: float) -> dict:
        """
        Update oil system state.
        
        Oil pressure model:
            P_oil = P_pump(RPM) * pump_health - leakage - viscosity_correction
        
        Oil temperature model:
            Absorbs heat from engine, rejects heat through cooler.
        """
        # Oil pump output (pressure proportional to RPM)
        rpm_norm = rpm / 5800.0
        pump_pressure = self.nominal_pressure_psi * (0.3 + 0.7 * rpm_norm) * self.pump_efficiency
        
        # Pressure loss from leakage
        leak_loss = self.leakage_rate * 40.0  # up to 40 psi loss at full leak
        
        # Viscosity effect on pressure (hot oil = lower viscosity = lower pressure)
        temp_excess = max(0, self.oil_temperature_c - 90.0)
        viscosity_pressure_loss = temp_excess * 0.15
        
        # Target oil pressure
        target_pressure = pump_pressure - leak_loss - viscosity_pressure_loss
        target_pressure = np.clip(target_pressure, 0.0, self.max_pressure_psi)
        
        # Smooth approach to target
        tau_pressure = 1.0  # seconds (hydraulic response)
        alpha = 1.0 - np.exp(-dt / tau_pressure)
        self.oil_pressure_psi += alpha * (target_pressure - self.oil_pressure_psi)
        
        # Oil temperature model
        # Heat input from engine (proportional to power)
        heat_input_rate = power_hp * 0.15  # °C/s equivalent, ~15% of power heats oil
        
        # Heat rejection from oil cooler
        oil_to_ambient_delta = self.oil_temperature_c - ambient_temp_c
        heat_rejection = oil_to_ambient_delta * 0.08 * self.cooler_efficiency  # °C/s
        
        # Net temperature change
        net_heating = (heat_input_rate - heat_rejection) * 0.02  # scale factor
        
        target_temp = self.nominal_temp_c + net_heating * 30.0  # offset from nominal
        target_temp = np.clip(target_temp, ambient_temp_c + 10, self.max_temp_c + 20)
        
        tau_temp = 30.0  # thermal lag (seconds)
        alpha_t = 1.0 - np.exp(-dt / tau_temp)
        self.oil_temperature_c += alpha_t * (target_temp - self.oil_temperature_c)
        
        # Viscosity factor (decreases with temperature)
        self.oil_viscosity_factor = 1.0 - 0.005 * max(0, self.oil_temperature_c - 80.0)
        self.oil_viscosity_factor = np.clip(self.oil_viscosity_factor, 0.3, 1.2)
        
        return {
            "oil_pressure_psi": round(self.oil_pressure_psi, 2),
            "oil_temperature_c": round(self.oil_temperature_c, 2),
            "oil_viscosity_factor": round(self.oil_viscosity_factor, 3),
            "pump_efficiency": self.pump_efficiency,
            "leakage_rate": self.leakage_rate,
        }

    def set_pump_efficiency(self, efficiency: float):
        """Degrade oil pump (for fault injection)."""
        self.pump_efficiency = np.clip(efficiency, 0.0, 1.0)

    def set_leakage_rate(self, rate: float):
        """Set oil leakage rate (0-1)."""
        self.leakage_rate = np.clip(rate, 0.0, 1.0)

    def set_cooler_efficiency(self, efficiency: float):
        self.cooler_efficiency = np.clip(efficiency, 0.0, 1.0)

    def get_bearing_stress(self) -> float:
        """
        Bearing stress increases when oil pressure is low.
        Returns 0-1 where 1 = extreme bearing stress.
        """
        if self.oil_pressure_psi < self.min_pressure_psi:
            stress = 1.0 - (self.oil_pressure_psi / self.min_pressure_psi)
            return min(stress, 1.0)
        return 0.0

    def reset(self):
        self.oil_pressure_psi = 60.0
        self.oil_temperature_c = 80.0
        self.oil_viscosity_factor = 1.0
        self.pump_efficiency = 1.0
        self.leakage_rate = 0.0
        self.cooler_efficiency = 1.0
        self.oil_quality = 1.0
