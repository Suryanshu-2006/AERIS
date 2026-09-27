"""
Readiness Assessment
Determines if the engine is ready for a given mission based on health,
degradation, and mission requirements.
"""
from ..schemas.engine import HealthScores, MissionSafeHorizon
from ..schemas.mission import MissionProfile


class ReadinessAssessor:
    """Determines engine readiness for a mission."""

    HEALTH_THRESHOLDS = {
        "go": 75.0,
        "caution": 50.0,
        "no_go": 25.0,
    }

    def assess(self, health: HealthScores, mission: MissionProfile,
               safe_horizon: MissionSafeHorizon) -> dict:
        """
        Returns readiness assessment with go/no-go recommendation.
        """
        issues = []
        
        # Check each subsystem
        for subsystem in ["combustion", "cooling", "lubrication", "turbo", "mechanical", "electrical"]:
            score = getattr(health, subsystem)
            if score < self.HEALTH_THRESHOLDS["no_go"]:
                issues.append(f"{subsystem.upper()} critically degraded ({score:.0f}%) — NO GO")
            elif score < self.HEALTH_THRESHOLDS["caution"]:
                issues.append(f"{subsystem.upper()} degraded ({score:.0f}%) — CAUTION")
        
        # Check safe horizon vs mission duration
        if safe_horizon.safe_hours < mission.total_duration_hours:
            issues.append(
                f"Safe horizon ({safe_horizon.safe_hours:.1f}h) < mission duration "
                f"({mission.total_duration_hours:.1f}h) — RISK"
            )
        
        # Determine readiness
        critical_issues = [i for i in issues if "NO GO" in i]
        caution_issues = [i for i in issues if "CAUTION" in i or "RISK" in i]
        
        if critical_issues:
            readiness = "NOT_READY"
            recommendation = "INSPECT_BEFORE_NEXT_MISSION"
        elif caution_issues:
            readiness = "CAUTION"
            recommendation = "MONITOR"
        else:
            readiness = "READY"
            recommendation = "CONTINUE"
        
        return {
            "readiness": readiness,
            "recommendation": recommendation,
            "issues": issues,
            "overall_health": health.engine,
            "safe_horizon_hours": safe_horizon.safe_hours,
            "mission_duration_hours": mission.total_duration_hours,
        }
