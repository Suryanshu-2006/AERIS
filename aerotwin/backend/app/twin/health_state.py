"""
Health State Tracker
Computes subsystem health scores (0-100) from residuals, fault severity,
degradation, sensor confidence, and operating conditions.
"""
import numpy as np
from ..schemas.engine import HealthScores


class HealthState:
    """
    Maintains and updates health scores for all engine subsystems.
    
    Health is derived from:
    - Residuals (divergence from expected)
    - Fault severity (if diagnosed)
    - Degradation level
    - Sensor confidence
    - Operating conditions
    """

    def __init__(self):
        self.scores = HealthScores()
        self._raw_scores = {
            "combustion": 100.0,
            "cooling": 100.0,
            "lubrication": 100.0,
            "turbo": 100.0,
            "mechanical": 100.0,
            "electrical": 100.0,
            "sensors": 100.0,
        }
        # Smoothing factor for health changes
        self.smoothing = 0.95  # slow changes (higher = slower)

    def update(self, residuals: dict[str, float], fault_severity: float = 0.0,
               fault_subsystem: str = "", sensor_confidences: dict[str, float] = None,
               degradation_levels: dict[str, float] = None) -> HealthScores:
        """
        Update health scores based on current system state.
        """
        if sensor_confidences is None:
            sensor_confidences = {}
        if degradation_levels is None:
            degradation_levels = {}
        
        # Compute raw health for each subsystem based on related residuals
        subsystem_channels = {
            "combustion": ["EGT1", "EGT2", "EGT3", "EGT4", "FUEL_FLOW"],
            "cooling": ["CHT1", "CHT2", "CHT3", "CHT4"],
            "lubrication": ["OIL_PRESSURE", "OIL_TEMP"],
            "turbo": ["TURBO_BOOST", "MAP"],
            "mechanical": ["VIBRATION", "RPM"],
            "electrical": ["BUS_VOLTAGE"],
            "sensors": list(sensor_confidences.keys()) if sensor_confidences else [],
        }
        
        for subsystem, channels in subsystem_channels.items():
            if not channels:
                continue
            
            # Average absolute residual for this subsystem
            channel_residuals = [abs(residuals.get(ch, 0.0)) for ch in channels if ch in residuals]
            if channel_residuals:
                avg_residual = np.mean(channel_residuals)
                # Convert residual magnitude to health decrement
                # >3 sigma = significant, >5 sigma = severe
                residual_penalty = min(avg_residual * 8.0, 60.0)  # max 60-point penalty from residuals
            else:
                residual_penalty = 0.0
            
            # Fault penalty if this subsystem is affected
            fault_penalty = 0.0
            if fault_subsystem and fault_subsystem.upper() == subsystem.upper():
                fault_penalty = fault_severity * 50.0  # up to 50-point penalty
            
            # Degradation penalty
            deg = degradation_levels.get(subsystem, 0.0)
            deg_penalty = deg * 40.0  # up to 40-point penalty
            
            # Sensor confidence penalty (for sensors subsystem)
            sensor_penalty = 0.0
            if subsystem == "sensors":
                confidences = list(sensor_confidences.values())
                if confidences:
                    avg_conf = np.mean(confidences)
                    sensor_penalty = (1.0 - avg_conf) * 40.0
            
            # Raw target health
            target = 100.0 - residual_penalty - fault_penalty - deg_penalty - sensor_penalty
            target = np.clip(target, 0.0, 100.0)
            
            # Smooth transition
            current = self._raw_scores[subsystem]
            self._raw_scores[subsystem] = self.smoothing * current + (1 - self.smoothing) * target
        
        # Update scores
        self.scores.combustion = round(self._raw_scores["combustion"], 1)
        self.scores.cooling = round(self._raw_scores["cooling"], 1)
        self.scores.lubrication = round(self._raw_scores["lubrication"], 1)
        self.scores.turbo = round(self._raw_scores["turbo"], 1)
        self.scores.mechanical = round(self._raw_scores["mechanical"], 1)
        self.scores.electrical = round(self._raw_scores["electrical"], 1)
        self.scores.sensors = round(self._raw_scores["sensors"], 1)
        self.scores.overall()
        
        return self.scores

    def get_weakest_subsystem(self) -> tuple[str, float]:
        """Return the weakest subsystem and its score."""
        scores = {
            "combustion": self.scores.combustion,
            "cooling": self.scores.cooling,
            "lubrication": self.scores.lubrication,
            "turbo": self.scores.turbo,
            "mechanical": self.scores.mechanical,
            "electrical": self.scores.electrical,
        }
        weakest = min(scores, key=scores.get)
        return weakest, scores[weakest]

    def reset(self):
        self.scores = HealthScores()
        self._raw_scores = {k: 100.0 for k in self._raw_scores}
