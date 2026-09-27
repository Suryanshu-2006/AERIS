"""API routes for telemetry data."""
from fastapi import APIRouter
from ..core.orchestrator import get_orchestrator

router = APIRouter()


@router.get("/state")
@router.get("/telemetry/state")
async def get_state():
    """Get complete system state snapshot."""
    return get_orchestrator().get_state()


@router.get("/telemetry/history")
async def get_telemetry_history():
    """Get recent telemetry history."""
    return get_orchestrator().state_manager.get_telemetry_history()


@router.get("/telemetry/residuals")
async def get_residuals():
    """Get current residuals with statistics."""
    orch = get_orchestrator()
    return {
        "residuals": orch.state_manager.residuals,
        "details": orch.state_manager.residual_details,
        "drift": orch.state_manager.drift_info,
    }
