"""
Mission Schemas — Pydantic models for mission definition, risk, and what-if simulation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class MissionPhase(str, Enum):
    GROUND = "GROUND"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    SURVEILLANCE = "SURVEILLANCE"
    LOITER = "LOITER"
    DESCENT = "DESCENT"
    LANDING = "LANDING"
    EMERGENCY = "EMERGENCY"


class MissionPhaseConfig(BaseModel):
    """Configuration for a single mission phase."""
    phase: MissionPhase
    duration_minutes: float
    altitude_ft: float
    throttle_percent: float
    description: str = ""


class MissionProfile(BaseModel):
    """Complete mission definition as a sequence of phases."""
    mission_id: str = ""
    mission_name: str = "Default Mission"
    phases: list[MissionPhaseConfig] = []
    total_duration_hours: float = 0.0
    max_altitude_ft: float = 20000.0
    payload_kg: float = 50.0
    ambient_temperature_c: float = 15.0
    cruise_duration_minutes: float = 120.0
    loiter_duration_minutes: float = 60.0
    description: str = ""
    
    def compute_total_duration(self) -> float:
        self.total_duration_hours = sum(p.duration_minutes for p in self.phases) / 60.0
        return self.total_duration_hours


class MissionRiskResult(BaseModel):
    """Mission risk assessment output."""
    mission_id: str = ""
    mission_risk_score: float = Field(0.0, ge=0.0, le=1.0)
    mission_readiness: str = "READY"  # READY, CAUTION, WARNING, NOT_READY
    critical_phase: str = ""
    critical_phase_risk: float = 0.0
    risk_drivers: list[str] = []
    safe_horizon_hours: float = 0.0
    
    # Per-phase breakdown
    phase_risks: list[dict] = []
    
    # Health-based
    engine_health: float = 100.0
    degradation_rate: float = 0.0
    thermal_risk: float = 0.0
    lubrication_risk: float = 0.0
    mechanical_risk: float = 0.0
    
    note: str = "System recommendation — not certified for flight safety"


class WhatIfRequest(BaseModel):
    """Parameters for a what-if / counterfactual simulation."""
    # Baseline uses current mission; modified params override:
    altitude_ft: Optional[float] = None
    mission_duration_hours: Optional[float] = None
    throttle_percent: Optional[float] = None
    payload_kg: Optional[float] = None
    ambient_temperature_c: Optional[float] = None
    loiter_duration_minutes: Optional[float] = None
    cruise_duration_minutes: Optional[float] = None


class WhatIfTrajectoryPoint(BaseModel):
    """Single point in a what-if trajectory."""
    time_hours: float
    phase: str
    health: float
    temperature_c: float
    oil_pressure_psi: float
    rul_hours: float
    risk_score: float
    safe_horizon_hours: float


class WhatIfResult(BaseModel):
    """Comparison of baseline vs modified mission simulation."""
    baseline_risk: MissionRiskResult
    modified_risk: MissionRiskResult
    baseline_trajectory: list[WhatIfTrajectoryPoint] = []
    modified_trajectory: list[WhatIfTrajectoryPoint] = []
    risk_delta: float = 0.0
    safe_horizon_delta: float = 0.0
    critical_phase_changed: bool = False
    summary: str = ""
    recommendation: str = ""


class SimulationControl(BaseModel):
    """Control commands for the simulation."""
    action: str = "start"  # start, pause, resume, reset, speed
    speed: float = 1.0  # 1x, 5x, 10x, 20x
    scenario_id: str = ""
