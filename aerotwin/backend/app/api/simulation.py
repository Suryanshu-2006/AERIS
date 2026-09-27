"""API routes for simulation control."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..core.orchestrator import get_orchestrator

router = APIRouter()


class SpeedRequest(BaseModel):
    speed: float = 1.0


class ScenarioRequest(BaseModel):
    scenario_id: str = ""


@router.post("/simulation/start")
@router.post("/sim/start")
async def start_simulation():
    orch = get_orchestrator()
    await orch.start()
    return {"status": "started", "simulation_id": orch.state_manager.simulation_id}


@router.post("/simulation/pause")
@router.post("/sim/pause")
async def pause_simulation():
    get_orchestrator().pause()
    return {"status": "paused"}


@router.post("/simulation/resume")
@router.post("/sim/resume")
async def resume_simulation():
    get_orchestrator().resume()
    return {"status": "resumed"}


@router.post("/simulation/reset")
@router.post("/sim/reset")
async def reset_simulation():
    orch = get_orchestrator()
    await orch.stop()
    orch.reset()
    await orch.start()
    return {"status": "reset", "simulation_id": orch.state_manager.simulation_id}


@router.post("/simulation/speed")
@router.post("/sim/speed")
async def set_speed(req: SpeedRequest):
    get_orchestrator().set_speed(req.speed)
    return {"status": "speed_set", "speed": req.speed}


@router.get("/scenarios")
async def list_scenarios():
    """List available predefined scenarios."""
    from ..data.scenarios import SCENARIOS
    return {"scenarios": [
        {"id": s.scenario_id, "name": s.name, "description": s.description}
        for s in SCENARIOS.values()
    ]}


@router.post("/simulation/scenario")
@router.post("/sim/scenario")
async def load_scenario(req: ScenarioRequest):
    """Load and run a predefined scenario."""
    from ..data.scenarios import SCENARIOS, apply_scenario
    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        return {"error": f"Scenario {req.scenario_id} not found"}
    
    orch = get_orchestrator()
    await orch.stop()
    orch.reset()
    apply_scenario(orch, scenario)
    orch.state_manager.scenario_id = req.scenario_id
    await orch.start()
    return {"status": "scenario_loaded", "scenario": req.scenario_id}


@router.post("/sim/scenario/{scenario_id}")
async def load_scenario_by_path(scenario_id: str):
    """Load scenario by URL path parameter."""
    return await load_scenario(ScenarioRequest(scenario_id=scenario_id))
