"""
Combustion Model
Physics-informed demonstrator model for aero piston engine combustion.
Models the relationship: Throttle → Airflow → F/A Ratio → Combustion → Torque + EGT + CHT

NOT an exact DRDO engine model. Simplified for prototype demonstration.
"""
import numpy as np
from typing import Optional


class CombustionModel:
    """
    Models combustion per cylinder including:
    - Air mass flow based on throttle, MAP, RPM, volumetric efficiency
    - Fuel injection and mixture ratio
    - Combustion efficiency and thermal output
    - Per-cylinder EGT and CHT
    """

    # Constants
    R_AIR = 287.05  # J/(kg·K)
    GAMMA = 1.4
    LHV_AVGAS = 43.5e6  # J/kg lower heating value of avgas
    CP_EXHAUST = 1100.0  # J/(kg·K)
    STOICH_AFR = 14.7

    def __init__(self, num_cylinders: int = 4, displacement_cc: float = 1211.0,
                 compression_ratio: float = 9.0):
        self.num_cylinders = num_cylinders
        self.displacement_per_cyl_m3 = (displacement_cc / num_cylinders) * 1e-6
        self.compression_ratio = compression_ratio
        self.total_displacement_m3 = displacement_cc * 1e-6

        # Per-cylinder state
        self.cylinder_efficiency = np.ones(num_cylinders)
        self.cylinder_mixture_offset = np.zeros(num_cylinders)  # F/A ratio offset per cyl
        self.cylinder_cooling_factor = np.ones(num_cylinders)  # cooling effectiveness

    def compute(self, throttle: float, rpm: float, map_inhg: float,
                ambient_temp_c: float, ambient_pressure_inhg: float,
                density_ratio: float, turbo_boost_psi: float = 0.0) -> dict:
        """
        Compute combustion parameters for all cylinders.
        
        Returns dict with per-cylinder and aggregate combustion results.
        """
        # Effective MAP includes turbo boost
        effective_map_inhg = map_inhg + turbo_boost_psi * 2.036  # psi to inHg

        # Manifold conditions
        manifold_pressure_pa = effective_map_inhg * 3386.39  # inHg to Pa
        manifold_temp_k = (ambient_temp_c + 273.15) * (1.0 + 0.05 * turbo_boost_psi)  # charge heating from turbo

        # Volumetric efficiency varies with RPM (peaks around 3500-4000 RPM)
        rpm_norm = rpm / 5800.0
        vol_eff = 0.85 * (1.0 - 0.3 * (rpm_norm - 0.65) ** 2)
        vol_eff = np.clip(vol_eff, 0.5, 0.92)

        # Total air mass flow (kg/s) using speed-density method
        # mdot_air = (MAP * Vd * N * η_vol) / (2 * R * T)  for 4-stroke
        if rpm > 0 and manifold_temp_k > 0:
            air_mass_flow = (manifold_pressure_pa * self.total_displacement_m3 *
                             (rpm / 60.0) * vol_eff) / (2.0 * self.R_AIR * manifold_temp_k)
        else:
            air_mass_flow = 0.0

        air_mass_flow = max(0.0, air_mass_flow)

        # Fuel flow for stoichiometric mixture
        base_fuel_flow = air_mass_flow / self.STOICH_AFR  # kg/s
        
        # Throttle affects mixture targeting (slightly rich for power, lean for cruise)
        mixture_target = 1.0
        if throttle > 0.85:
            mixture_target = 1.08  # rich for power
        elif throttle < 0.4:
            mixture_target = 0.95  # slightly lean for cruise economy

        # Per-cylinder combustion
        cyl_egts = np.zeros(self.num_cylinders)
        cyl_chts = np.zeros(self.num_cylinders)
        cyl_torques = np.zeros(self.num_cylinders)
        cyl_efficiencies = np.zeros(self.num_cylinders)
        cyl_far = np.zeros(self.num_cylinders)  # fuel-air ratio

        per_cyl_air = air_mass_flow / self.num_cylinders

        for i in range(self.num_cylinders):
            # Per-cylinder mixture with individual offsets (for lean/rich fault injection)
            cyl_mixture = mixture_target + self.cylinder_mixture_offset[i]
            cyl_fuel = (per_cyl_air / self.STOICH_AFR) * cyl_mixture
            
            actual_far = cyl_fuel / max(per_cyl_air, 1e-10)
            cyl_far[i] = actual_far

            # Combustion efficiency depends on mixture, compression, and cylinder health
            # Peaks at stoich, degrades lean or rich
            phi = cyl_mixture  # equivalence ratio
            mixture_eff = 1.0 - 0.4 * (phi - 1.0) ** 2
            mixture_eff = np.clip(mixture_eff, 0.3, 1.0)
            
            # Combined efficiency with cylinder health
            eta = mixture_eff * self.cylinder_efficiency[i]
            cyl_efficiencies[i] = eta

            # Heat released per cylinder
            q_released = cyl_fuel * self.LHV_AVGAS * eta  # W

            # Thermal efficiency (simplified Otto cycle)
            eta_thermal = 1.0 - (1.0 / self.compression_ratio ** (self.GAMMA - 1))
            
            # Mechanical work per cylinder
            work_per_cyl = q_released * eta_thermal  # W
            
            # Torque per cylinder
            if rpm > 0:
                omega = rpm * 2.0 * np.pi / 60.0
                cyl_torques[i] = work_per_cyl / omega  # N·m per cylinder
            else:
                cyl_torques[i] = 0.0

            # Exhaust gas temperature
            # EGT rises with power, enrichment, and poor efficiency
            q_exhaust = q_released * (1.0 - eta_thermal) * 0.6  # ~60% of waste heat to exhaust
            exhaust_mass_flow = per_cyl_air + cyl_fuel
            if exhaust_mass_flow > 0:
                delta_t_exhaust = q_exhaust / (exhaust_mass_flow * self.CP_EXHAUST)
            else:
                delta_t_exhaust = 0.0
            
            base_egt = ambient_temp_c + 50  # base temperature
            cyl_egts[i] = base_egt + delta_t_exhaust
            
            # Rich mixture increases EGT, lean can also increase (lean misfire)
            if phi > 1.05:
                cyl_egts[i] += (phi - 1.0) * 80  # rich penalty
            elif phi < 0.9:
                cyl_egts[i] += (1.0 - phi) * 120  # lean burn penalty

            # Cylinder head temperature
            # CHT is driven by combustion heat minus cooling
            q_to_head = q_released * (1.0 - eta_thermal) * 0.3  # ~30% of waste heat to cylinder walls
            cooling_eff = self.cylinder_cooling_factor[i]
            
            # Simplified thermal equilibrium
            cht_rise = (q_to_head / max(cooling_eff * 500.0, 1.0))  # simplified thermal resistance
            cyl_chts[i] = ambient_temp_c + 80 + cht_rise  # base CHT offset + heating

        # Aggregate results
        total_torque = float(np.sum(cyl_torques))
        power_w = total_torque * (rpm * 2.0 * np.pi / 60.0) if rpm > 0 else 0.0
        power_hp = power_w / 745.7
        
        # Fuel flow in gal/hr (1 gal avgas ≈ 2.72 kg)
        fuel_flow_kgs = base_fuel_flow * mixture_target
        fuel_flow_gph = fuel_flow_kgs * 3600.0 / 2.72

        return {
            "air_mass_flow_gs": air_mass_flow * 1000.0,  # g/s
            "fuel_flow_gph": fuel_flow_gph,
            "fuel_air_ratio": float(np.mean(cyl_far)),
            "volumetric_efficiency": vol_eff,
            "total_torque_nm": total_torque,
            "power_hp": power_hp,
            "cyl_egts": cyl_egts.tolist(),
            "cyl_chts": cyl_chts.tolist(),
            "cyl_efficiencies": cyl_efficiencies.tolist(),
            "cyl_torques": cyl_torques.tolist(),
            "cyl_fuel_air_ratios": cyl_far.tolist(),
            "mixture_target": mixture_target,
            "effective_map_inhg": effective_map_inhg,
            "manifold_temp_k": manifold_temp_k,
        }

    def set_cylinder_efficiency(self, cylinder_id: int, efficiency: float):
        """Set combustion efficiency for a specific cylinder (fault injection point)."""
        if 0 <= cylinder_id < self.num_cylinders:
            self.cylinder_efficiency[cylinder_id] = np.clip(efficiency, 0.0, 1.0)

    def set_mixture_offset(self, cylinder_id: int, offset: float):
        """Set mixture offset for a specific cylinder (lean/rich fault)."""
        if 0 <= cylinder_id < self.num_cylinders:
            self.cylinder_mixture_offset[cylinder_id] = offset

    def set_cooling_factor(self, cylinder_id: int, factor: float):
        """Set cooling effectiveness for a specific cylinder."""
        if 0 <= cylinder_id < self.num_cylinders:
            self.cylinder_cooling_factor[cylinder_id] = np.clip(factor, 0.1, 1.5)

    def reset(self):
        """Reset all cylinders to healthy state."""
        self.cylinder_efficiency = np.ones(self.num_cylinders)
        self.cylinder_mixture_offset = np.zeros(self.num_cylinders)
        self.cylinder_cooling_factor = np.ones(self.num_cylinders)
