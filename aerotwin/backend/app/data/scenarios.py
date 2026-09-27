"""
Predefined Scenarios
Reproducible test scenarios for validation and demonstration.
Each scenario has a seed, fault configuration, and mission profile.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scenario:
    scenario_id: str
    name: str
    description: str
    seed: int = 42
    faults: list[dict] = field(default_factory=list)
    fault_start_time: float = 60.0  # seconds after sim start
    mission_override: Optional[dict] = None


SCENARIOS = {
    "SCENARIO_01": Scenario(
        scenario_id="SCENARIO_01",
        name="Healthy Cruise",
        description="Normal engine operation during standard surveillance mission. No faults.",
        seed=42,
    ),
    "SCENARIO_02": Scenario(
        scenario_id="SCENARIO_02",
        name="Oil Pressure Degradation",
        description="Progressive oil pressure loss beginning at 60s simulation time.",
        seed=43,
        faults=[{"fault_id": "OIL_PRESSURE_LOSS", "severity": 0.6}],
        fault_start_time=60.0,
    ),
    "SCENARIO_03": Scenario(
        scenario_id="SCENARIO_03",
        name="Turbo Boost Deficiency",
        description="Turbocharger performance degradation.",
        seed=44,
        faults=[{"fault_id": "TURBO_BOOST_DEFICIENCY", "severity": 0.5}],
        fault_start_time=90.0,
    ),
    "SCENARIO_04": Scenario(
        scenario_id="SCENARIO_04",
        name="Cylinder Cooling Degradation",
        description="Cooling fin obstruction on cylinder 2, causing CHT rise.",
        seed=45,
        faults=[{"fault_id": "COOLING_DEGRADATION_CYL2", "severity": 0.6}],
        fault_start_time=45.0,
    ),
    "SCENARIO_05": Scenario(
        scenario_id="SCENARIO_05",
        name="Bearing Wear",
        description="Main bearing wear causing vibration increase and oil system stress.",
        seed=46,
        faults=[{"fault_id": "BEARING_WEAR", "severity": 0.5}],
        fault_start_time=60.0,
    ),
    "SCENARIO_06": Scenario(
        scenario_id="SCENARIO_06",
        name="EGT3 Sensor Fault",
        description="EGT3 sensor bias — should be identified as sensor fault, not engine fault.",
        seed=47,
        faults=[{"fault_id": "EGT3_BIAS", "severity": 0.6}],
        fault_start_time=30.0,
    ),
    "SCENARIO_07": Scenario(
        scenario_id="SCENARIO_07",
        name="Combined Sensor + Engine Anomaly",
        description="Oil pressure sensor bias AND bearing wear simultaneously.",
        seed=48,
        faults=[
            {"fault_id": "OIL_PRESSURE_SENSOR_BIAS", "severity": 0.4},
            {"fault_id": "BEARING_WEAR", "severity": 0.4},
        ],
        fault_start_time=45.0,
    ),
    "SCENARIO_08": Scenario(
        scenario_id="SCENARIO_08",
        name="Unknown Anomaly",
        description="Lean mixture on CYL3 at low severity — may not match known patterns clearly.",
        seed=49,
        faults=[{"fault_id": "LEAN_MIXTURE_CYL3", "severity": 0.25}],
        fault_start_time=60.0,
    ),
    "SCENARIO_09": Scenario(
        scenario_id="SCENARIO_09",
        name="High-Altitude Mission",
        description="Normal engine at high altitude (28000 ft) — tests thermal and turbo behavior.",
        seed=50,
        mission_override={"max_altitude_ft": 28000},
    ),
    "SCENARIO_10": Scenario(
        scenario_id="SCENARIO_10",
        name="Long-Duration Loiter Mission",
        description="Extended 3-hour loiter — tests degradation accumulation over time.",
        seed=51,
        mission_override={"loiter_duration_minutes": 180},
    ),
}


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    """Retrieve a scenario by its ID."""
    return SCENARIOS.get(scenario_id)


def apply_scenario(orchestrator, scenario: Scenario):
    """Apply a scenario to the orchestrator."""
    import numpy as np
    
    # Set seed
    orchestrator.sensor_model.rng = np.random.RandomState(scenario.seed)
    orchestrator.state_manager.scenario_id = scenario.scenario_id
    
    # Apply faults
    for fault_cfg in scenario.faults:
        orchestrator.inject_fault(
            fault_id=fault_cfg["fault_id"],
            severity=fault_cfg.get("severity"),
            start_time=scenario.fault_start_time,
            duration=fault_cfg.get("duration", float('inf')),
        )
    
    # Apply mission override
    if scenario.mission_override:
        override = scenario.mission_override
        mission = orchestrator.mission_model.current_mission
        
        if "max_altitude_ft" in override:
            scale = override["max_altitude_ft"] / max(mission.max_altitude_ft, 1)
            for phase in mission.phases:
                phase.altitude_ft *= scale
            mission.max_altitude_ft = override["max_altitude_ft"]
        
        if "loiter_duration_minutes" in override:
            from ..schemas.mission import MissionPhase
            for phase in mission.phases:
                if phase.phase == MissionPhase.LOITER:
                    phase.duration_minutes = override["loiter_duration_minutes"]
            mission.compute_total_duration()
        
        # Rebuild flight profile
        from ..simulation.flight_profile import FlightProfileInterpolator
        orchestrator.flight_profile = FlightProfileInterpolator(mission)
