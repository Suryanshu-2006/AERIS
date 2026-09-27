"""
Drift Monitor
Detects systematic model drift: when residuals are consistently elevated
across many channels without evidence of a specific fault.
This prevents the system from treating model mismatch as engine failure.
"""
import numpy as np
from collections import deque
from typing import Optional
from ..config import TwinConfig


class DriftMonitor:
    """
    Twin Drift Monitor
    
    If residuals remain systematically high across many healthy channels
    while no fault evidence exists → MODEL DRIFT / OPERATING REGIME MISMATCH
    """

    def __init__(self, config: Optional[TwinConfig] = None):
        if config is None:
            config = TwinConfig()
        self.window_size = config.drift_window_size
        self.threshold = config.drift_threshold
        
        # Track per-channel mean residuals over long window
        self.channel_means: dict[str, deque] = {}
        self.drift_detected = False
        self.drift_score = 0.0
        self.drift_channels: list[str] = []

    def update(self, residuals: dict[str, float], anomalous_channels: list[str]) -> dict:
        """
        Check for systematic model drift.
        
        Drift is suspected when:
        1. Many channels show elevated residuals (> threshold)
        2. But no specific fault pattern is identified
        3. The elevation is consistent (not sporadic)
        """
        elevated_count = 0
        total_count = 0
        elevated_channels = []
        
        for channel, residual in residuals.items():
            # Track rolling mean
            if channel not in self.channel_means:
                self.channel_means[channel] = deque(maxlen=self.window_size)
            self.channel_means[channel].append(abs(residual))
            
            total_count += 1
            
            # Check if channel mean is systematically elevated
            if len(self.channel_means[channel]) >= 20:
                channel_mean = np.mean(list(self.channel_means[channel]))
                if channel_mean > self.threshold:
                    elevated_count += 1
                    elevated_channels.append(channel)
        
        # Drift detected if many channels are elevated but not in anomalous set
        # (anomalous channels already have fault explanations)
        non_fault_elevated = [ch for ch in elevated_channels if ch not in anomalous_channels]
        
        fraction_elevated = len(non_fault_elevated) / max(total_count, 1)
        
        self.drift_detected = fraction_elevated > 0.4 and len(non_fault_elevated) >= 3
        self.drift_score = min(fraction_elevated * 2, 1.0)
        self.drift_channels = non_fault_elevated
        
        return {
            "drift_detected": self.drift_detected,
            "drift_score": round(self.drift_score, 3),
            "elevated_channels": self.drift_channels,
            "fraction_elevated": round(fraction_elevated, 3),
            "description": (
                "MODEL DRIFT / OPERATING REGIME MISMATCH detected — "
                f"{len(non_fault_elevated)} channels show systematic residual elevation "
                "without matching any known fault pattern"
            ) if self.drift_detected else "No model drift detected",
        }

    def reset(self):
        self.channel_means.clear()
        self.drift_detected = False
        self.drift_score = 0.0
        self.drift_channels = []
