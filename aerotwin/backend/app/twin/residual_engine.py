"""
Residual Engine
Computes normalized residuals between observed (sensor) and expected (digital twin) values.
Tracks residual trends over time using rolling windows.

residual_i = (observed_i - expected_i) / sigma_i
"""
import numpy as np
from collections import deque
from typing import Optional
from ..schemas.telemetry import SensorFrame
from ..config import TwinConfig


class ResidualEngine:
    """
    Computes and tracks residuals between actual sensor readings and
    digital twin predictions.
    
    Normalized residual: r_i = (observed_i - expected_i) / sigma_i
    
    Maintains rolling window statistics for trend detection.
    """

    def __init__(self, config: Optional[TwinConfig] = None):
        if config is None:
            config = TwinConfig()
        self.config = config
        self.window_size = config.residual_window_size
        
        # Rolling residual history per channel
        self.history: dict[str, deque] = {}
        # Channel uncertainty (sigma) per channel
        self.channel_sigma: dict[str, float] = {}
        # Latest residuals
        self.current_residuals: dict[str, float] = {}
        self.current_raw_residuals: dict[str, float] = {}
        
        # Default sigma values (noise std from sensor model)
        self._default_sigmas = {
            "EGT1": 3.0, "EGT2": 3.0, "EGT3": 3.0, "EGT4": 3.0,
            "CHT1": 2.0, "CHT2": 2.0, "CHT3": 2.0, "CHT4": 2.0,
            "OIL_PRESSURE": 0.5, "OIL_TEMP": 1.5,
            "MAP": 0.3, "RPM": 5.0,
            "VIBRATION": 0.02, "BUS_VOLTAGE": 0.05,
            "FUEL_FLOW": 0.1, "TURBO_BOOST": 0.1,
        }

    def compute(self, sensor_frame: SensorFrame, expected_values: dict[str, float]) -> dict[str, float]:
        """
        Compute normalized residuals for all channels.
        
        Returns dict of channel_name → normalized_residual
        """
        self.current_residuals = {}
        self.current_raw_residuals = {}
        
        for name, expected in expected_values.items():
            sensor = sensor_frame.sensors.get(name)
            if sensor is None:
                continue
            
            observed = sensor.value
            raw_residual = observed - expected
            self.current_raw_residuals[name] = raw_residual
            
            # Get sigma for normalization
            sigma = self._get_sigma(name)
            if sigma > 0:
                normalized = raw_residual / sigma
            else:
                normalized = raw_residual
            
            self.current_residuals[name] = normalized
            
            # Update history
            if name not in self.history:
                self.history[name] = deque(maxlen=self.window_size)
            self.history[name].append(normalized)
        
        return self.current_residuals

    def _get_sigma(self, channel: str) -> float:
        """Get uncertainty (sigma) for a channel."""
        if channel in self.channel_sigma:
            return self.channel_sigma[channel]
        return self._default_sigmas.get(channel, 1.0)

    def set_sigma(self, channel: str, sigma: float):
        """Override sigma for a channel."""
        self.channel_sigma[channel] = max(sigma, 0.001)

    def get_rolling_mean(self, channel: str) -> float:
        """Get rolling mean of residuals for a channel."""
        if channel in self.history and len(self.history[channel]) > 0:
            return float(np.mean(list(self.history[channel])))
        return 0.0

    def get_rolling_std(self, channel: str) -> float:
        """Get rolling std of residuals for a channel."""
        if channel in self.history and len(self.history[channel]) > 2:
            return float(np.std(list(self.history[channel])))
        return 0.0

    def get_trend(self, channel: str) -> float:
        """
        Get linear trend (slope) of residuals for a channel.
        Positive = increasing divergence.
        """
        if channel not in self.history or len(self.history[channel]) < 10:
            return 0.0
        
        data = np.array(list(self.history[channel]))
        x = np.arange(len(data))
        if len(data) < 2:
            return 0.0
        
        # Simple linear regression slope
        slope = np.polyfit(x, data, 1)[0]
        return float(slope)

    def get_anomalous_channels(self, threshold: float = 3.0) -> list[str]:
        """Get channels where recent residuals exceed threshold."""
        anomalous = []
        for channel, residual in self.current_residuals.items():
            if abs(residual) > threshold:
                # Check persistence: use rolling mean not just single sample
                rolling_mean = self.get_rolling_mean(channel)
                if abs(rolling_mean) > threshold * 0.5:  # persistent anomaly
                    anomalous.append(channel)
        return anomalous

    def get_all_residuals(self) -> dict:
        """Get current residuals with statistics."""
        result = {}
        for channel in self.current_residuals:
            result[channel] = {
                "normalized": round(self.current_residuals.get(channel, 0.0), 3),
                "raw": round(self.current_raw_residuals.get(channel, 0.0), 3),
                "rolling_mean": round(self.get_rolling_mean(channel), 3),
                "rolling_std": round(self.get_rolling_std(channel), 3),
                "trend": round(self.get_trend(channel), 5),
                "sigma": round(self._get_sigma(channel), 3),
            }
        return result

    def reset(self):
        self.history.clear()
        self.current_residuals.clear()
        self.current_raw_residuals.clear()
