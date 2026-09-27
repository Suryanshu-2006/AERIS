"""
What-If / Counterfactual Mission Simulation
Runs parallel simulations with modified mission parameters to compare outcomes.
This is NOT a frontend-only calculation — it actually reruns the simulation.
"""
import copy
import numpy as np
from ..schemas.mission import (
    MissionProfile, MissionPhaseConfig, MissionPhase,
    WhatIfRequest, WhatIfResult, WhatIfTrajectoryPoint, MissionRiskResult
)
from ..schemas.engine import HealthScores, DegradationState, MissionSafeHorizon
from ..simulation.environment import FlightEnvironment
from ..simulation.engine import EngineModel
from ..simulation.flight_profile import FlightProfileInterpolator
from ..twin.health_state import HealthState
from ..prognostics.degradation import DegradationTracker
from ..prognostics.rul import RULEstimator
from .mission_model import MissionModel
from .mission_risk import MissionRiskEngine
from ..config import get_config


class WhatIfSimulator:
    """
    Counterfactual simulation engine.
    
    Modifies mission parameters and reruns the full simulation to compare:
    - Health trajectory
    - Temperature trajectory
    - Oil pressure trajectory
    - RUL trajectory
    - Mission risk
    - Safe horizon
    - Critical phase
    """

    def __init__(self):
        self.config = get_config()

    def simulate(self, baseline_mission: MissionProfile,
                 what_if: WhatIfRequest,
                 current_health: HealthScores,
                 current_degradation: dict[str, DegradationState]) -> WhatIfResult:
        """
        Run both baseline and modified mission simulations, then compare.
        """
        # Create modified mission
        modified_mission = self._apply_modifications(baseline_mission, what_if)
        
        # Run baseline simulation
        baseline_trajectory, baseline_risk = self._run_simulation(
            baseline_mission, current_health, current_degradation,
            baseline_mission.ambient_temperature_c
        )
        
        # Run modified simulation
        modified_ambient = what_if.ambient_temperature_c if what_if.ambient_temperature_c is not None \
            else baseline_mission.ambient_temperature_c
        modified_trajectory, modified_risk = self._run_simulation(
            modified_mission, current_health, current_degradation,
            modified_ambient
        )
        
        # Compare
        risk_delta = modified_risk.mission_risk_score - baseline_risk.mission_risk_score
        
        baseline_safe = baseline_risk.safe_horizon_hours
        modified_safe = modified_risk.safe_horizon_hours
        safe_horizon_delta = modified_safe - baseline_safe
        
        critical_changed = baseline_risk.critical_phase != modified_risk.critical_phase
        
        # Generate summary
        summary = self._generate_summary(baseline_risk, modified_risk, what_if, risk_delta)
        recommendation = self._generate_recommendation(risk_delta, modified_risk)
        
        return WhatIfResult(
            baseline_risk=baseline_risk,
            modified_risk=modified_risk,
            baseline_trajectory=baseline_trajectory,
            modified_trajectory=modified_trajectory,
            risk_delta=round(risk_delta, 4),
            safe_horizon_delta=round(safe_horizon_delta, 1),
            critical_phase_changed=critical_changed,
            summary=summary,
            recommendation=recommendation,
        )

    def _apply_modifications(self, baseline: MissionProfile,
                              what_if: WhatIfRequest) -> MissionProfile:
        """Create modified mission profile from what-if parameters."""
        modified = baseline.model_copy(deep=True)
        
        if what_if.altitude_ft is not None:
            # Scale all phase altitudes proportionally
            if baseline.max_altitude_ft > 0:
                scale = what_if.altitude_ft / baseline.max_altitude_ft
            else:
                scale = 1.0
            for phase in modified.phases:
                phase.altitude_ft = phase.altitude_ft * scale
            modified.max_altitude_ft = what_if.altitude_ft
        
        if what_if.throttle_percent is not None:
            for phase in modified.phases:
                if phase.phase in (MissionPhase.CRUISE, MissionPhase.SURVEILLANCE, MissionPhase.LOITER):
                    phase.throttle_percent = what_if.throttle_percent
        
        if what_if.loiter_duration_minutes is not None:
            for phase in modified.phases:
                if phase.phase == MissionPhase.LOITER:
                    phase.duration_minutes = what_if.loiter_duration_minutes
        
        if what_if.cruise_duration_minutes is not None:
            cruise_phases = [p for p in modified.phases if p.phase == MissionPhase.CRUISE]
            if cruise_phases:
                total_cruise = sum(p.duration_minutes for p in cruise_phases)
                if total_cruise > 0:
                    scale = what_if.cruise_duration_minutes / total_cruise
                    for p in cruise_phases:
                        p.duration_minutes = p.duration_minutes * scale
        
        if what_if.mission_duration_hours is not None:
            current_total = sum(p.duration_minutes for p in modified.phases)
            if current_total > 0:
                scale = (what_if.mission_duration_hours * 60) / current_total
                for p in modified.phases:
                    p.duration_minutes = p.duration_minutes * scale
        
        if what_if.ambient_temperature_c is not None:
            modified.ambient_temperature_c = what_if.ambient_temperature_c
        
        if what_if.payload_kg is not None:
            modified.payload_kg = what_if.payload_kg
        
        modified.compute_total_duration()
        return modified

    def _run_simulation(self, mission: MissionProfile,
                        initial_health: HealthScores,
                        initial_degradation: dict[str, DegradationState],
                        ambient_temp_c: float) -> tuple[list[WhatIfTrajectoryPoint], MissionRiskResult]:
        """
        Actually run the engine simulation for the given mission.
        Returns trajectory points and final risk assessment.
        """
        # Create fresh engine and subsystem instances
        engine = EngineModel(self.config.engine)
        environment = FlightEnvironment()
        interpolator = FlightProfileInterpolator(mission)
        health_tracker = HealthState()
        deg_tracker = DegradationTracker()
        rul_estimator = RULEstimator()
        mission_model = MissionModel()
        risk_engine = MissionRiskEngine()
        
        # Initialize from current state
        health_tracker.scores = initial_health.model_copy()
        for comp, state in initial_degradation.items():
            if comp in deg_tracker.states:
                deg_tracker.states[comp] = state.model_copy()
        
        # Simulation parameters
        total_time_s = interpolator.get_total_duration_s()
        dt = 15.0  # 15-second steps for fast counterfactual rerun
        trajectory = []
        
        t = 0.0
        sample_interval = max(total_time_s / 50, 60)  # ~50 trajectory points
        next_sample = 0.0
        
        while t < total_time_s:
            # Get flight conditions
            conditions = interpolator.get_conditions(t)
            phase = conditions["phase"]
            altitude = conditions["altitude_ft"]
            throttle = conditions["throttle"]
            
            # Update environment
            environment.update(altitude, ambient_temp_c - 15.0)
            
            # Step engine
            engine_state = engine.step(dt, throttle, environment)
            
            # Get stress factor
            stress = mission_model.get_phase_stress_factor(
                phase, altitude, throttle, ambient_temp_c
            )
            
            # Update degradation
            deg_tracker.update(
                dt_hours=dt / 3600.0,
                health_scores=health_tracker.scores,
                thermal_stress=min(max(engine_state.mean_cht_c - 180, 0) / 80, 1.0),
                oil_stress=max(0, (40 - engine_state.oil_pressure_psi) / 40),
                altitude_ft=altitude,
                timestamp=t,
            )
            
            # Sample trajectory points
            if t >= next_sample:
                # Quick health update
                health_tracker.update({})
                
                # RUL estimate
                rul_estimator.estimate(deg_tracker.states, stress)
                safe_horizon = rul_estimator.compute_mission_safe_horizon(
                    deg_tracker.states, stress
                )
                
                trajectory.append(WhatIfTrajectoryPoint(
                    time_hours=round(t / 3600, 2),
                    phase=phase.value if hasattr(phase, 'value') else str(phase),
                    health=round(health_tracker.scores.engine, 1),
                    temperature_c=round(engine_state.mean_cht_c, 1),
                    oil_pressure_psi=round(engine_state.oil_pressure_psi, 1),
                    rul_hours=round(rul_estimator.engine_rul.rul_hours if rul_estimator.engine_rul else 999, 1),
                    risk_score=0.0,  # filled later
                    safe_horizon_hours=round(safe_horizon.safe_hours, 1),
                ))
                next_sample += sample_interval
            
            t += dt
        
        # Final risk assessment
        rul_estimator.estimate(deg_tracker.states)
        safe_horizon = rul_estimator.compute_mission_safe_horizon(deg_tracker.states)
        
        risk_result = risk_engine.assess(
            mission=mission,
            health=health_tracker.scores,
            degradation=deg_tracker.states,
            safe_horizon=safe_horizon,
            mission_model=mission_model,
        )
        
        # Backfill risk scores in trajectory
        for point in trajectory:
            point.risk_score = round(risk_result.mission_risk_score * (1 + point.time_hours / max(mission.total_duration_hours, 1) * 0.2), 3)
        
        return trajectory, risk_result

    def _generate_summary(self, baseline: MissionRiskResult, modified: MissionRiskResult,
                           what_if: WhatIfRequest, risk_delta: float) -> str:
        """Generate natural-language comparison summary."""
        parts = []
        
        if what_if.altitude_ft is not None:
            parts.append(f"altitude changed to {what_if.altitude_ft:.0f} ft")
        if what_if.loiter_duration_minutes is not None:
            parts.append(f"loiter duration changed to {what_if.loiter_duration_minutes:.0f} min")
        if what_if.mission_duration_hours is not None:
            parts.append(f"mission duration changed to {what_if.mission_duration_hours:.1f}h")
        if what_if.ambient_temperature_c is not None:
            parts.append(f"ambient temperature changed to {what_if.ambient_temperature_c:.0f} deg C")
        if what_if.throttle_percent is not None:
            parts.append(f"throttle changed to {what_if.throttle_percent:.0f}%")
        
        changes = ", ".join(parts) if parts else "no changes"
        
        direction = "increased" if risk_delta > 0 else "decreased"
        return (
            f"With {changes}: mission risk {direction} by {abs(risk_delta):.1%} "
            f"({baseline.mission_risk_score:.1%} -> {modified.mission_risk_score:.1%}). "
            f"Readiness: {baseline.mission_readiness} -> {modified.mission_readiness}."
        )

    def _generate_recommendation(self, risk_delta: float, modified_risk: MissionRiskResult) -> str:
        if modified_risk.mission_risk_score > 0.7:
            return "Modified mission NOT recommended -- risk exceeds acceptable threshold"
        if risk_delta > 0.15:
            return "Modified mission significantly increases risk -- consider alternatives"
        if risk_delta > 0.05:
            return "Modified mission moderately increases risk -- proceed with enhanced monitoring"
        if risk_delta < -0.05:
            return "Modified mission reduces risk -- recommended over baseline"
        return "Modified mission has similar risk to baseline"
