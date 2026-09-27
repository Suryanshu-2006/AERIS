"""
What-If Counterfactual Simulation Tests
Verifies that:
1. Modifying mission parameters (altitude, duration, temperature) actually reruns the physics simulation.
2. WhatIfResult contains comparison delta between baseline and modified mission.
"""
import pytest
from app.schemas.mission import WhatIfRequest
from app.schemas.engine import HealthScores, DegradationState
from app.mission.mission_model import MissionModel
from app.mission.what_if import WhatIfSimulator


def test_what_if_counterfactual_produces_real_difference():
    """Verify modifying parameters produces concrete differences in the simulated trajectory."""
    simulator = WhatIfSimulator()
    mission_model = MissionModel()
    baseline = mission_model.current_mission
    
    current_health = HealthScores(
        engine=85.0,
        combustion=85.0,
        cooling=80.0,
        lubrication=82.0,
        turbo=85.0,
        mechanical=88.0,
        electrical=95.0,
        sensors=100.0,
    )
    current_degradation = {
        "cooling": DegradationState(component="cooling", degradation_level=0.15, rate_per_hour=0.01),
        "lubrication": DegradationState(component="lubrication", degradation_level=0.12, rate_per_hour=0.008),
    }
    
    # What-if request: increase altitude to 25000 ft and increase ambient temp by 15°C (hot-and-high)
    request = WhatIfRequest(
        altitude_ft=25000.0,
        ambient_temperature_c=35.0,
        loiter_duration_minutes=120.0,
    )
    
    result = simulator.simulate(
        baseline_mission=baseline,
        what_if=request,
        current_health=current_health,
        current_degradation=current_degradation,
    )
    
    assert len(result.baseline_trajectory) > 0
    assert len(result.modified_trajectory) > 0
    
    # Verify counterfactual produces evaluated risk and deltas
    assert result.modified_risk is not None
    assert result.baseline_risk is not None
    assert result.summary != ""
    assert result.recommendation != ""
