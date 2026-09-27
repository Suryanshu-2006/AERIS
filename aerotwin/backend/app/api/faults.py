"""API routes for fault injection and management."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..core.orchestrator import get_orchestrator

router = APIRouter()


class FaultInjectRequest(BaseModel):
    fault_id: str
    severity: Optional[float] = None
    duration: float = 9999.0


class FaultClearRequest(BaseModel):
    fault_id: str


@router.get("/faults")
async def list_faults():
    return {"available_faults": get_orchestrator().get_available_faults()}


@router.get("/faults/active")
async def active_faults():
    orch = get_orchestrator()
    return {"active_faults": orch.state_manager.active_faults}


@router.post("/fault/inject")
@router.post("/faults/inject")
async def inject_fault(req: FaultInjectRequest):
    result = get_orchestrator().inject_fault(
        req.fault_id, req.severity, duration=req.duration
    )
    if result:
        return {"status": "injected", "fault": result}
    return {"error": f"Unknown fault: {req.fault_id}"}


@router.post("/fault/clear")
@router.post("/faults/clear")
async def clear_fault(req: FaultClearRequest):
    get_orchestrator().clear_fault(req.fault_id)
    return {"status": "cleared", "fault_id": req.fault_id}


@router.post("/fault/clear-all")
@router.post("/faults/clear-all")
async def clear_all_faults():
    get_orchestrator().clear_all_faults()
    return {"status": "all_cleared"}
