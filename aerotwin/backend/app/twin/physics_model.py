"""
Digital Twin Physics Model
Maintains the "expected healthy engine" state that runs in parallel with the actual engine.
Used to compute residuals: observed - expected.
"""
import numpy as np
from ..simulation.engine import EngineModel
from ..simulation.environment import FlightEnvironment
from ..schemas.engine import EngineState
from ..config import EngineConfig


class PhysicsModel:
    """
    The Digital Twin's internal physics model.
    
    This is a CLEAN copy of the engine model that always represents
    the expected behavior of a healthy engine under the same operating conditions.
    
    Residuals are computed as: observed (actual sensor) - expected (this model).
    """

    def __init__(self, config: EngineConfig = None):
        if config is None:
            config = EngineConfig()
        self.engine = EngineModel(config)
        self.last_state: EngineState = None

    def predict(self, dt: float, throttle: float, environment: FlightEnvironment) -> EngineState:
        """
        Predict what the engine SHOULD produce under these conditions
        if it were perfectly healthy.
        """
        state = self.engine.step(dt, throttle, environment)
        self.last_state = state
        return state

    def get_expected_values(self) -> dict[str, float]:
        """Extract expected sensor values from the healthy model."""
        if self.last_state is None:
            return {}
        
        s = self.last_state
        values = {}
        for i, cyl in enumerate(s.cylinders):
            values[f"EGT{i + 1}"] = cyl.egt_c
            values[f"CHT{i + 1}"] = cyl.cht_c
        
        values["OIL_PRESSURE"] = s.oil_pressure_psi
        values["OIL_TEMP"] = s.oil_temperature_c
        values["MAP"] = s.manifold_pressure_inhg
        values["RPM"] = s.rpm
        values["VIBRATION"] = s.vibration_g
        values["BUS_VOLTAGE"] = s.bus_voltage
        values["FUEL_FLOW"] = s.fuel_flow_gph
        values["TURBO_BOOST"] = s.turbo_boost_psi
        return values

    def reset(self):
        self.engine.reset()
        self.last_state = None
