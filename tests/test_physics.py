"""
Physics Engine Validation Tests
Verifies that:
1. Throttle increase affects airflow and engine power
2. Altitude affects ambient pressure and temperature
3. Oil-pressure degradation affects lubrication state
4. Cooling degradation affects CHT
5. Turbo deficiency affects MAP
"""
import pytest
import numpy as np
from app.simulation.engine import EngineModel
from app.simulation.environment import FlightEnvironment
from app.config import EngineConfig


def test_throttle_increase_affects_airflow_and_rpm():
    """Verify throttle increase increases airflow and RPM."""
    env = FlightEnvironment()
    env.update(0.0)
    engine = EngineModel()
    
    # Run idle for a few steps
    for _ in range(50):
        state_idle = engine.step(dt=0.05, throttle=0.2, environment=env)
    
    # Increase throttle
    for _ in range(100):
        state_high = engine.step(dt=0.05, throttle=0.8, environment=env)
        
    assert state_high.rpm > state_idle.rpm, "Higher throttle must yield higher RPM"
    assert state_high.fuel_flow_gph > state_idle.fuel_flow_gph, "Higher throttle must yield higher fuel flow"
    assert state_high.manifold_pressure_inhg >= state_idle.manifold_pressure_inhg, "Higher throttle must yield higher or equal MAP"


def test_altitude_affects_ambient_pressure_and_temp():
    """Verify altitude change affects pressure according to ISA."""
    env = FlightEnvironment()
    env.update(0.0)
    p_sl = env.ambient_pressure_inhg
    t_sl = env.ambient_temp_c
    
    env.update(15000.0)
    p_15k = env.ambient_pressure_inhg
    t_15k = env.ambient_temp_c
    
    assert p_15k < p_sl, f"Pressure at 15k ft ({p_15k}) must be lower than sea level ({p_sl})"
    assert t_15k < t_sl, f"Temperature at 15k ft ({t_15k}) must be lower than sea level ({t_sl})"


def test_oil_pressure_degradation_affects_lubrication():
    """Verify oil degradation affects lubrication state and friction."""
    env = FlightEnvironment()
    env.update(5000.0)
    engine = EngineModel()
    
    # Run normal
    for _ in range(50):
        state_normal = engine.step(dt=0.05, throttle=0.6, environment=env)
        
    normal_p = state_normal.oil_pressure_psi
    
    # Inject oil leak degradation
    engine.lubrication.set_leakage_rate(0.6)
    for _ in range(100):
        state_degraded = engine.step(dt=0.05, throttle=0.6, environment=env)
        
    assert state_degraded.oil_pressure_psi < normal_p, "Oil leak must reduce oil pressure"


def test_cooling_degradation_affects_cht():
    """Verify cooling degradation increases cylinder head temperature."""
    env = FlightEnvironment()
    env.update(5000.0)
    engine = EngineModel()
    
    # Normal operation
    for _ in range(60):
        state_normal = engine.step(dt=0.05, throttle=0.7, environment=env)
    
    normal_cht = state_normal.cylinders[0].cht_c
    
    # Degrade cooling on cylinder 1
    engine.cooling.set_cooling_health(0, 0.2)
    for _ in range(120):
        state_hot = engine.step(dt=0.05, throttle=0.7, environment=env)
        
    assert state_hot.cylinders[0].cht_c > normal_cht, "Reduced cooling efficiency must increase CHT"


def test_turbo_deficiency_affects_map():
    """Verify turbo boost deficiency reduces manifold pressure."""
    env = FlightEnvironment()
    env.update(12000.0)
    
    engine_normal = EngineModel()
    for _ in range(160):
        state_normal = engine_normal.step(dt=0.05, throttle=0.9, environment=env)
        
    engine_turbo_fail = EngineModel()
    engine_turbo_fail.turbo.set_health(0.1)
    engine_turbo_fail.turbo.set_shaft_efficiency(0.1)
    for _ in range(160):
        state_turbo_fail = engine_turbo_fail.step(dt=0.05, throttle=0.9, environment=env)
        
    assert state_turbo_fail.manifold_pressure_inhg < state_normal.manifold_pressure_inhg, (
        "Degraded turbo must cause boost loss and lower MAP at altitude"
    )
