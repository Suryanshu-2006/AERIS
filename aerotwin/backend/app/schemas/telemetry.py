"""
Telemetry Schemas — Pydantic models for telemetry data flowing through the system.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DataSource(str, Enum):
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"
    LIVE = "LIVE"


class SensorHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAULTY = "FAULTY"
    UNKNOWN = "UNKNOWN"


class SensorReading(BaseModel):
    """Individual sensor reading with metadata."""
    name: str
    value: float
    unit: str
    timestamp: float
    noise_std: float = 0.0
    health: SensorHealth = SensorHealth.HEALTHY
    confidence: float = 1.0
    raw_value: Optional[float] = None  # before any correction


class CylinderTelemetry(BaseModel):
    """Per-cylinder telemetry."""
    cylinder_id: int
    egt: float = Field(..., description="Exhaust Gas Temperature °C")
    cht: float = Field(..., description="Cylinder Head Temperature °C")
    combustion_efficiency: float = Field(1.0, ge=0.0, le=1.0)


class TelemetryFrame(BaseModel):
    """Complete telemetry snapshot at a point in time."""
    timestamp: float
    simulation_time: float = 0.0
    data_source: DataSource = DataSource.SIMULATION
    simulation_id: str = ""
    scenario_id: str = ""
    model_version: str = "0.1.0"
    
    # Engine parameters
    rpm: float = 0.0
    manifold_pressure_inhg: float = 29.92
    throttle_percent: float = 0.0
    fuel_flow_gph: float = 0.0
    air_flow_cfm: float = 0.0
    torque_nm: float = 0.0
    power_hp: float = 0.0
    
    # Per-cylinder
    cylinders: list[CylinderTelemetry] = []
    
    # Oil system
    oil_pressure_psi: float = 60.0
    oil_temperature_c: float = 80.0
    
    # Vibration
    vibration_g: float = 0.05
    
    # Electrical
    bus_voltage: float = 28.0
    
    # Turbocharger
    turbo_boost_psi: float = 0.0
    turbo_rpm: float = 0.0
    
    # Environment
    altitude_ft: float = 0.0
    ambient_temp_c: float = 15.0
    ambient_pressure_inhg: float = 29.92
    
    # Mission
    mission_phase: str = "GROUND"
    flight_time_seconds: float = 0.0
    
    # Fuel
    fuel_remaining_gal: float = 50.0
    fuel_consumed_gal: float = 0.0


class SensorFrame(BaseModel):
    """All sensor readings at a point in time (with noise, bias, faults)."""
    timestamp: float
    simulation_time: float = 0.0
    sensors: dict[str, SensorReading] = {}
    
    def get(self, name: str) -> Optional[SensorReading]:
        return self.sensors.get(name)


class TelemetryBatch(BaseModel):
    """Batch of telemetry frames for streaming."""
    frames: list[TelemetryFrame]
    start_time: float
    end_time: float
    count: int
    data_source: DataSource = DataSource.SIMULATION
