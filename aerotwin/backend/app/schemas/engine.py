"""
Engine Schemas — Pydantic models for engine state, subsystems, and physics.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SubsystemName(str, Enum):
    COMBUSTION = "COMBUSTION"
    COOLING = "COOLING"
    LUBRICATION = "LUBRICATION"
    TURBO = "TURBO"
    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    SENSORS = "SENSORS"
    ENGINE = "ENGINE"


class CylinderState(BaseModel):
    """Physics state of a single cylinder."""
    cylinder_id: int
    egt_c: float = 650.0
    cht_c: float = 180.0
    combustion_efficiency: float = 1.0
    fuel_air_ratio: float = Field(default=1.0 / 14.7, description="Actual F/A ratio")
    mixture_quality: float = 1.0  # 1.0 = ideal stoich
    cooling_effectiveness: float = 1.0
    misfire_probability: float = 0.0


class EngineState(BaseModel):
    """Complete physical state of the engine."""
    timestamp: float = 0.0
    
    # Core parameters
    rpm: float = 0.0
    throttle: float = 0.0  # 0-1
    manifold_pressure_inhg: float = 29.92
    torque_nm: float = 0.0
    power_hp: float = 0.0
    
    # Airflow
    air_mass_flow_gs: float = 0.0  # g/s
    volumetric_efficiency: float = 0.85
    
    # Fuel
    fuel_flow_gph: float = 0.0
    fuel_air_ratio: float = 1.0 / 14.7
    
    # Cylinders
    cylinders: list[CylinderState] = []
    mean_egt_c: float = 650.0
    mean_cht_c: float = 180.0
    
    # Oil system
    oil_pressure_psi: float = 60.0
    oil_temperature_c: float = 80.0
    oil_viscosity_factor: float = 1.0
    
    # Turbocharger
    turbo_boost_psi: float = 0.0
    turbo_rpm: float = 0.0
    turbo_efficiency: float = 0.75
    
    # Vibration
    vibration_g: float = 0.05
    vibration_dominant_freq_hz: float = 0.0
    
    # Electrical
    bus_voltage: float = 28.0
    alternator_output_a: float = 30.0
    
    # Derived
    specific_fuel_consumption: float = 0.0
    thermal_margin_c: float = 100.0  # degrees below redline


class HealthScores(BaseModel):
    """Health scores per subsystem (0-100)."""
    engine: float = 100.0
    combustion: float = 100.0
    cooling: float = 100.0
    lubrication: float = 100.0
    turbo: float = 100.0
    mechanical: float = 100.0
    electrical: float = 100.0
    sensors: float = 100.0
    
    def overall(self) -> float:
        weights = {
            'combustion': 0.25,
            'cooling': 0.15,
            'lubrication': 0.20,
            'turbo': 0.10,
            'mechanical': 0.15,
            'electrical': 0.10,
            'sensors': 0.05,
        }
        score = sum(getattr(self, k) * w for k, w in weights.items())
        self.engine = score
        return score


class DegradationState(BaseModel):
    """Degradation tracking per component."""
    component: str
    degradation_level: float = 0.0  # 0 = new, 1 = failed
    rate_per_hour: float = 0.0
    accumulated_hours: float = 0.0
    last_update: float = 0.0


class RULEstimate(BaseModel):
    """Remaining Useful Life estimate."""
    component: str
    rul_hours: float = Field(..., description="Estimated RUL in hours")
    lower_bound_hours: float = 0.0
    upper_bound_hours: float = 0.0
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    method: str = "degradation_extrapolation"
    is_model_estimate: bool = True  # Always true for prototype
    note: str = "Model estimate — not certified for flight safety"


class MissionSafeHorizon(BaseModel):
    """How long the engine can safely operate under current/selected mission conditions."""
    safe_hours: float
    lower_bound_hours: float
    upper_bound_hours: float
    confidence: float
    limiting_factor: str
    limiting_subsystem: SubsystemName
    mission_conditions: str = ""
    note: str = "Model estimate under simulated mission conditions"
