"""
Sensor Integrity Analyzer
Determines whether abnormal telemetry is caused by sensor faults vs physical faults.
Uses cross-channel correlation and temporal patterns.
"""
import numpy as np
from collections import deque
from ..schemas.diagnosis import SensorIntegrityResult


class SensorIntegrityAnalyzer:
    """
    Analyzes individual sensor health by comparing against:
    1. Expected value from physics model
    2. Cross-channel consistency (e.g., EGT3 vs EGT1/2/4)
    3. Temporal behavior (stuck, drift, noise changes)
    """

    def __init__(self, window_size: int = 40):
        self.window_size = window_size
        self.value_history: dict[str, deque] = {}
        self.residual_history: dict[str, deque] = {}

    def analyze(self, sensor_values: dict[str, float],
                residuals: dict[str, float],
                sensor_confidences: dict[str, float]) -> list[SensorIntegrityResult]:
        """Analyze integrity of all sensors."""
        results = []
        
        for name, value in sensor_values.items():
            # Update history
            if name not in self.value_history:
                self.value_history[name] = deque(maxlen=self.window_size)
                self.residual_history[name] = deque(maxlen=self.window_size)
            self.value_history[name].append(value)
            self.residual_history[name].append(residuals.get(name, 0.0))
            
            result = self._analyze_sensor(name, value, residuals, sensor_values, sensor_confidences)
            results.append(result)
        
        return results

    def _analyze_sensor(self, name: str, value: float,
                        residuals: dict, all_values: dict,
                        confidences: dict) -> SensorIntegrityResult:
        """Analyze a single sensor's integrity."""
        evidence = []
        integrity_score = 1.0
        fault_type = ""
        
        residual = abs(residuals.get(name, 0.0))
        history = list(self.value_history.get(name, []))
        
        # 1. Check for stuck sensor (variance near zero)
        if len(history) >= 10:
            recent_std = np.std(history[-10:])
            expected_noise = self._expected_noise(name)
            if recent_std < expected_noise * 0.1 and len(history) >= 15:
                integrity_score -= 0.4
                fault_type = "STUCK"
                evidence.append(f"Sensor variance ({recent_std:.4f}) much lower than expected ({expected_noise:.4f}) — possible stuck sensor")
        
        # 2. Check for drift (trend in residual)
        res_history = list(self.residual_history.get(name, []))
        if len(res_history) >= 20:
            x = np.arange(len(res_history))
            slope = np.polyfit(x, res_history, 1)[0]
            if abs(slope) > 0.05:
                integrity_score -= min(abs(slope) * 2, 0.3)
                if not fault_type:
                    fault_type = "DRIFT"
                evidence.append(f"Residual trend slope: {slope:.4f}/sample — progressive drift detected")
        
        # 3. Check cross-channel consistency
        group = self._get_channel_group(name)
        if group:
            group_values = [all_values.get(ch, None) for ch in group if ch != name and ch in all_values]
            group_residuals = [abs(residuals.get(ch, 0)) for ch in group if ch != name and ch in residuals]
            
            if group_values and None not in group_values:
                group_mean = np.mean(group_values)
                deviation = abs(value - group_mean)
                group_std = np.std(group_values) if len(group_values) > 1 else 1.0
                
                if group_std > 0 and deviation > 3 * max(group_std, 1.0):
                    # This sensor is very different from its group
                    if group_residuals and max(group_residuals) < 2.0:
                        # Group members are normal → likely this sensor is faulty
                        integrity_score -= 0.3
                        if not fault_type:
                            fault_type = "BIAS"
                        evidence.append(
                            f"Value deviates significantly from peer group "
                            f"(value={value:.1f}, group_mean={group_mean:.1f}) "
                            f"while peer sensors are normal"
                        )
        
        # 4. High residual without correlated evidence
        correlated = self._get_correlated_channels(name)
        if residual > 4.0:
            corr_residuals = [abs(residuals.get(ch, 0)) for ch in correlated if ch in residuals]
            if corr_residuals and max(corr_residuals) < 2.0:
                # Only this sensor is anomalous, correlated channels are fine
                integrity_score -= 0.2
                if not fault_type:
                    fault_type = "BIAS"
                evidence.append(
                    f"High residual ({residual:.1f}σ) but correlated channels "
                    f"({', '.join(correlated[:3])}) are normal — suggests sensor issue"
                )
        
        # 5. Intermittent check (high variance in residuals)
        if len(res_history) >= 10:
            res_std = np.std(res_history[-10:])
            if res_std > 5.0:
                integrity_score -= 0.2
                if not fault_type:
                    fault_type = "INTERMITTENT"
                evidence.append(f"Residual variance unusually high ({res_std:.2f}) — intermittent behavior")
        
        # Factor in reported confidence
        reported_conf = confidences.get(name, 1.0)
        if reported_conf < 0.8:
            integrity_score -= (1.0 - reported_conf) * 0.3
        
        integrity_score = max(0.0, min(1.0, integrity_score))
        is_faulty = integrity_score < 0.6
        
        if not fault_type:
            fault_type = "HEALTHY"
        
        return SensorIntegrityResult(
            sensor_name=name,
            integrity_score=round(integrity_score, 3),
            is_faulty=is_faulty,
            fault_type=fault_type,
            evidence=evidence,
            confidence=round(1.0 - abs(integrity_score - 0.5) * 0.5, 3),
        )

    def _get_channel_group(self, name: str) -> list[str]:
        """Get the group of similar sensors for cross-validation."""
        norm = name.upper().replace("_", "")
        if norm.startswith("EGT"):
            prefix = "egt_" if "_" in name else ("egt" if name.islower() else "EGT")
            if "_" in name and name.isupper():
                prefix = "EGT_"
            return [f"{prefix}{i}" for i in range(1, 5)]
        if norm.startswith("CHT"):
            prefix = "cht_" if "_" in name else ("cht" if name.islower() else "CHT")
            if "_" in name and name.isupper():
                prefix = "CHT_"
            return [f"{prefix}{i}" for i in range(1, 5)]
        return []

    def _get_correlated_channels(self, name: str) -> list[str]:
        """Channels that should physically correlate."""
        norm = name.upper().replace("_", "")
        correlations = {
            "EGT1": ["CHT1", "FUEL_FLOW", "VIBRATION"],
            "EGT2": ["CHT2", "FUEL_FLOW", "VIBRATION"],
            "EGT3": ["CHT3", "FUEL_FLOW", "VIBRATION"],
            "EGT4": ["CHT4", "FUEL_FLOW", "VIBRATION"],
            "CHT1": ["EGT1"], "CHT2": ["EGT2"], "CHT3": ["EGT3"], "CHT4": ["EGT4"],
            "OILPRESSURE": ["OIL_TEMP", "VIBRATION", "RPM"],
            "OILTEMP": ["OIL_PRESSURE"],
            "VIBRATION": ["RPM", "OIL_PRESSURE"],
            "MAP": ["TURBO_BOOST", "RPM"],
            "TURBOBOOST": ["MAP", "RPM"],
            "RPM": ["MAP", "FUEL_FLOW"],
        }
        res = correlations.get(norm, [])
        # Also return matching case/format if needed
        all_res = list(res)
        if "_" in name:
            all_res.extend([r.lower() for r in res])
        return all_res

    def _expected_noise(self, name: str) -> float:
        """Expected noise standard deviation for a sensor type."""
        norm = name.upper().replace("_", "")
        noise_map = {
            "EGT": 3.0, "CHT": 2.0, "OILPRESSURE": 0.5, "OILTEMP": 1.5,
            "MAP": 0.3, "RPM": 5.0, "VIBRATION": 0.02, "BUSVOLTAGE": 0.05,
            "FUELFLOW": 0.1, "TURBOBOOST": 0.1,
        }
        for prefix, noise in noise_map.items():
            if norm.startswith(prefix):
                return noise
        return 1.0

    def reset(self):
        self.value_history.clear()
        self.residual_history.clear()
