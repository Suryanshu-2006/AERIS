"""
Turbocharger Model
Models exhaust-driven turbocharger boost as a function of RPM, exhaust energy, and altitude.
Turbo allows maintaining sea-level power at altitude.
"""
import numpy as np


class TurboModel:
    """
    Simplified turbocharger model:
    - Turbine driven by exhaust gas energy
    - Compressor boosts intake manifold pressure
    - Wastegate limits max boost
    - Turbo lag modeled with spool-up time constant
    """

    def __init__(self, max_boost_psi: float = 8.0):
        self.max_boost_psi = max_boost_psi
        self.current_boost_psi = 0.0
        self.turbo_rpm = 0.0
        self.max_turbo_rpm = 140000.0
        self.efficiency = 0.75
        self.wastegate_position = 0.0  # 0 = closed, 1 = fully open
        
        # Health
        self.turbo_health = 1.0  # bearing wear, blade damage
        self.shaft_efficiency = 1.0

    def update(self, dt: float, engine_rpm: float, exhaust_energy: float,
               altitude_ft: float, throttle: float, ambient_pressure_inhg: float) -> dict:
        """
        Update turbo state.
        
        Boost is needed more at altitude where ambient pressure drops.
        Higher exhaust energy (more throttle/RPM) drives more boost.
        """
        # Exhaust energy drives turbine speed
        # More RPM + more throttle = more exhaust = more turbo
        rpm_factor = engine_rpm / 5800.0
        throttle_factor = throttle
        energy_factor = rpm_factor * throttle_factor * self.turbo_health
        
        # Target turbo RPM
        target_turbo_rpm = self.max_turbo_rpm * energy_factor * self.shaft_efficiency
        
        # Turbo lag: spool-up time constant
        tau_spool = 2.5  # seconds
        alpha = 1.0 - np.exp(-dt / tau_spool)
        self.turbo_rpm += alpha * (target_turbo_rpm - self.turbo_rpm)
        self.turbo_rpm = max(0.0, self.turbo_rpm)
        
        # Boost pressure from turbo RPM
        turbo_rpm_ratio = self.turbo_rpm / self.max_turbo_rpm
        potential_boost = self.max_boost_psi * turbo_rpm_ratio ** 1.5 * self.efficiency
        
        # Wastegate regulation: limit boost to max
        if potential_boost > self.max_boost_psi * self.turbo_health:
            self.wastegate_position = 1.0 - (self.max_boost_psi * self.turbo_health / max(potential_boost, 0.01))
            self.wastegate_position = np.clip(self.wastegate_position, 0.0, 1.0)
            actual_boost = self.max_boost_psi * self.turbo_health
        else:
            self.wastegate_position = 0.0
            actual_boost = potential_boost
        
        # Altitude compensation: turbo works harder at altitude to maintain boost
        # But available exhaust energy also decreases
        altitude_factor = ambient_pressure_inhg / 29.92
        actual_boost *= (0.5 + 0.5 * altitude_factor)  # partial altitude compensation
        
        # Smooth transition
        tau_boost = 1.5
        alpha_b = 1.0 - np.exp(-dt / tau_boost)
        self.current_boost_psi += alpha_b * (actual_boost - self.current_boost_psi)
        self.current_boost_psi = max(0.0, self.current_boost_psi)
        
        return {
            "turbo_boost_psi": round(self.current_boost_psi, 3),
            "turbo_rpm": round(self.turbo_rpm, 0),
            "wastegate_position": round(self.wastegate_position, 3),
            "turbo_efficiency": self.efficiency,
            "turbo_health": self.turbo_health,
        }

    def set_health(self, health: float):
        """Degrade turbo (bearing wear, blade damage)."""
        self.turbo_health = np.clip(health, 0.0, 1.0)

    def set_shaft_efficiency(self, eff: float):
        self.shaft_efficiency = np.clip(eff, 0.0, 1.0)

    def get_manifold_pressure(self, ambient_pressure_inhg: float) -> float:
        """Return total manifold pressure = ambient + boost."""
        return ambient_pressure_inhg + self.current_boost_psi * 2.036

    def reset(self):
        self.current_boost_psi = 0.0
        self.turbo_rpm = 0.0
        self.wastegate_position = 0.0
        self.turbo_health = 1.0
        self.shaft_efficiency = 1.0
        self.efficiency = 0.75
