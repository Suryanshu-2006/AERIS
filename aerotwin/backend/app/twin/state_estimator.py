"""
State Estimator
Maintains the digital twin's estimate of the actual engine state,
combining sensor data with physics model predictions using a
simplified Kalman-like fusion approach.
"""
import numpy as np
from typing import Optional
from ..schemas.telemetry import SensorFrame
from ..schemas.engine import EngineState


class StateEstimator:
    """
    Fuses sensor observations with physics model predictions.
    
    Uses a simplified alpha-beta filter approach:
    estimated = alpha * observed + (1 - alpha) * predicted
    
    where alpha is adjusted based on sensor confidence.
    """

    def __init__(self, base_alpha: float = 0.7):
        self.base_alpha = base_alpha  # default trust in sensors
        self.estimated_state: dict[str, float] = {}
        self.state_variance: dict[str, float] = {}

    def estimate(self, sensor_frame: SensorFrame, predicted_values: dict[str, float]) -> dict[str, float]:
        """
        Produce fused state estimate from sensors and physics prediction.
        """
        self.estimated_state = {}
        
        for name, predicted in predicted_values.items():
            sensor = sensor_frame.sensors.get(name)
            if sensor is None:
                self.estimated_state[name] = predicted
                continue
            
            observed = sensor.value
            confidence = sensor.confidence
            
            # Adjust alpha based on sensor confidence
            alpha = self.base_alpha * confidence
            alpha = np.clip(alpha, 0.1, 0.95)
            
            # Fused estimate
            estimated = alpha * observed + (1.0 - alpha) * predicted
            self.estimated_state[name] = estimated
            
            # State variance (rough approximation)
            sensor_var = sensor.noise_std ** 2
            model_var = sensor_var * 2  # model has roughly 2x sensor uncertainty
            fused_var = (1.0 / (1.0 / max(sensor_var, 0.001) + 1.0 / max(model_var, 0.001)))
            self.state_variance[name] = fused_var
        
        return self.estimated_state

    def get_confidence(self, channel: str) -> float:
        """Get estimation confidence for a channel (inverse of variance)."""
        var = self.state_variance.get(channel, 1.0)
        return 1.0 / (1.0 + var)

    def reset(self):
        self.estimated_state.clear()
        self.state_variance.clear()
