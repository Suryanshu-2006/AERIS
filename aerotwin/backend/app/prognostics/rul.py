"""
Remaining Useful Life (RUL) Estimation
Estimates RUL for each component and the overall engine.
Also computes Mission-Safe Horizon — the critical differentiator.

All RUL values are labeled as MODEL ESTIMATES.
"""
import numpy as np
from ..schemas.engine import RULEstimate, MissionSafeHorizon, SubsystemName, DegradationState


class RULEstimator:
    """
    Estimates RUL by extrapolating current degradation trends.
    
    RUL = (failure_threshold - current_degradation) / degradation_rate
    
    Also computes Mission-Safe Horizon:
    How long can the engine remain within acceptable risk under selected mission conditions?
    This is NOT simply RUL — it accounts for mission stress amplification.
    """

    FAILURE_THRESHOLD = 0.85  # degradation level considered as functional failure
    MISSION_RISK_THRESHOLD = 0.6  # degradation level where mission risk becomes unacceptable

    def __init__(self):
        self.rul_estimates: dict[str, RULEstimate] = {}
        self.engine_rul: RULEstimate = None
        self.mission_safe_horizon: MissionSafeHorizon = None

    def estimate(self, degradation_states: dict[str, DegradationState],
                 mission_stress_factor: float = 1.0) -> dict[str, RULEstimate]:
        """
        Estimate RUL for all components.
        
        Args:
            degradation_states: current degradation per component
            mission_stress_factor: multiplier for mission conditions (>1 = harder mission)
        """
        self.rul_estimates = {}
        min_rul = float('inf')
        limiting_component = ""
        
        for comp, state in degradation_states.items():
            remaining = self.FAILURE_THRESHOLD - state.degradation_level
            
            if remaining <= 0:
                rul_hours = 0.0
            elif state.rate_per_hour > 0:
                rul_hours = remaining / state.rate_per_hour
            else:
                rul_hours = 999.9  # effectively infinite for prototype
            
            # Uncertainty bounds (wider with higher degradation)
            uncertainty_factor = 0.2 + 0.3 * state.degradation_level
            lower = max(0, rul_hours * (1 - uncertainty_factor))
            upper = rul_hours * (1 + uncertainty_factor)
            
            # Confidence decreases with high degradation rate variability
            confidence = max(0.3, 1.0 - state.degradation_level * 0.5)
            
            estimate = RULEstimate(
                component=comp,
                rul_hours=round(rul_hours, 1),
                lower_bound_hours=round(lower, 1),
                upper_bound_hours=round(upper, 1),
                confidence=round(confidence, 3),
                method="degradation_trend_extrapolation",
                is_model_estimate=True,
                note="Model estimate — not certified for flight safety",
            )
            self.rul_estimates[comp] = estimate
            
            if rul_hours < min_rul:
                min_rul = rul_hours
                limiting_component = comp
        
        # Overall engine RUL = minimum component RUL
        self.engine_rul = RULEstimate(
            component="engine",
            rul_hours=round(min_rul, 1),
            lower_bound_hours=round(min_rul * 0.7, 1) if min_rul < 999 else 700.0,
            upper_bound_hours=round(min_rul * 1.3, 1) if min_rul < 999 else 1300.0,
            confidence=0.7,
            method="min_component_rul",
            is_model_estimate=True,
            note=f"Limited by {limiting_component}. Model estimate — not certified for flight safety",
        )
        
        return self.rul_estimates

    def compute_mission_safe_horizon(self, degradation_states: dict[str, DegradationState],
                                      mission_stress_factor: float = 1.0,
                                      mission_conditions: str = "") -> MissionSafeHorizon:
        """
        Compute mission-safe horizon: how long can the engine safely operate
        under the selected mission conditions?
        
        This accounts for mission-specific stress amplification.
        Higher altitude, longer duration, more throttle = shorter safe horizon.
        """
        min_safe = float('inf')
        limiting = ""
        limiting_subsystem = SubsystemName.ENGINE
        
        for comp, state in degradation_states.items():
            remaining = self.MISSION_RISK_THRESHOLD - state.degradation_level
            
            if remaining <= 0:
                safe_hours = 0.0
            elif state.rate_per_hour > 0:
                # Mission stress amplifies degradation rate
                effective_rate = state.rate_per_hour * mission_stress_factor
                safe_hours = remaining / effective_rate
            else:
                safe_hours = 999.9
            
            if safe_hours < min_safe:
                min_safe = safe_hours
                limiting = comp
                try:
                    limiting_subsystem = SubsystemName(comp.upper())
                except ValueError:
                    limiting_subsystem = SubsystemName.ENGINE
        
        uncertainty_factor = 0.25
        
        self.mission_safe_horizon = MissionSafeHorizon(
            safe_hours=round(min_safe, 1),
            lower_bound_hours=round(min_safe * (1 - uncertainty_factor), 1),
            upper_bound_hours=round(min_safe * (1 + uncertainty_factor), 1),
            confidence=0.65,
            limiting_factor=f"{limiting} degradation under mission conditions",
            limiting_subsystem=limiting_subsystem,
            mission_conditions=mission_conditions,
            note="Model estimate under simulated mission conditions",
        )
        
        return self.mission_safe_horizon

    def reset(self):
        self.rul_estimates.clear()
        self.engine_rul = None
        self.mission_safe_horizon = None
