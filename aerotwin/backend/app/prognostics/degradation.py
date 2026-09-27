"""
Degradation Model
Tracks component degradation over time based on operating conditions,
fault history, and stress factors. Degradation is the basis for RUL estimation.
"""
import numpy as np
from ..schemas.engine import DegradationState, HealthScores


class DegradationTracker:
    """
    Tracks degradation state for each engine subsystem.
    
    Degradation increases with:
    - Operating time
    - High thermal load
    - Low oil pressure (bearing stress)
    - Fault severity
    - High-altitude operation (thermal cycling)
    
    Degradation level: 0 = new, 1 = failed
    """

    COMPONENTS = ["combustion", "cooling", "lubrication", "turbo", "mechanical", "electrical"]

    def __init__(self):
        self.states: dict[str, DegradationState] = {}
        for comp in self.COMPONENTS:
            self.states[comp] = DegradationState(
                component=comp,
                degradation_level=0.0,
                rate_per_hour=0.0,
                accumulated_hours=0.0,
            )
        # Base degradation rates (per hour of operation)
        self.base_rates = {
            "combustion": 0.0005,
            "cooling": 0.0003,
            "lubrication": 0.0004,
            "turbo": 0.0006,
            "mechanical": 0.0003,
            "electrical": 0.0002,
        }

    def update(self, dt_hours: float, health_scores: HealthScores,
               thermal_stress: float = 0.0, oil_stress: float = 0.0,
               altitude_ft: float = 0.0, fault_severity: float = 0.0,
               fault_subsystem: str = "", timestamp: float = 0.0) -> dict[str, DegradationState]:
        """
        Update degradation for all components.
        
        Args:
            dt_hours: time step in hours
            health_scores: current health scores
            thermal_stress: 0-1 thermal stress factor
            oil_stress: 0-1 oil system stress factor
            altitude_ft: current altitude (affects thermal cycling)
            fault_severity: active fault severity
            fault_subsystem: affected subsystem
            timestamp: current simulation time
        """
        # Altitude stress factor (thermal cycling at high altitude)
        altitude_factor = 1.0 + 0.5 * min(altitude_ft / 30000.0, 1.0)
        
        for comp in self.COMPONENTS:
            state = self.states[comp]
            base_rate = self.base_rates[comp]
            
            # Stress multipliers
            thermal_mult = 1.0 + thermal_stress * 2.0 if comp in ("combustion", "cooling") else 1.0
            oil_mult = 1.0 + oil_stress * 3.0 if comp in ("lubrication", "mechanical") else 1.0
            
            # Fault accelerates degradation of affected subsystem
            fault_mult = 1.0
            if fault_subsystem and fault_subsystem.upper() == comp.upper():
                fault_mult = 1.0 + fault_severity * 5.0
            
            # Combined degradation rate
            rate = base_rate * thermal_mult * oil_mult * altitude_factor * fault_mult
            
            # Degradation accelerates as component deteriorates (wear-out phase)
            wear_acceleration = 1.0 + state.degradation_level ** 2 * 3.0
            rate *= wear_acceleration
            
            state.rate_per_hour = rate
            state.degradation_level += rate * dt_hours
            state.degradation_level = min(state.degradation_level, 1.0)
            state.accumulated_hours += dt_hours
            state.last_update = timestamp
        
        return self.states

    def get_degradation_levels(self) -> dict[str, float]:
        """Get current degradation levels for all components."""
        return {comp: state.degradation_level for comp, state in self.states.items()}

    def get_worst_component(self) -> tuple[str, float]:
        """Get the most degraded component."""
        worst = max(self.states.items(), key=lambda x: x[1].degradation_level)
        return worst[0], worst[1].degradation_level

    def reset(self):
        for comp in self.COMPONENTS:
            self.states[comp] = DegradationState(
                component=comp,
                degradation_level=0.0,
                rate_per_hour=0.0,
                accumulated_hours=0.0,
            )
