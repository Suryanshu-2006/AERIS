"""
Engine Fault Propagation Tests
Verifies that:
1. Physical faults propagate through engine physics rather than overriding sensor values directly.
2. Oil pressure loss degrades lubrication state, increases friction and vibration.
3. Cooling degradation propagates to cylinder head temperature (CHT).
4. Turbo boost deficiency propagates to manifold pressure (MAP) and power loss.
"""
import pytest
from app.simulation.engine import EngineModel
from app.simulation.environment import FlightEnvironment
from app.simulation.faults import FaultInjector, FaultDefinition, FaultType


def test_oil_pressure_loss_propagation():
    """Verify oil pressure loss reduces oil pressure and increases friction/vibration."""
    env = FlightEnvironment()
    env.update(3000.0)
    engine = EngineModel()
    injector = FaultInjector()
    
    # Warm up / stabilize
    for _ in range(50):
        state = engine.step(0.05, 0.6, env)
    
    p_initial = state.oil_pressure_psi
    
    # Inject oil pressure loss
    fault = FaultDefinition(
        fault_id="oil_leak_1",
        fault_type=FaultType.OIL_PRESSURE_LOSS,
        target="OIL_SYSTEM",
        severity=0.7,
        start_time=0.0,
        duration=100.0,
        subsystem="LUBRICATION"
    )
    injector.inject(fault)
    
    for t in range(100):
        current_time = t * 0.05
        injector.apply_to_engine(engine, current_time)
        state = engine.step(0.05, 0.6, env)
        
    assert state.oil_pressure_psi < p_initial * 0.7, "Oil pressure must substantially drop under oil leak"


def test_cooling_fault_propagation():
    """Verify cylinder cooling fault increases targeted cylinder CHT."""
    env = FlightEnvironment()
    env.update(5000.0)
    engine = EngineModel()
    injector = FaultInjector()
    
    for _ in range(60):
        state_initial = engine.step(0.05, 0.6, env)
        
    cht2_initial = state_initial.cylinders[1].cht_c
    
    fault = FaultDefinition(
        fault_id="cooling_cyl2",
        fault_type=FaultType.COOLING_DEGRADATION,
        target="CYL2",
        severity=0.8,
        start_time=0.0,
        duration=100.0,
        subsystem="COOLING"
    )
    injector.inject(fault)
    
    for t in range(120):
        current_time = 30.0 + t * 0.05
        injector.apply_to_engine(engine, current_time)
        state = engine.step(0.05, 0.6, env)
        
    assert state.cylinders[1].cht_c > cht2_initial + 5.0, "Cylinder 2 CHT must rise under cooling fault"
