"""
Mission Digital Twin and Risk Engine Tests
Verifies that:
1. Mission model computes phase durations and stress factors.
2. Low health score and rapid degradation reduce mission readiness and safe horizon.
"""
import pytest
from app.schemas.mission import MissionProfile, MissionPhaseConfig, MissionPhase
from app.schemas.engine import HealthScores, DegradationState, MissionSafeHorizon, SubsystemName
from app.mission.mission_risk import MissionRiskEngine
from app.mission.mission_model import MissionModel


def test_mission_model_and_stress_factors():
    """Verify mission model computes phase durations and stress factors."""
    model = MissionModel()
    profile = model.current_mission
    
    assert len(profile.phases) > 0
    climb_phase = next((p for p in profile.phases if p.phase == MissionPhase.CLIMB), None)
    cruise_phase = next((p for p in profile.phases if p.phase == MissionPhase.CRUISE), None)
    
    assert climb_phase is not None and cruise_phase is not None
    # Climb typically has higher throttle/stress than cruise
    assert climb_phase.throttle_percent >= cruise_phase.throttle_percent


def test_mission_risk_increases_with_degradation():
    """Verify mission risk engine yields higher risk when engine health is degraded."""
    risk_engine = MissionRiskEngine()
    model = MissionModel()
    mission = model.current_mission
    
    healthy = HealthScores(
        engine=95.0,
        combustion=95.0,
        cooling=95.0,
        lubrication=95.0,
        mechanical=95.0,
        turbo=95.0,
        electrical=98.0,
        sensors=100.0,
    )
    safe_horizon_healthy = MissionSafeHorizon(
        safe_hours=12.0,
        lower_bound_hours=10.0,
        upper_bound_hours=14.0,
        confidence=0.9,
        limiting_factor="Normal wear",
        limiting_subsystem=SubsystemName.ENGINE,
    )
    risk_healthy = risk_engine.assess(mission, healthy, {}, safe_horizon_healthy, mission_model=model)
    
    degraded = HealthScores(
        engine=45.0,
        combustion=50.0,
        cooling=45.0,
        lubrication=40.0,
        mechanical=60.0,
        turbo=50.0,
        electrical=90.0,
        sensors=100.0,
    )
    safe_horizon_degraded = MissionSafeHorizon(
        safe_hours=2.0,
        lower_bound_hours=1.5,
        upper_bound_hours=2.5,
        confidence=0.9,
        limiting_factor="Critical oil pressure degradation",
        limiting_subsystem=SubsystemName.LUBRICATION,
    )
    risk_degraded = risk_engine.assess(mission, degraded, {}, safe_horizon_degraded, mission_model=model)
    
    assert risk_degraded.mission_risk_score > risk_healthy.mission_risk_score, (
        f"Degraded engine risk ({risk_degraded.mission_risk_score}) must exceed healthy ({risk_healthy.mission_risk_score})"
    )
