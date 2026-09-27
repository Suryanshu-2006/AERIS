"""
Fault Diagnosis Engine
Multi-hypothesis fault diagnosis with sensor vs engine fault separation.
Uses pattern matching on residual signatures to distinguish fault types.

CRITICAL: Separates sensor faults from physical engine faults.
"""
import numpy as np
from typing import Optional
from ..schemas.diagnosis import (
    DiagnosisResult, FaultHypothesis, FaultCategory, FaultSeverity,
    EvidenceItem, SensorIntegrityResult, AnomalyResult
)


# Fault signature patterns: which channels are affected and how
FAULT_SIGNATURES = {
    "LEAN_MIXTURE_CYL": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "COMBUSTION",
        "required": ["EGT_HIGH"],  # EGT rises (lean burn)
        "supporting": ["CHT_CHANGE", "FUEL_FLOW_LOW", "VIBRATION_CHANGE"],
        "contradicting": ["SINGLE_SENSOR_ONLY"],
        "affected_components": ["fuel_system", "injector", "mixture_control"],
    },
    "RICH_MIXTURE_CYL": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "COMBUSTION",
        "required": ["EGT_HIGH"],
        "supporting": ["FUEL_FLOW_HIGH", "CHT_CHANGE"],
        "contradicting": ["SINGLE_SENSOR_ONLY"],
        "affected_components": ["fuel_system", "injector"],
    },
    "COOLING_DEGRADATION": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "COOLING",
        "required": ["CHT_HIGH"],
        "supporting": ["EGT_NORMAL_OR_SLIGHT", "VIBRATION_NORMAL"],
        "contradicting": ["ALL_CHT_HIGH"],  # single cyl cooling issue
        "affected_components": ["cooling_fins", "baffles", "airflow"],
    },
    "OIL_PRESSURE_LOSS": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "LUBRICATION",
        "required": ["OIL_PRESSURE_LOW"],
        "supporting": ["OIL_TEMP_HIGH", "VIBRATION_HIGH"],
        "contradicting": [],
        "affected_components": ["oil_pump", "oil_lines", "bearings"],
    },
    "TURBO_BOOST_DEFICIENCY": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "TURBO",
        "required": ["TURBO_BOOST_LOW"],
        "supporting": ["MAP_LOW", "POWER_LOW"],
        "contradicting": [],
        "affected_components": ["turbocharger", "wastegate", "intercooler"],
    },
    "BEARING_WEAR": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "MECHANICAL",
        "required": ["VIBRATION_HIGH"],
        "supporting": ["OIL_PRESSURE_CHANGE", "OIL_TEMP_HIGH"],
        "contradicting": [],
        "affected_components": ["main_bearings", "con_rod_bearings", "crankshaft"],
    },
    "CYLINDER_MISFIRE": {
        "category": FaultCategory.MECHANICAL,
        "subsystem": "COMBUSTION",
        "required": ["EGT_LOW_SINGLE", "VIBRATION_HIGH"],
        "supporting": ["RPM_ROUGH", "POWER_LOW"],
        "contradicting": [],
        "affected_components": ["ignition", "spark_plug", "magneto"],
    },
}


class DiagnosisEngine:
    """
    Multi-hypothesis fault diagnosis engine.
    
    Process:
    1. Check sensor integrity (is the anomaly from a sensor fault?)
    2. Match residual patterns against known fault signatures
    3. Score hypotheses with evidence
    4. Detect unknown anomalies
    5. Generate evidence chain
    """

    def __init__(self):
        self.last_diagnosis: Optional[DiagnosisResult] = None
        self.diagnosis_history = []

    def diagnose(self, residuals: dict[str, float],
                 raw_residuals: dict[str, float],
                 anomaly: AnomalyResult,
                 sensor_integrity: list[SensorIntegrityResult],
                 observed_values: dict[str, float] = None,
                 expected_values: dict[str, float] = None,
                 timestamp: float = 0.0) -> DiagnosisResult:
        """
        Run full diagnosis pipeline.
        """
        if observed_values is None:
            observed_values = {}
        if expected_values is None:
            expected_values = {}
        
        if not anomaly.is_anomalous:
            result = DiagnosisResult(
                timestamp=timestamp,
                anomaly=anomaly,
                sensor_integrity=sensor_integrity,
                observation="All parameters within normal range",
                diagnosis_summary="No fault detected",
                recommendation="CONTINUE",
            )
            self.last_diagnosis = result
            return result
        
        # Analyze residual patterns
        patterns = self._analyze_patterns(residuals, raw_residuals, observed_values, expected_values)
        
        # Check if sensor faults explain the anomaly
        faulty_sensors = [si for si in sensor_integrity if si.is_faulty]
        
        # Generate hypotheses
        hypotheses = []
        
        # 1. Check for sensor fault hypotheses
        for si in faulty_sensors:
            sensor_hyp = self._build_sensor_hypothesis(si, patterns, residuals)
            if sensor_hyp:
                hypotheses.append(sensor_hyp)
        
        # 2. Check for physical fault hypotheses
        for fault_name, signature in FAULT_SIGNATURES.items():
            hyp = self._match_signature(fault_name, signature, patterns, residuals, 
                                        raw_residuals, observed_values, expected_values)
            if hyp and hyp.confidence > 0.15:
                hypotheses.append(hyp)
        
        # 3. Check for unknown anomaly
        if not hypotheses or max(h.confidence for h in hypotheses) < 0.4:
            unknown_hyp = FaultHypothesis(
                fault_id="UNKNOWN_ANOMALY",
                fault_name="Unknown Anomaly",
                category=FaultCategory.UNKNOWN,
                confidence=anomaly.anomaly_score * 0.7,
                severity=anomaly.anomaly_score,
                severity_label=anomaly.severity,
                subsystem="UNKNOWN",
                affected_components=anomaly.anomalous_channels[:5],
                evidence=[EvidenceItem(
                    category="OBSERVATION",
                    description=f"Anomalous behavior in {len(anomaly.anomalous_channels)} channels "
                                f"does not match any known fault signature",
                    weight=1.0,
                )],
            )
            hypotheses.append(unknown_hyp)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        primary = hypotheses[0] if hypotheses else None
        alternatives = hypotheses[1:5] if len(hypotheses) > 1 else []
        
        # Build evidence chain
        result = DiagnosisResult(
            timestamp=timestamp,
            primary_fault=primary,
            alternative_hypotheses=alternatives,
            sensor_integrity=sensor_integrity,
            anomaly=anomaly,
            observation=self._build_observation(anomaly, residuals, raw_residuals),
            physics_evidence=self._build_physics_evidence(primary, residuals, expected_values),
            correlated_signals=self._build_correlation_evidence(primary, residuals),
            diagnosis_summary=self._build_summary(primary, alternatives),
            confidence_explanation=self._build_confidence_explanation(primary),
            severity_explanation=self._build_severity_explanation(primary, anomaly),
            mission_consequence=self._build_mission_consequence(primary),
            recommendation=self._build_recommendation(primary, anomaly),
        )
        
        self.last_diagnosis = result
        return result

    def _analyze_patterns(self, residuals: dict, raw_residuals: dict,
                          observed: dict, expected: dict) -> dict:
        """Analyze residual patterns for pattern matching."""
        patterns = {}
        
        # EGT patterns
        egt_residuals = {k: v for k, v in residuals.items() if k.startswith("EGT")}
        if egt_residuals:
            egt_vals = list(egt_residuals.values())
            patterns["EGT_MEAN"] = np.mean(egt_vals)
            patterns["EGT_STD"] = np.std(egt_vals)
            patterns["EGT_MAX"] = max(egt_vals)
            patterns["EGT_MAX_CHANNEL"] = max(egt_residuals, key=egt_residuals.get)
            
            # Check if single EGT is high vs all
            if patterns["EGT_STD"] > 2.0:
                patterns["EGT_SINGLE_HIGH"] = True
            else:
                patterns["EGT_SINGLE_HIGH"] = False
        
        # CHT patterns
        cht_residuals = {k: v for k, v in residuals.items() if k.startswith("CHT")}
        if cht_residuals:
            cht_vals = list(cht_residuals.values())
            patterns["CHT_MEAN"] = np.mean(cht_vals)
            patterns["CHT_STD"] = np.std(cht_vals)
            patterns["CHT_MAX"] = max(cht_vals)
            patterns["CHT_MAX_CHANNEL"] = max(cht_residuals, key=cht_residuals.get)
        
        # Oil patterns
        patterns["OIL_PRESSURE_RESIDUAL"] = residuals.get("OIL_PRESSURE", 0.0)
        patterns["OIL_TEMP_RESIDUAL"] = residuals.get("OIL_TEMP", 0.0)
        patterns["VIBRATION_RESIDUAL"] = residuals.get("VIBRATION", 0.0)
        patterns["MAP_RESIDUAL"] = residuals.get("MAP", 0.0)
        patterns["TURBO_RESIDUAL"] = residuals.get("TURBO_BOOST", 0.0)
        patterns["FUEL_FLOW_RESIDUAL"] = residuals.get("FUEL_FLOW", 0.0)
        patterns["RPM_RESIDUAL"] = residuals.get("RPM", 0.0)
        
        return patterns

    def _build_sensor_hypothesis(self, si: SensorIntegrityResult,
                                  patterns: dict, residuals: dict) -> Optional[FaultHypothesis]:
        """Build hypothesis for a sensor fault."""
        sensor_name = si.sensor_name
        
        # Key check: does ONLY this sensor show anomaly, or do correlated channels also?
        # If only this sensor is anomalous → likely sensor fault
        # If correlated channels also anomalous → likely physical fault
        
        correlated = self._get_correlated_channels(sensor_name)
        correlated_anomalous = sum(1 for ch in correlated if abs(residuals.get(ch, 0)) > 3.0)
        
        # If correlated channels are normal → sensor fault is more likely
        if correlated_anomalous == 0:
            confidence = 0.7 + 0.2 * (1.0 - si.integrity_score)
        else:
            confidence = 0.3 * (1.0 - si.integrity_score)  # lower confidence if correlated signals also bad
        
        evidence = [
            EvidenceItem(
                category="SENSOR_CHECK",
                description=f"{sensor_name} integrity score: {si.integrity_score:.2f}",
                signal_name=sensor_name,
                value=si.integrity_score,
                weight=1.0,
                supports_hypothesis=f"{sensor_name}_SENSOR_FAULT",
            ),
            EvidenceItem(
                category="CORRELATION",
                description=f"Correlated channels anomalous: {correlated_anomalous}/{len(correlated)}",
                weight=0.8,
                supports_hypothesis=f"{sensor_name}_SENSOR_FAULT" if correlated_anomalous == 0 else "PHYSICAL_FAULT",
            ),
        ]
        evidence.extend([EvidenceItem(
            category="SENSOR_CHECK",
            description=ev,
            supports_hypothesis=f"{sensor_name}_SENSOR_FAULT",
            weight=0.5,
        ) for ev in si.evidence])
        
        return FaultHypothesis(
            fault_id=f"{sensor_name}_SENSOR_FAULT",
            fault_name=f"{sensor_name} Sensor Fault ({si.fault_type})",
            category=FaultCategory.SENSOR,
            confidence=round(min(confidence, 0.98), 3),
            severity=round(1.0 - si.integrity_score, 3),
            severity_label=FaultSeverity.from_value(1.0 - si.integrity_score),
            subsystem="SENSORS",
            affected_components=[sensor_name],
            evidence=evidence,
        )

    def _get_correlated_channels(self, sensor_name: str) -> list[str]:
        """Get channels physically correlated with a given sensor."""
        correlations = {
            "EGT1": ["CHT1", "FUEL_FLOW", "VIBRATION"],
            "EGT2": ["CHT2", "FUEL_FLOW", "VIBRATION"],
            "EGT3": ["CHT3", "FUEL_FLOW", "VIBRATION"],
            "EGT4": ["CHT4", "FUEL_FLOW", "VIBRATION"],
            "CHT1": ["EGT1", "VIBRATION"],
            "CHT2": ["EGT2", "VIBRATION"],
            "CHT3": ["EGT3", "VIBRATION"],
            "CHT4": ["EGT4", "VIBRATION"],
            "OIL_PRESSURE": ["OIL_TEMP", "VIBRATION", "RPM"],
            "OIL_TEMP": ["OIL_PRESSURE", "RPM"],
            "VIBRATION": ["OIL_PRESSURE", "RPM"],
            "MAP": ["TURBO_BOOST", "RPM", "FUEL_FLOW"],
            "TURBO_BOOST": ["MAP", "RPM"],
            "RPM": ["MAP", "FUEL_FLOW", "VIBRATION"],
            "FUEL_FLOW": ["RPM", "MAP"],
            "BUS_VOLTAGE": ["RPM"],
        }
        return correlations.get(sensor_name, [])

    def _match_signature(self, fault_name: str, signature: dict,
                         patterns: dict, residuals: dict, raw_residuals: dict,
                         observed: dict, expected: dict) -> Optional[FaultHypothesis]:
        """Match a fault signature against current patterns."""
        score = 0.0
        max_score = 0.0
        evidence_items = []
        
        # Check required patterns
        for req in signature["required"]:
            max_score += 2.0
            matched, ev = self._check_pattern(req, patterns, residuals, raw_residuals, observed, expected)
            if matched:
                score += 2.0
                evidence_items.append(ev)
            else:
                # Required pattern not met — greatly reduce confidence
                score -= 1.0
        
        # Check supporting patterns
        for sup in signature["supporting"]:
            max_score += 1.0
            matched, ev = self._check_pattern(sup, patterns, residuals, raw_residuals, observed, expected)
            if matched:
                score += 1.0
                evidence_items.append(ev)
        
        # Check contradicting patterns
        for contra in signature.get("contradicting", []):
            matched, ev = self._check_pattern(contra, patterns, residuals, raw_residuals, observed, expected)
            if matched:
                score -= 1.5
        
        if max_score <= 0:
            return None
        
        confidence = max(0.0, score / max_score)
        
        if confidence < 0.15:
            return None
        
        # Severity from residual magnitude
        relevant_residuals = [abs(residuals.get(ch, 0)) for ch in signature.get("affected_components", [])[:3]]
        if not relevant_residuals:
            relevant_residuals = [abs(v) for v in residuals.values()]
        avg_magnitude = np.mean(relevant_residuals) if relevant_residuals else 0
        severity = min(avg_magnitude / 8.0, 1.0)
        
        return FaultHypothesis(
            fault_id=fault_name,
            fault_name=fault_name.replace("_", " ").title(),
            category=signature["category"],
            confidence=round(min(confidence, 0.98), 3),
            severity=round(severity, 3),
            severity_label=FaultSeverity.from_value(severity),
            subsystem=signature["subsystem"],
            affected_components=signature["affected_components"],
            evidence=evidence_items,
        )

    def _check_pattern(self, pattern: str, patterns: dict, residuals: dict,
                       raw_residuals: dict, observed: dict, expected: dict) -> tuple[bool, Optional[EvidenceItem]]:
        """Check if a specific pattern is present."""
        if pattern == "EGT_HIGH":
            val = patterns.get("EGT_MAX", 0)
            if val > 3.0:
                ch = patterns.get("EGT_MAX_CHANNEL", "EGT")
                return True, EvidenceItem(
                    category="OBSERVATION",
                    description=f"EGT elevated on {ch} (residual: {val:.1f}σ)",
                    signal_name=ch, deviation_sigma=val, weight=1.0,
                )
        elif pattern == "EGT_LOW_SINGLE":
            egt_res = {k: v for k, v in residuals.items() if k.startswith("EGT")}
            for ch, v in egt_res.items():
                if v < -3.0:
                    return True, EvidenceItem(
                        category="OBSERVATION",
                        description=f"EGT low on {ch} (residual: {v:.1f}σ) — possible misfire",
                        signal_name=ch, deviation_sigma=v, weight=1.0,
                    )
        elif pattern == "CHT_HIGH":
            val = patterns.get("CHT_MAX", 0)
            if val > 3.0:
                return True, EvidenceItem(
                    category="OBSERVATION",
                    description=f"CHT elevated (residual: {val:.1f}σ)",
                    deviation_sigma=val, weight=1.0,
                )
        elif pattern == "CHT_CHANGE":
            val = patterns.get("CHT_MEAN", 0)
            if abs(val) > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"CHT shows correlated change (mean residual: {val:.1f}σ)",
                    deviation_sigma=val, weight=0.7,
                )
        elif pattern == "OIL_PRESSURE_LOW":
            val = patterns.get("OIL_PRESSURE_RESIDUAL", 0)
            if val < -3.0:
                return True, EvidenceItem(
                    category="OBSERVATION",
                    description=f"Oil pressure below expected (residual: {val:.1f}σ)",
                    signal_name="OIL_PRESSURE", deviation_sigma=val, weight=1.0,
                )
        elif pattern == "OIL_TEMP_HIGH":
            val = patterns.get("OIL_TEMP_RESIDUAL", 0)
            if val > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Oil temperature elevated (residual: {val:.1f}σ)",
                    signal_name="OIL_TEMP", deviation_sigma=val, weight=0.8,
                )
        elif pattern == "OIL_PRESSURE_CHANGE":
            val = patterns.get("OIL_PRESSURE_RESIDUAL", 0)
            if abs(val) > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Oil pressure change detected (residual: {val:.1f}σ)",
                    weight=0.6,
                )
        elif pattern == "VIBRATION_HIGH":
            val = patterns.get("VIBRATION_RESIDUAL", 0)
            if val > 3.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Vibration elevated (residual: {val:.1f}σ)",
                    signal_name="VIBRATION", deviation_sigma=val, weight=0.9,
                )
        elif pattern == "VIBRATION_NORMAL":
            val = patterns.get("VIBRATION_RESIDUAL", 0)
            if abs(val) < 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description="Vibration remains normal — supports localized thermal fault",
                    weight=0.5,
                )
        elif pattern == "VIBRATION_CHANGE":
            val = patterns.get("VIBRATION_RESIDUAL", 0)
            if abs(val) > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Vibration changed (residual: {val:.1f}σ)",
                    weight=0.6,
                )
        elif pattern == "TURBO_BOOST_LOW":
            val = patterns.get("TURBO_RESIDUAL", 0)
            if val < -3.0:
                return True, EvidenceItem(
                    category="OBSERVATION",
                    description=f"Turbo boost below expected (residual: {val:.1f}σ)",
                    signal_name="TURBO_BOOST", deviation_sigma=val, weight=1.0,
                )
        elif pattern == "MAP_LOW":
            val = patterns.get("MAP_RESIDUAL", 0)
            if val < -2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Manifold pressure reduced (residual: {val:.1f}σ)",
                    weight=0.7,
                )
        elif pattern == "FUEL_FLOW_LOW":
            val = patterns.get("FUEL_FLOW_RESIDUAL", 0)
            if val < -2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Fuel flow below expected (residual: {val:.1f}σ)",
                    weight=0.7,
                )
        elif pattern == "FUEL_FLOW_HIGH":
            val = patterns.get("FUEL_FLOW_RESIDUAL", 0)
            if val > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description=f"Fuel flow above expected (residual: {val:.1f}σ)",
                    weight=0.7,
                )
        elif pattern == "POWER_LOW":
            val = patterns.get("RPM_RESIDUAL", 0)
            if val < -2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description="RPM/power below expected",
                    weight=0.5,
                )
        elif pattern == "RPM_ROUGH":
            val = patterns.get("RPM_RESIDUAL", 0)
            if abs(val) > 2.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description="RPM instability detected",
                    weight=0.5,
                )
        elif pattern == "SINGLE_SENSOR_ONLY":
            # Check if only one sensor channel is anomalous
            anomalous = [ch for ch, r in residuals.items() if abs(r) > 3.0]
            if len(anomalous) == 1:
                return True, EvidenceItem(
                    category="SENSOR_CHECK",
                    description=f"Only {anomalous[0]} is anomalous — suggests sensor fault",
                    weight=1.0,
                )
        elif pattern == "EGT_NORMAL_OR_SLIGHT":
            val = abs(patterns.get("EGT_MEAN", 0))
            if val < 3.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description="EGT near normal — supports cooling-only fault",
                    weight=0.5,
                )
        elif pattern == "ALL_CHT_HIGH":
            val = patterns.get("CHT_STD", 0)
            if val < 1.0 and patterns.get("CHT_MEAN", 0) > 3.0:
                return True, EvidenceItem(
                    category="CORRELATION",
                    description="All CHT elevated uniformly — less likely single-cylinder cooling fault",
                    weight=0.7,
                )
        
        return False, None

    def _build_observation(self, anomaly: AnomalyResult, residuals: dict, raw_residuals: dict) -> str:
        top_channels = sorted(residuals.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        parts = [f"{ch}: {raw_residuals.get(ch, 0):.1f} ({r:.1f}σ)" for ch, r in top_channels]
        return f"Anomaly detected — top deviations: {'; '.join(parts)}"

    def _build_physics_evidence(self, primary: Optional[FaultHypothesis], residuals: dict, expected: dict) -> str:
        if not primary:
            return "No physics evidence"
        physics_ev = [e for e in primary.evidence if e.category in ("OBSERVATION", "PHYSICS")]
        if physics_ev:
            return "; ".join(e.description for e in physics_ev[:3])
        return f"Residual pattern consistent with {primary.fault_name}"

    def _build_correlation_evidence(self, primary: Optional[FaultHypothesis], residuals: dict) -> str:
        if not primary:
            return "No correlated signals"
        corr_ev = [e for e in primary.evidence if e.category == "CORRELATION"]
        if corr_ev:
            return "; ".join(e.description for e in corr_ev[:3])
        return "No additional correlated signal evidence"

    def _build_summary(self, primary: Optional[FaultHypothesis], alternatives: list) -> str:
        if not primary:
            return "No fault diagnosed"
        summary = f"Primary: {primary.fault_name} (confidence: {primary.confidence:.0%})"
        if alternatives:
            alt_names = [f"{a.fault_name} ({a.confidence:.0%})" for a in alternatives[:2]]
            summary += f" | Alternatives: {', '.join(alt_names)}"
        return summary

    def _build_confidence_explanation(self, primary: Optional[FaultHypothesis]) -> str:
        if not primary:
            return ""
        n_evidence = len(primary.evidence)
        return (f"Confidence {primary.confidence:.0%} based on {n_evidence} evidence items. "
                f"{'High' if primary.confidence > 0.7 else 'Moderate' if primary.confidence > 0.4 else 'Low'} "
                f"match with {primary.fault_name} signature.")

    def _build_severity_explanation(self, primary: Optional[FaultHypothesis], anomaly: AnomalyResult) -> str:
        if not primary:
            return ""
        return (f"Severity: {primary.severity_label.value} ({primary.severity:.2f}). "
                f"Anomaly score: {anomaly.anomaly_score:.2f}, persistence: {anomaly.persistence} frames.")

    def _build_mission_consequence(self, primary: Optional[FaultHypothesis]) -> str:
        if not primary or primary.severity < 0.3:
            return "No significant mission impact expected"
        consequences = {
            "COMBUSTION": "Combustion fault may reduce available power and increase thermal stress during climb/cruise",
            "COOLING": "Cooling degradation increases thermal risk during high-power phases (takeoff, climb)",
            "LUBRICATION": "Lubrication fault increases bearing wear risk during extended cruise",
            "TURBO": "Turbo deficiency reduces altitude capability and power margin",
            "MECHANICAL": "Mechanical fault may worsen with continued operation",
            "SENSORS": "Sensor fault reduces monitoring confidence but does not directly affect engine",
        }
        return consequences.get(primary.subsystem, "Monitor for mission impact")

    def _build_recommendation(self, primary: Optional[FaultHypothesis], anomaly: AnomalyResult) -> str:
        if not primary:
            return "CONTINUE"
        if primary.category == FaultCategory.SENSOR:
            if primary.severity > 0.7:
                return "MONITOR — sensor fault detected, cross-check with redundant data"
            return "CONTINUE — minor sensor anomaly, monitoring"
        if primary.severity > 0.8:
            return "RETURN_TO_BASE — critical engine fault detected"
        if primary.severity > 0.6:
            return "REDUCE_LOAD — significant fault, minimize engine stress"
        if primary.severity > 0.4:
            return "MONITOR — moderate fault detected, assess mission risk"
        return "CONTINUE — minor fault, monitoring"

    def reset(self):
        self.last_diagnosis = None
        self.diagnosis_history.clear()
