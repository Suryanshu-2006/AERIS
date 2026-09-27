"""API routes for mission management and what-if simulation."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..core.orchestrator import get_orchestrator
from ..schemas.mission import WhatIfRequest

router = APIRouter()


class MissionCreateRequest(BaseModel):
    name: str = "Custom Mission"
    phases: list[dict] = []
    payload_kg: float = 50.0
    ambient_temp_c: float = 15.0


@router.get("/mission")
async def get_mission():
    return get_orchestrator().get_mission_info()


@router.post("/mission/create")
async def create_mission(req: MissionCreateRequest):
    orch = get_orchestrator()
    mission = orch.mission_model.create_mission(
        name=req.name, phases=req.phases,
        payload_kg=req.payload_kg, ambient_temp_c=req.ambient_temp_c,
    )
    return {"status": "created", "mission": orch.mission_model.get_mission_summary(mission.mission_id)}


@router.post("/mission/simulate")
async def simulate_mission():
    orch = get_orchestrator()
    # Run what-if with current parameters (no changes = baseline)
    result = orch.run_what_if(WhatIfRequest())
    return result


@router.post("/mission/what-if")
async def what_if_simulation(req: WhatIfRequest):
    """Run counterfactual what-if simulation."""
    return get_orchestrator().run_what_if(req)
