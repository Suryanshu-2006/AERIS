"""
Mission Risk Engine
Calculates mission risk using engine health, fault severity, predicted degradation,
mission duration, altitude, thermal load, and remaining safe horizon.
"""
import numpy as np
from ..schemas.mission import MissionRiskResult, MissionProfile, MissionPhase
from ..schemas.engine import HealthScores, DegradationState, MissionSafeHorizon
from .mission_model import MissionModel


class MissionRiskEngine:
    """
    Computes mission risk score and readiness.
    
    Risk is derived from:
    - Engine health scores
    - Fault severity
    - Predicted degradation over mission duration
    - Mission altitude and duration
    - Thermal load profile
    - Remaining safe horizon
    """

    def __init__(self):
        self.last_result: MissionRiskResult = None

    def assess(self, mission: MissionProfile,
               health: HealthScores,
               degradation: dict[str, DegradationState],
               safe_horizon: MissionSafeHorizon,
               fault_severity: float = 0.0,
               fault_subsystem: str = "",
               mission_model: MissionModel = None) -> MissionRiskResult:
        """
        Comprehensive mission risk assessment.
        """
        # Per-phase risk analysis
        phase_risks = []
        max_phase_risk = 0.0
        critical_phase = ""
        
        for phase_cfg in mission.phases:
            phase = phase_cfg.phase
            alt = phase_cfg.altitude_ft
            throttle = phase_cfg.throttle_percent / 100.0
            duration_h = phase_cfg.duration_minutes / 60.0
            
            # Compute phase stress
            stress = 1.0
            if mission_model:
                stress = mission_model.get_phase_stress_factor(
                    phase, alt, throttle, mission.ambient_temperature_c
                )
            
            # Phase risk components
            health_risk = max(0, (100 - health.engine) / 100.0)
            thermal_risk = self._thermal_risk(alt, throttle, health.cooling)
            lub_risk = self._lubrication_risk(duration_h, health.lubrication)
            mech_risk = self._mechanical_risk(health.mechanical, stress)
            
            # Combined phase risk
            phase_risk = (
                health_risk * 0.3 +
                thermal_risk * 0.25 +
                lub_risk * 0.2 +
                mech_risk * 0.15 +
                fault_severity * 0.1
            ) * stress / 2.0
            
            phase_risk = min(phase_risk, 1.0)
            
            phase_risks.append({
                "phase": phase.value,
                "risk": round(phase_risk, 3),
                "altitude_ft": alt,
                "throttle": throttle,
                "duration_h": duration_h,
                "stress_factor": round(stress, 2),
            })
            
            if phase_risk > max_phase_risk:
                max_phase_risk = phase_risk
                critical_phase = phase.value
        
        # Overall mission risk
        if phase_risks:
            avg_risk = np.mean([p["risk"] for p in phase_risks])
            mission_risk = 0.6 * max_phase_risk + 0.4 * avg_risk
        else:
            mission_risk = 0.0
        
        # Safe horizon contribution
        if safe_horizon.safe_hours < mission.total_duration_hours:
            horizon_penalty = min(
                (mission.total_duration_hours - safe_horizon.safe_hours) /
                max(mission.total_duration_hours, 0.1), 0.5
            )
            mission_risk += horizon_penalty
        
        # Fault contribution
        if fault_severity > 0.3:
            mission_risk += fault_severity * 0.2
        
        mission_risk = float(np.clip(mission_risk, 0.0, 1.0))
        
        # Determine readiness
        if mission_risk < 0.2:
            readiness = "READY"
        elif mission_risk < 0.4:
            readiness = "CAUTION"
        elif mission_risk < 0.7:
            readiness = "WARNING"
        else:
            readiness = "NOT_READY"
        
        # Risk drivers
        risk_drivers = []
        if health.engine < 80:
            risk_drivers.append(f"Engine health at {health.engine:.0f}%")
        if fault_severity > 0.3:
            risk_drivers.append(f"Active fault severity: {fault_severity:.2f}")
        if safe_horizon.safe_hours < mission.total_duration_hours:
            risk_drivers.append(
                f"Safe horizon ({safe_horizon.safe_hours:.1f}h) shorter than mission ({mission.total_duration_hours:.1f}h)"
            )
        if mission.max_altitude_ft > 25000:
            risk_drivers.append(f"High altitude operation ({mission.max_altitude_ft:.0f} ft)")
        worst_deg = max(degradation.values(), key=lambda d: d.degradation_level) if degradation else None
        if worst_deg and worst_deg.degradation_level > 0.3:
            risk_drivers.append(f"{worst_deg.component} degradation at {worst_deg.degradation_level:.0%}")
        
        self.last_result = MissionRiskResult(
            mission_id=mission.mission_id,
            mission_risk_score=round(mission_risk, 3),
            mission_readiness=readiness,
            critical_phase=critical_phase,
            critical_phase_risk=round(max_phase_risk, 3),
            risk_drivers=risk_drivers,
            safe_horizon_hours=round(safe_horizon.safe_hours, 1),
            phase_risks=phase_risks,
            engine_health=health.engine,
            degradation_rate=round(worst_deg.rate_per_hour, 5) if worst_deg else 0.0,
            thermal_risk=round(self._thermal_risk(
                mission.max_altitude_ft, 0.65, health.cooling
            ), 3),
            lubrication_risk=round(self._lubrication_risk(
                mission.total_duration_hours, health.lubrication
            ), 3),
            mechanical_risk=round(self._mechanical_risk(health.mechanical, 1.0), 3),
        )
        
        return self.last_result

    def _thermal_risk(self, altitude_ft: float, throttle: float, cooling_health: float) -> float:
        """Compute thermal risk."""
        alt_factor = altitude_ft / 30000.0
        throttle_factor = throttle
        cooling_factor = max(0, (100 - cooling_health) / 100.0)
        return min((alt_factor * 0.3 + throttle_factor * 0.4 + cooling_factor * 0.3), 1.0)

    def _lubrication_risk(self, duration_h: float, lub_health: float) -> float:
        """Compute lubrication risk."""
        duration_factor = min(duration_h / 10.0, 1.0)
        health_factor = max(0, (100 - lub_health) / 100.0)
        return min(duration_factor * 0.4 + health_factor * 0.6, 1.0)

    def _mechanical_risk(self, mech_health: float, stress: float) -> float:
        """Compute mechanical risk."""
        health_factor = max(0, (100 - mech_health) / 100.0)
        return min(health_factor * stress, 1.0)
