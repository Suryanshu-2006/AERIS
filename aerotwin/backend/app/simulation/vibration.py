"""
Vibration Model
Models engine vibration as a function of RPM, mechanical balance, bearing health,
combustion roughness, and fault conditions.
"""
import numpy as np


class VibrationModel:
    """
    Simplified vibration model:
    - Base vibration from reciprocating mass (RPM-dependent)
    - Additional vibration from imbalance, bearing wear, misfire
    - Dominant frequency tracking
    """

    def __init__(self, num_cylinders: int = 4):
        self.num_cylinders = num_cylinders
        self.vibration_g = 0.05
        self.dominant_freq_hz = 0.0
        
        # Health factors
        self.balance_factor = 1.0  # 1.0 = perfect balance
        self.bearing_roughness = 0.0  # 0 = smooth, 1 = severe roughness
        self.misfire_vibration = 0.0  # additional vibration from misfire
        self.mount_integrity = 1.0  # engine mount condition

    def update(self, rpm: float, cyl_efficiencies: list[float],
               oil_pressure_psi: float, bearing_stress: float) -> dict:
        """
        Compute vibration level.
        
        Vibration sources:
        1. Base reciprocating vibration (proportional to RPM^2)
        2. Combustion roughness (from efficiency variation across cylinders)
        3. Bearing roughness (from oil pressure loss)
        4. Misfire events
        """
        # 1. Base vibration from reciprocating mass
        rpm_norm = rpm / 5800.0
        base_vib = 0.02 + 0.06 * rpm_norm ** 2  # ~0.02g idle, ~0.08g max RPM
        
        # 2. Combustion roughness: variance of per-cylinder efficiency
        if len(cyl_efficiencies) > 0:
            eff_array = np.array(cyl_efficiencies)
            roughness = np.std(eff_array) * 2.0  # higher variance = rougher
            combustion_vib = roughness * 0.5 * rpm_norm
        else:
            combustion_vib = 0.0
        
        # 3. Bearing wear increases with oil pressure loss
        bearing_vib = self.bearing_roughness * 0.3 * rpm_norm
        # Oil pressure contribution
        if oil_pressure_psi < 30:
            bearing_vib += (30 - oil_pressure_psi) / 30.0 * 0.2
        
        # Bearing stress from lubrication model
        bearing_vib += bearing_stress * 0.4 * rpm_norm
        
        # 4. Misfire events
        misfire_vib = self.misfire_vibration * 0.5
        
        # Total vibration
        total = base_vib + combustion_vib + bearing_vib + misfire_vib
        total *= (2.0 - self.mount_integrity)  # degraded mounts amplify
        total /= self.balance_factor  # imbalance increases
        
        self.vibration_g = np.clip(total, 0.01, 5.0)
        
        # Dominant frequency: primary firing frequency
        # For 4-cyl 4-stroke: 2 firings per revolution
        if rpm > 0:
            self.dominant_freq_hz = rpm / 60.0 * (self.num_cylinders / 2.0)
        else:
            self.dominant_freq_hz = 0.0
        
        return {
            "vibration_g": round(self.vibration_g, 4),
            "dominant_freq_hz": round(self.dominant_freq_hz, 1),
            "base_vib": round(base_vib, 4),
            "combustion_vib": round(combustion_vib, 4),
            "bearing_vib": round(bearing_vib, 4),
        }

    def set_bearing_roughness(self, roughness: float):
        self.bearing_roughness = np.clip(roughness, 0.0, 1.0)

    def set_misfire_vibration(self, level: float):
        self.misfire_vibration = np.clip(level, 0.0, 1.0)

    def set_balance_factor(self, factor: float):
        self.balance_factor = np.clip(factor, 0.5, 1.5)

    def set_mount_integrity(self, integrity: float):
        self.mount_integrity = np.clip(integrity, 0.3, 1.0)

    def reset(self):
        self.vibration_g = 0.05
        self.dominant_freq_hz = 0.0
        self.balance_factor = 1.0
        self.bearing_roughness = 0.0
        self.misfire_vibration = 0.0
        self.mount_integrity = 1.0
