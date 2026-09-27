"""
Evidence Chain Builder
Constructs complete evidence chains for each diagnosis, from observation
through physics evidence, correlation, diagnosis, and mission consequence.
"""
from ..schemas.diagnosis import DiagnosisResult, EvidenceItem, Recommendation


class EvidenceChainBuilder:
    """
    Builds human-readable evidence chains:
    
    OBSERVATION → PHYSICS EVIDENCE → CORRELATED SIGNALS →
    DIAGNOSIS → CONFIDENCE → SEVERITY → MISSION CONSEQUENCE → RECOMMENDATION
    """

    def build_chain(self, diagnosis: DiagnosisResult) -> dict:
        """Build a complete evidence chain from a diagnosis result."""
        chain = {
            "observation": diagnosis.observation or "No anomaly observed",
            "physics_evidence": diagnosis.physics_evidence or "No physics evidence",
            "correlated_signals": diagnosis.correlated_signals or "No correlation data",
            "diagnosis": diagnosis.diagnosis_summary or "No diagnosis",
            "confidence": diagnosis.confidence_explanation or "",
            "severity": diagnosis.severity_explanation or "",
            "mission_consequence": diagnosis.mission_consequence or "No mission impact",
            "recommendation": diagnosis.recommendation or "CONTINUE",
            "evidence_items": [],
        }
        
        # Collect all evidence from primary fault
        if diagnosis.primary_fault:
            for ev in diagnosis.primary_fault.evidence:
                chain["evidence_items"].append({
                    "category": ev.category,
                    "description": ev.description,
                    "signal": ev.signal_name,
                    "deviation_sigma": ev.deviation_sigma,
                    "supports": ev.supports_hypothesis,
                    "weight": ev.weight,
                })
        
        # Sensor integrity summary
        faulty_sensors = [si for si in diagnosis.sensor_integrity if si.is_faulty]
        if faulty_sensors:
            chain["sensor_warnings"] = [
                f"{si.sensor_name}: {si.fault_type} (integrity: {si.integrity_score:.2f})"
                for si in faulty_sensors
            ]
        else:
            chain["sensor_warnings"] = []
        
        return chain

    def generate_recommendation(self, diagnosis: DiagnosisResult,
                                 mission_risk: float = 0.0,
                                 safe_horizon_hours: float = 999.0) -> str:
        """Generate operator recommendation based on all evidence."""
        if not diagnosis.primary_fault:
            if mission_risk < 0.3:
                return Recommendation.CONTINUE.value
            return Recommendation.MONITOR.value
        
        severity = diagnosis.primary_fault.severity
        is_sensor = diagnosis.primary_fault.category.value == "SENSOR"
        
        if is_sensor:
            if severity > 0.7:
                return Recommendation.MONITOR.value
            return Recommendation.CONTINUE.value
        
        # Physical fault recommendations
        if severity > 0.8 or safe_horizon_hours < 1.0:
            return Recommendation.RETURN_TO_BASE.value
        if severity > 0.6 or safe_horizon_hours < 3.0:
            return Recommendation.REDUCE_LOAD.value
        if severity > 0.4 or mission_risk > 0.6:
            return Recommendation.SHORTEN_LOITER.value
        if severity > 0.2:
            return Recommendation.INSPECT_BEFORE_NEXT.value
        return Recommendation.CONTINUE.value
