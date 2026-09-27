"""
AERIS Configuration Module
Central configuration for the Aerospace Engine Risk & Intelligence System.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from enum import Enum
from typing import Optional
import os


class SimulationMode(str, Enum):
    LIVE = "LIVE"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"


class EngineConfig(BaseSettings):
    """Physics-informed demonstrator model configuration.
    NOT an exact DRDO engine model — simplified for prototype demonstration."""
    num_cylinders: int = 4
    displacement_cc: float = 1211.0  # ~Rotax 914 class
    compression_ratio: float = 9.0
    max_rpm: float = 5800.0
    idle_rpm: float = 1400.0
    max_power_hp: float = 115.0
    stoichiometric_afr: float = 14.7
    turbo_max_boost_psi: float = 8.0
    oil_capacity_liters: float = 4.0
    coolant_capacity_liters: float = 0.0  # air-cooled
    dry_weight_kg: float = 80.0


class SensorConfig(BaseSettings):
    """Sensor system configuration."""
    sampling_rate_hz: float = 20.0
    egt_noise_std: float = 3.0  # °C
    cht_noise_std: float = 2.0  # °C
    oil_pressure_noise_std: float = 0.5  # psi
    oil_temp_noise_std: float = 1.5  # °C
    map_noise_std: float = 0.3  # inHg
    rpm_noise_std: float = 5.0  # RPM
    vibration_noise_std: float = 0.02  # g
    voltage_noise_std: float = 0.05  # V
    fuel_flow_noise_std: float = 0.1  # gal/hr
    turbo_boost_noise_std: float = 0.1  # psi


class TwinConfig(BaseSettings):
    """Digital twin configuration."""
    residual_window_size: int = 60  # samples for rolling stats
    anomaly_threshold: float = 3.0  # sigma threshold
    persistence_window: int = 10  # consecutive samples before flagging
    drift_window_size: int = 300  # samples for drift detection
    drift_threshold: float = 1.5  # sigma for systematic drift


class MissionConfig(BaseSettings):
    """Mission simulation configuration."""
    max_altitude_ft: float = 30000.0
    min_altitude_ft: float = 0.0
    max_duration_hours: float = 24.0
    default_cruise_altitude_ft: float = 20000.0
    default_cruise_speed_kts: float = 120.0
    risk_threshold_critical: float = 0.8
    risk_threshold_warning: float = 0.5
    risk_threshold_caution: float = 0.3


class AerisConfig(BaseSettings):
    """Master configuration for AERIS system."""
    # General
    app_name: str = "AERIS"
    app_version: str = "0.1.0"
    app_subtitle: str = "Aerospace Engine Risk & Intelligence System"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    ws_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Simulation
    mode: SimulationMode = SimulationMode.SIMULATION
    simulation_speed: float = 1.0  # 1x, 5x, 10x, 20x
    tick_rate_hz: float = 20.0
    random_seed: int = 42
    
    # Database
    db_path: str = "data/aeris.db"
    
    # Sub-configs
    engine: EngineConfig = Field(default_factory=EngineConfig)
    sensor: SensorConfig = Field(default_factory=SensorConfig)
    twin: TwinConfig = Field(default_factory=TwinConfig)
    mission: MissionConfig = Field(default_factory=MissionConfig)
    
    # Data paths
    data_dir: str = "data"
    scenarios_dir: str = "data/scenarios"
    generated_dir: str = "data/generated"
    replay_dir: str = "data/replay"
    models_dir: str = "models"

    model_config = SettingsConfigDict(env_prefix="AERIS_", extra="ignore")


# Singleton
_config: Optional[AerisConfig] = None


def get_config() -> AerisConfig:
    global _config
    if _config is None:
        _config = AerisConfig()
    return _config
