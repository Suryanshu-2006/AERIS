"""
Model Calibration
Adaptive calibration of digital twin model parameters based on
observed sensor data during healthy operation periods.
"""
import numpy as np
from collections import deque


class ModelCalibrator:
    """
    Simple online calibration: adjusts per-channel sigma (uncertainty)
    based on observed residual statistics during confirmed-healthy periods.
    """

    def __init__(self, learning_rate: float = 0.01, window_size: int = 200):
        self.learning_rate = learning_rate
        self.window_size = window_size
        self.residual_windows: dict[str, deque] = {}
        self.calibrated_sigma: dict[str, float] = {}
        self.is_calibrating = False
        self.calibration_samples = 0

    def update(self, residuals: dict[str, float], is_healthy: bool):
        """Update calibration with new residuals (only during healthy operation)."""
        if not is_healthy:
            return
        
        self.is_calibrating = True
        self.calibration_samples += 1
        
        for channel, residual in residuals.items():
            if channel not in self.residual_windows:
                self.residual_windows[channel] = deque(maxlen=self.window_size)
            self.residual_windows[channel].append(residual)
            
            # Update sigma estimate
            if len(self.residual_windows[channel]) >= 20:
                observed_std = np.std(list(self.residual_windows[channel]))
                current = self.calibrated_sigma.get(channel, 1.0)
                # Exponential moving average update
                self.calibrated_sigma[channel] = (
                    (1 - self.learning_rate) * current +
                    self.learning_rate * max(observed_std, 0.1)
                )

    def get_calibrated_sigmas(self) -> dict[str, float]:
        return self.calibrated_sigma.copy()

    def reset(self):
        self.residual_windows.clear()
        self.calibrated_sigma.clear()
        self.calibration_samples = 0
        self.is_calibrating = False
