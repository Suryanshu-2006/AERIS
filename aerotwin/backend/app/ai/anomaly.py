"""
Anomaly Detection Engine
Temporal anomaly detection using rolling windows, physics residuals,
operating envelope analysis, and persistence tracking.

Does NOT classify from a single frame — requires persistence over time.
"""
import numpy as np
from collections import deque
from typing import Optional
from ..schemas.diagnosis import AnomalyResult, FaultSeverity
from ..config import TwinConfig


class AnomalyDetector:
    """
    Multi-signal temporal anomaly detection.
    
    Combines:
    1. Physics residual magnitude
    2. Temporal anomaly score (rolling window)
    3. Operating envelope check
    4. Sensor confidence weighting
    5. Persistence (consecutive anomalous frames)
    
    Unknown anomalies: if behavior doesn't match any known pattern,
    it is flagged as UNKNOWN_ANOMALY rather than force-classified.
    """

    def __init__(self, config: Optional[TwinConfig] = None):
        if config is None:
            config = TwinConfig()
        self.threshold = config.anomaly_threshold
        self.persistence_threshold = config.persistence_window
        
        # Persistence counters per channel
        self.persistence_counter: dict[str, int] = {}
        # Global anomaly persistence
        self.global_persistence = 0
        # History of anomaly scores
        self.score_history = deque(maxlen=120)
        # Operating envelope bounds (channel → (min, max))
        self.envelope = {
            "RPM": (800, 5900),
            "EGT1": (200, 870), "EGT2": (200, 870), "EGT3": (200, 870), "EGT4": (200, 870),
            "CHT1": (60, 260), "CHT2": (60, 260), "CHT3": (60, 260), "CHT4": (60, 260),
            "OIL_PRESSURE": (20, 95),
            "OIL_TEMP": (30, 135),
            "MAP": (5, 45),
            "VIBRATION": (0, 1.5),
            "BUS_VOLTAGE": (22, 30),
            "FUEL_FLOW": (0, 18),
            "TURBO_BOOST": (0, 10),
        }

    def detect(self, residuals: dict[str, float],
               sensor_confidences: dict[str, float] = None,
               observed_values: dict[str, float] = None) -> AnomalyResult:
        """
        Run anomaly detection on current frame.
        
        Returns AnomalyResult with score, confidence, persistence, and severity.
        """
        if sensor_confidences is None:
            sensor_confidences = {}
        if observed_values is None:
            observed_values = {}
        
        anomalous_channels = []
        channel_scores = []
        
        for channel, residual in residuals.items():
            abs_residual = abs(residual)
            
            # 1. Residual magnitude score
            residual_score = min(abs_residual / self.threshold, 3.0) / 3.0  # 0-1
            
            # 2. Operating envelope check
            envelope_score = 0.0
            if channel in self.envelope and channel in observed_values:
                lo, hi = self.envelope[channel]
                val = observed_values[channel]
                if val < lo:
                    envelope_score = min((lo - val) / max(lo, 1), 1.0)
                elif val > hi:
                    envelope_score = min((val - hi) / max(hi, 1), 1.0)
            
            # 3. Sensor confidence weighting
            sensor_conf = sensor_confidences.get(channel, 1.0)
            
            # Combined channel anomaly score
            # Weight residual more if sensor is trusted
            channel_score = (residual_score * 0.7 + envelope_score * 0.3) * sensor_conf
            channel_scores.append(channel_score)
            
            # Track persistence per channel
            if abs_residual > self.threshold:
                self.persistence_counter[channel] = self.persistence_counter.get(channel, 0) + 1
            else:
                self.persistence_counter[channel] = max(0, self.persistence_counter.get(channel, 0) - 1)
            
            # Only flag if persistent
            if self.persistence_counter.get(channel, 0) >= self.persistence_threshold:
                anomalous_channels.append(channel)
        
        # Global anomaly score (weighted by most anomalous channels)
        if channel_scores:
            sorted_scores = sorted(channel_scores, reverse=True)
            # Emphasize worst channels
            top_n = min(5, len(sorted_scores))
            anomaly_score = np.mean(sorted_scores[:top_n])
        else:
            anomaly_score = 0.0
        
        anomaly_score = float(np.clip(anomaly_score, 0.0, 1.0))
        
        # Global persistence
        if anomaly_score > 0.3:
            self.global_persistence += 1
        else:
            self.global_persistence = max(0, self.global_persistence - 2)
        
        # Determine if truly anomalous (requires persistence)
        is_anomalous = (
            anomaly_score > 0.3 and
            self.global_persistence >= self.persistence_threshold
        )
        
        # Confidence increases with persistence
        persistence_factor = min(self.global_persistence / (self.persistence_threshold * 3), 1.0)
        confidence = anomaly_score * (0.5 + 0.5 * persistence_factor) if is_anomalous else anomaly_score * 0.3
        
        # Severity
        if anomaly_score < 0.2:
            severity = FaultSeverity.HEALTHY
        elif anomaly_score < 0.4:
            severity = FaultSeverity.MILD
        elif anomaly_score < 0.6:
            severity = FaultSeverity.MODERATE
        elif anomaly_score < 0.8:
            severity = FaultSeverity.SEVERE
        else:
            severity = FaultSeverity.CRITICAL
        
        self.score_history.append(anomaly_score)
        
        # Description
        if is_anomalous:
            desc = f"Anomaly detected in {len(anomalous_channels)} channel(s): {', '.join(anomalous_channels[:5])}"
        else:
            desc = "No persistent anomaly detected"
        
        return AnomalyResult(
            timestamp=0.0,  # filled by caller
            anomaly_score=round(anomaly_score, 4),
            confidence=round(float(confidence), 4),
            persistence=self.global_persistence,
            severity=severity,
            is_anomalous=is_anomalous,
            anomalous_channels=anomalous_channels,
            description=desc,
        )

    def get_score_trend(self) -> list[float]:
        """Get recent anomaly score history."""
        return list(self.score_history)

    def reset(self):
        self.persistence_counter.clear()
        self.global_persistence = 0
        self.score_history.clear()
