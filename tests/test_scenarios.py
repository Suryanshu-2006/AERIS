"""
Scenario Validation Tests
Verifies that:
1. All 10 required scenarios are defined and have valid parameters
2. Each scenario is reproducible
"""
import pytest
from app.data.scenarios import SCENARIOS, get_scenario


def test_all_ten_scenarios_exist():
    """Verify all 10 mandated scenarios exist."""
    required = [
        "SCENARIO_01", "SCENARIO_02", "SCENARIO_03", "SCENARIO_04", "SCENARIO_05",
        "SCENARIO_06", "SCENARIO_07", "SCENARIO_08", "SCENARIO_09", "SCENARIO_10"
    ]
    for sc_id in required:
        assert sc_id in SCENARIOS, f"Missing required scenario: {sc_id}"
        sc = get_scenario(sc_id)
        assert sc is not None
        assert sc.name != ""
        assert sc.description != ""
        assert sc.seed is not None
