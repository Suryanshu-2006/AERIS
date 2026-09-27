"""API routes for health, diagnosis, and prognostics."""
from fastapi import APIRouter
from ..core.orchestrator import get_orchestrator

router = APIRouter()


@router.get("/health")
async def get_health():
    orch = get_orchestrator()
    return {
        "health": orch.get_health(),
        "rul": orch.state_manager.engine_rul.model_dump() if orch.state_manager.engine_rul else {},
        "safe_horizon": orch.state_manager.mission_safe_horizon.model_dump() if orch.state_manager.mission_safe_horizon else {},
        "degradation": {
            comp: {"level": state.degradation_level, "rate": state.rate_per_hour, "hours": state.accumulated_hours}
            for comp, state in orch.degradation_tracker.states.items()
        },
    }


@router.get("/diagnosis")
async def get_diagnosis():
    orch = get_orchestrator()
    return {
        "diagnosis": orch.get_diagnosis(),
        "evidence_chain": orch.state_manager.evidence_chain,
        "recommendation": orch.state_manager.recommendation,
        "anomaly_history": list(orch.state_manager.anomaly_history)[-50:],
    }


@router.get("/replay")
async def get_replay_data():
    """Get data for timeline replay."""
    orch = get_orchestrator()
    return {
        "telemetry": orch.state_manager.get_telemetry_history(),
        "health": orch.state_manager.get_health_history(),
        "anomalies": list(orch.state_manager.anomaly_history),
        "diagnoses": list(orch.state_manager.diagnosis_history),
        "simulation_time": orch.simulation_time,
    }
