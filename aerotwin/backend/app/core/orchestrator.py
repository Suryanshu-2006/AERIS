"""
Orchestrator
The central coordinator that runs the simulation loop, connecting:
Simulator → Environment → Engine → Sensors → Digital Twin → AI → Mission → API

This is the heartbeat of AERIS.
"""
import asyncio
import time
import uuid
import numpy as np
from typing import Optional

from ..config import get_config, AerisConfig
from ..simulation.environment import FlightEnvironment
from ..simulation.engine import EngineModel
from ..simulation.sensors import SensorModel
from ..simulation.faults import FaultInjector, FaultDefinition, PREDEFINED_FAULTS
from ..simulation.flight_profile import FlightProfileInterpolator, create_default_mission

from ..twin.physics_model import PhysicsModel
from ..twin.state_estimator import StateEstimator
from ..twin.residual_engine import ResidualEngine
from ..twin.health_state import HealthState
from ..twin.drift_monitor import DriftMonitor

from ..ai.anomaly import AnomalyDetector
from ..ai.diagnosis import DiagnosisEngine
from ..ai.severity import SensorIntegrityAnalyzer
from ..ai.calibration import ModelCalibrator

from ..prognostics.degradation import DegradationTracker
from ..prognostics.rul import RULEstimator

from ..explainability.evidence import EvidenceChainBuilder
from ..explainability.explainer import Explainer

from ..mission.mission_model import MissionModel
from ..mission.mission_risk import MissionRiskEngine
from ..mission.readiness import ReadinessAssessor
from ..mission.what_if import WhatIfSimulator

from .state_manager import StateManager
from .event_bus import EventBus
from ..schemas.telemetry import DataSource
from ..schemas.mission import WhatIfRequest


class Orchestrator:
    """
    Master orchestrator that runs the complete OBSERVE → UNDERSTAND → PREDICT →
    SIMULATE → COMPARE → DECIDE loop.
    """

    def __init__(self):
        self.config = get_config()
        
        # Core components
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        
        # Simulation
        self.environment = FlightEnvironment()
        self.engine = EngineModel(self.config.engine)
        self.sensor_model = SensorModel(self.config.sensor, self.config.engine.num_cylinders, self.config.random_seed)
        self.fault_injector = FaultInjector()
        self.flight_profile: Optional[FlightProfileInterpolator] = None
        
        # Digital Twin
        self.physics_model = PhysicsModel(self.config.engine)
        self.state_estimator = StateEstimator()
        self.residual_engine = ResidualEngine(self.config.twin)
        self.health_state = HealthState()
        self.drift_monitor = DriftMonitor(self.config.twin)
        
        # AI
        self.anomaly_detector = AnomalyDetector(self.config.twin)
        self.diagnosis_engine = DiagnosisEngine()
        self.sensor_integrity = SensorIntegrityAnalyzer()
        self.calibrator = ModelCalibrator()
        
        # Prognostics
        self.degradation_tracker = DegradationTracker()
        self.rul_estimator = RULEstimator()
        
        # Explainability
        self.evidence_builder = EvidenceChainBuilder()
        self.explainer = Explainer()
        
        # Mission
        self.mission_model = MissionModel()
        self.risk_engine = MissionRiskEngine()
        self.readiness_assessor = ReadinessAssessor()
        self.what_if_simulator = WhatIfSimulator()
        
        # Simulation control
        self.simulation_time = 0.0
        self.dt = 1.0 / self.config.tick_rate_hz  # seconds per tick
        self.speed = 1.0
        self.running = False
        self.paused = False
        self._task: Optional[asyncio.Task] = None
        self._ws_clients: list = []
        
        # Initialize mission
        self._init_mission()

    def _init_mission(self):
        """Set up default mission profile."""
        mission = self.mission_model.current_mission
        self.flight_profile = FlightProfileInterpolator(mission)
        self.state_manager.current_mission = mission
        self.state_manager.simulation_id = f"SIM_{uuid.uuid4().hex[:8].upper()}"
        self.state_manager.data_source = DataSource.SIMULATION
        # Prime initial state snapshot immediately
        self.step(dt=0.0)
        self.simulation_time = 0.0

    async def start(self):
        """Start the simulation loop."""
        if self.running:
            return
        self.running = True
        self.paused = False
        self.state_manager.is_running = True
        self.state_manager.is_paused = False
        self._task = asyncio.create_task(self._simulation_loop())
        self.event_bus.publish("simulation_started", {"time": time.time()})

    async def stop(self):
        """Stop the simulation."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.state_manager.is_running = False

    def pause(self):
        self.paused = True
        self.state_manager.is_paused = True

    def resume(self):
        self.paused = False
        self.state_manager.is_paused = False

    def set_speed(self, speed: float):
        self.speed = max(0.1, min(speed, 20.0))
        self.state_manager.simulation_speed = self.speed

    def reset(self):
        """Reset entire simulation."""
        self.running = False
        self.paused = False
        self.simulation_time = 0.0
        self.engine.reset()
        self.sensor_model.reset()
        self.fault_injector.clear_all()
        self.physics_model.reset()
        self.state_estimator.reset()
        self.residual_engine.reset()
        self.health_state.reset()
        self.drift_monitor.reset()
        self.anomaly_detector.reset()
        self.diagnosis_engine.reset()
        self.sensor_integrity.reset()
        self.calibrator.reset()
        self.degradation_tracker.reset()
        self.rul_estimator.reset()
        self.state_manager.reset()
        self._init_mission()

    def inject_fault(self, fault_id: str, severity: float = None,
                     start_time: float = None, duration: float = float('inf')) -> Optional[dict]:
        """Inject a fault by predefined ID."""
        if start_time is None:
            start_time = self.simulation_time
        result = self.fault_injector.inject_by_id(fault_id, severity, start_time, duration)
        if result:
            return result.model_dump()
        return None

    def inject_custom_fault(self, fault_def: FaultDefinition) -> dict:
        """Inject a custom fault definition."""
        self.fault_injector.inject(fault_def)
        return fault_def.model_dump()

    def clear_fault(self, fault_id: str):
        self.fault_injector.clear(fault_id)

    def clear_all_faults(self):
        self.fault_injector.clear_all()
        self.sensor_model.clear_all_faults()

    def run_what_if(self, request: WhatIfRequest) -> dict:
        """Run a what-if counterfactual simulation."""
        result = self.what_if_simulator.simulate(
            baseline_mission=self.mission_model.current_mission,
            what_if=request,
            current_health=self.health_state.scores,
            current_degradation=self.degradation_tracker.states,
        )
        return result.model_dump()

    def register_ws_client(self, ws):
        self._ws_clients.append(ws)

    def unregister_ws_client(self, ws):
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)

    def step(self, dt: Optional[float] = None):
        """
        Advance the simulation by dt seconds (synchronous step).
        Runs the full digital twin, AI, diagnosis, and prognostics pipeline.
        """
        effective_dt = (dt if dt is not None else self.dt) * self.speed
        self.simulation_time += effective_dt
        
        # --- STEP 1: Flight conditions ---
        if self.flight_profile:
            conditions = self.flight_profile.get_conditions(self.simulation_time)
            throttle = conditions["throttle"]
            altitude = conditions["altitude_ft"]
            phase = conditions["phase"]
        else:
            throttle = 0.65
            altitude = 20000
            phase = "CRUISE"
        
        self.environment.update(altitude)
        self.environment.mission_phase = phase
        
        # --- STEP 2: Apply physical faults to engine ---
        self.fault_injector.apply_to_engine(self.engine, self.simulation_time)
        
        # --- STEP 3: Step actual engine ---
        engine_state = self.engine.step(effective_dt, throttle, self.environment)
        
        # --- STEP 4: Apply sensor faults and measure ---
        self.fault_injector.apply_to_sensors(self.sensor_model, self.simulation_time)
        sensor_frame = self.sensor_model.measure(engine_state, self.simulation_time)
        
        # --- STEP 5: Digital twin prediction (healthy expected) ---
        expected_state = self.physics_model.predict(effective_dt, throttle, self.environment)
        expected_values = self.physics_model.get_expected_values()
        
        # --- STEP 6: State estimation (sensor + model fusion) ---
        estimated = self.state_estimator.estimate(sensor_frame, expected_values)
        
        # --- STEP 7: Residuals ---
        residuals = self.residual_engine.compute(sensor_frame, expected_values)
        anomalous_channels = self.residual_engine.get_anomalous_channels(self.config.twin.anomaly_threshold)
        
        # --- STEP 8: Sensor integrity ---
        sensor_values = {name: sr.value for name, sr in sensor_frame.sensors.items()}
        sensor_confidences = {name: sr.confidence for name, sr in sensor_frame.sensors.items()}
        integrity_results = self.sensor_integrity.analyze(sensor_values, residuals, sensor_confidences)
        
        # --- STEP 9: Drift monitor ---
        drift_info = self.drift_monitor.update(residuals, anomalous_channels)
        
        # --- STEP 10: Anomaly detection ---
        anomaly = self.anomaly_detector.detect(residuals, sensor_confidences, sensor_values)
        anomaly.timestamp = self.simulation_time
        
        # --- STEP 11: Fault diagnosis ---
        raw_residuals = self.residual_engine.current_raw_residuals
        diagnosis = self.diagnosis_engine.diagnose(
            residuals=residuals,
            raw_residuals=raw_residuals,
            anomaly=anomaly,
            sensor_integrity=integrity_results,
            observed_values=sensor_values,
            expected_values=expected_values,
            timestamp=self.simulation_time,
        )
        
        # --- STEP 12: Health scores ---
        fault_severity = diagnosis.primary_fault.severity if diagnosis.primary_fault else 0.0
        fault_subsystem = diagnosis.primary_fault.subsystem if diagnosis.primary_fault else ""
        health = self.health_state.update(
            residuals=residuals,
            fault_severity=fault_severity,
            fault_subsystem=fault_subsystem,
            sensor_confidences=sensor_confidences,
            degradation_levels=self.degradation_tracker.get_degradation_levels(),
        )
        
        # --- STEP 13: Degradation ---
        thermal_stress = max(0, (engine_state.mean_cht_c - 180) / 80.0)
        oil_stress = max(0, (40 - engine_state.oil_pressure_psi) / 40.0)
        self.degradation_tracker.update(
            dt_hours=effective_dt / 3600.0,
            health_scores=health,
            thermal_stress=min(thermal_stress, 1.0),
            oil_stress=min(oil_stress, 1.0),
            altitude_ft=altitude,
            fault_severity=fault_severity,
            fault_subsystem=fault_subsystem,
            timestamp=self.simulation_time,
        )
        
        # --- STEP 14: RUL ---
        from ..schemas.mission import MissionPhase
        if isinstance(phase, str):
            try:
                phase_enum = MissionPhase(phase)
            except ValueError:
                phase_enum = MissionPhase.CRUISE
        else:
            phase_enum = phase
        mission_stress = self.mission_model.get_phase_stress_factor(
            phase_enum, altitude, throttle, self.environment.ambient_temp_c
        )
        
        self.rul_estimator.estimate(self.degradation_tracker.states, mission_stress)
        safe_horizon = self.rul_estimator.compute_mission_safe_horizon(
            self.degradation_tracker.states, mission_stress,
            f"Phase: {phase_enum.value}, Alt: {altitude:.0f}ft"
        )
        
        # --- STEP 15: Mission risk ---
        mission_risk = self.risk_engine.assess(
            mission=self.mission_model.current_mission,
            health=health,
            degradation=self.degradation_tracker.states,
            safe_horizon=safe_horizon,
            fault_severity=fault_severity,
            fault_subsystem=fault_subsystem,
            mission_model=self.mission_model,
        )
        
        # --- STEP 16: Evidence chain ---
        evidence_chain = self.evidence_builder.build_chain(diagnosis)
        recommendation = self.evidence_builder.generate_recommendation(
            diagnosis, mission_risk.mission_risk_score, safe_horizon.safe_hours
        )
        
        # --- STEP 17: Calibration (during healthy periods) ---
        is_healthy = not anomaly.is_anomalous and fault_severity < 0.1
        self.calibrator.update(residuals, is_healthy)
        
        # --- STEP 18: Update state manager ---
        self.state_manager.update_telemetry(engine_state, sensor_frame)
        if self.state_manager.telemetry_frame:
            self.state_manager.telemetry_frame.altitude_ft = altitude
            self.state_manager.telemetry_frame.ambient_temp_c = self.environment.ambient_temp_c
            self.state_manager.telemetry_frame.ambient_pressure_inhg = self.environment.ambient_pressure_inhg
            self.state_manager.telemetry_frame.mission_phase = phase_enum.value if hasattr(phase_enum, 'value') else str(phase)
        self.state_manager.update_health(health)
        self.state_manager.update_diagnosis(diagnosis)
        self.state_manager.engine_rul = self.rul_estimator.engine_rul
        self.state_manager.mission_safe_horizon = safe_horizon
        self.state_manager.mission_risk = mission_risk
        self.state_manager.residuals = {k: round(v, 3) for k, v in residuals.items()}
        self.state_manager.expected_values = expected_values
        self.state_manager.residual_details = self.residual_engine.get_all_residuals()
        self.state_manager.drift_info = drift_info
        self.state_manager.evidence_chain = evidence_chain
        self.state_manager.active_faults = self.fault_injector.get_active_faults(self.simulation_time)
        self.state_manager.recommendation = recommendation
        return self.state_manager.get_full_state()

    async def _simulation_loop(self):
        """Main simulation loop — the heartbeat."""
        target_dt = self.dt
        
        while self.running:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            
            loop_start = time.monotonic()
            
            # Step the simulation
            self.step(target_dt)
            
            # Broadcast to WebSocket clients
            await self._broadcast_telemetry()
            
            # Timing
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, target_dt - elapsed)
            await asyncio.sleep(sleep_time)

    async def _broadcast_telemetry(self):
        """Send telemetry to all WebSocket clients."""
        if not self._ws_clients:
            return
        
        state = self.state_manager.get_full_state()
        
        dead_clients = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(state)
            except Exception:
                dead_clients.append(ws)
        
        for ws in dead_clients:
            self._ws_clients.remove(ws)

    def get_available_faults(self) -> list[dict]:
        return self.fault_injector.list_available_faults()

    def get_state(self) -> dict:
        return self.state_manager.get_full_state()

    def get_health(self) -> dict:
        return self.health_state.scores.model_dump()

    def get_diagnosis(self) -> dict:
        return self.state_manager._diagnosis_summary()

    def get_mission_info(self) -> dict:
        return {
            "mission": self.mission_model.get_mission_summary(),
            "risk": self.state_manager.mission_risk.model_dump() if self.state_manager.mission_risk else {},
            "readiness": self.readiness_assessor.assess(
                self.health_state.scores,
                self.mission_model.current_mission,
                self.rul_estimator.mission_safe_horizon or self.rul_estimator.compute_mission_safe_horizon(self.degradation_tracker.states),
            ),
            "safe_horizon": self.state_manager.mission_safe_horizon.model_dump() if self.state_manager.mission_safe_horizon else {},
        }


# Global singleton
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
