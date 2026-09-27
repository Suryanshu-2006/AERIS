"""
Explainer Module
Generates human-readable explanations and structured summaries of system state.
"""
from ..schemas.engine import HealthScores, RULEstimate, MissionSafeHorizon
from ..schemas.diagnosis import DiagnosisResult


class Explainer:
    """Generates natural-language explanations of system state and predictions."""

    @staticmethod
    def explain_health(scores: HealthScores) -> str:
        overall = scores.engine
        weakest_name = ""
        weakest_score = 100.0
        for name in ["combustion", "cooling", "lubrication", "turbo", "mechanical", "electrical", "sensors"]:
            s = getattr(scores, name)
            if s < weakest_score:
                weakest_score = s
                weakest_name = name
        
        if overall > 90:
            status = "Engine health is excellent"
        elif overall > 75:
            status = "Engine health is good with minor concerns"
        elif overall > 50:
            status = f"Engine health is degraded — {weakest_name} subsystem at {weakest_score:.0f}%"
        elif overall > 25:
            status = f"Engine health is poor — {weakest_name} subsystem critically degraded at {weakest_score:.0f}%"
        else:
            status = f"Engine health is critical — {weakest_name} subsystem near failure at {weakest_score:.0f}%"
        
        return status

    @staticmethod
    def explain_rul(rul: RULEstimate, safe_horizon: MissionSafeHorizon = None) -> str:
        parts = [f"Estimated engine RUL: {rul.rul_hours:.1f} hours "
                 f"(range: {rul.lower_bound_hours:.1f}-{rul.upper_bound_hours:.1f}h, "
                 f"confidence: {rul.confidence:.0%})"]
        
        if safe_horizon:
            parts.append(
                f"Mission-safe horizon: {safe_horizon.safe_hours:.1f} hours — "
                f"limited by {safe_horizon.limiting_factor}"
            )
            if safe_horizon.safe_hours < rul.rul_hours * 0.5:
                parts.append(
                    "⚠ Mission conditions significantly reduce safe operating time "
                    "compared to baseline RUL"
                )
        
        parts.append("Note: All RUL values are model estimates, not certified predictions")
        return " | ".join(parts)

    @staticmethod
    def explain_diagnosis(diagnosis: DiagnosisResult) -> dict:
        """Generate structured explanation dict for frontend."""
        result = {
            "status": "HEALTHY" if not diagnosis.primary_fault else diagnosis.primary_fault.severity_label.value,
            "summary": diagnosis.diagnosis_summary,
            "observation": diagnosis.observation,
            "physics_evidence": diagnosis.physics_evidence,
            "correlated_signals": diagnosis.correlated_signals,
            "confidence": diagnosis.confidence_explanation,
            "severity": diagnosis.severity_explanation,
            "mission_impact": diagnosis.mission_consequence,
            "recommendation": diagnosis.recommendation,
            "anomaly_score": diagnosis.anomaly.anomaly_score,
            "anomaly_persistent": diagnosis.anomaly.persistence > 5,
        }
        
        if diagnosis.primary_fault:
            result["primary_fault"] = {
                "name": diagnosis.primary_fault.fault_name,
                "category": diagnosis.primary_fault.category.value,
                "confidence": diagnosis.primary_fault.confidence,
                "severity": diagnosis.primary_fault.severity,
                "subsystem": diagnosis.primary_fault.subsystem,
                "components": diagnosis.primary_fault.affected_components,
            }
        
        if diagnosis.alternative_hypotheses:
            result["alternatives"] = [
                {
                    "name": h.fault_name,
                    "confidence": h.confidence,
                    "category": h.category.value,
                }
                for h in diagnosis.alternative_hypotheses[:3]
            ]
        
        return result
