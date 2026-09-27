"""
State Manager
Central state management for the simulation system.
Holds the current snapshot of the entire system state for API access.
"""
import time
import json
from collections import deque
from typing import Optional
from ..schemas.telemetry import TelemetryFrame, SensorFrame, DataSource, CylinderTelemetry
from ..schemas.engine import EngineState, HealthScores, RULEstimate, MissionSafeHorizon
from ..schemas.diagnosis import DiagnosisResult, AnomalyResult
from ..schemas.mission import MissionRiskResult, MissionProfile


class StateManager:
    """
    Holds the current and historical system state.
    This is the single source of truth for API endpoints.
    """

    def __init__(self, history_size: int = 600):
        self.history_size = history_size
        
        # Current state
        self.engine_state: Optional[EngineState] = None
        self.sensor_frame: Optional[SensorFrame] = None
        self.telemetry_frame: Optional[TelemetryFrame] = None
        self.health_scores: HealthScores = HealthScores()
        self.diagnosis: Optional[DiagnosisResult] = None
        self.anomaly: AnomalyResult = AnomalyResult()
        self.engine_rul: Optional[RULEstimate] = None
        self.mission_safe_horizon: Optional[MissionSafeHorizon] = None
        self.mission_risk: Optional[MissionRiskResult] = None
        self.current_mission: Optional[MissionProfile] = None
        self.residuals: dict[str, float] = {}
        self.residual_details: dict = {}
        self.drift_info: dict = {}
        self.evidence_chain: dict = {}
        self.active_faults: list[dict] = []
        self.recommendation: str = "CONTINUE"
        
        # Simulation metadata
        self.simulation_id: str = ""
        self.scenario_id: str = ""
        self.data_source: DataSource = DataSource.SIMULATION
        self.simulation_time: float = 0.0
        self.simulation_speed: float = 1.0
        self.is_running: bool = False
        self.is_paused: bool = False
        
        # History
        self.telemetry_history: deque = deque(maxlen=history_size)
        self.health_history: deque = deque(maxlen=history_size)
        self.anomaly_history: deque = deque(maxlen=history_size)
        self.diagnosis_history: deque = deque(maxlen=100)

    def update_telemetry(self, engine_state: EngineState, sensor_frame: SensorFrame):
        """Update current telemetry state."""
        self.engine_state = engine_state
        self.sensor_frame = sensor_frame
        self.simulation_time = engine_state.timestamp
        
        # Build telemetry frame for streaming
        cylinders = [
            CylinderTelemetry(
                cylinder_id=cyl.cylinder_id,
                egt=cyl.egt_c,
                cht=cyl.cht_c,
                combustion_efficiency=cyl.combustion_efficiency,
            )
            for cyl in engine_state.cylinders
        ]
        
        self.telemetry_frame = TelemetryFrame(
            timestamp=time.time(),
            simulation_time=engine_state.timestamp,
            data_source=self.data_source,
            simulation_id=self.simulation_id,
            scenario_id=self.scenario_id,
            rpm=engine_state.rpm,
            manifold_pressure_inhg=engine_state.manifold_pressure_inhg,
            throttle_percent=engine_state.throttle * 100,
            fuel_flow_gph=engine_state.fuel_flow_gph,
            air_flow_cfm=engine_state.air_mass_flow_gs,
            torque_nm=engine_state.torque_nm,
            power_hp=engine_state.power_hp,
            cylinders=cylinders,
            oil_pressure_psi=engine_state.oil_pressure_psi,
            oil_temperature_c=engine_state.oil_temperature_c,
            vibration_g=engine_state.vibration_g,
            bus_voltage=engine_state.bus_voltage,
            turbo_boost_psi=engine_state.turbo_boost_psi,
            turbo_rpm=engine_state.turbo_rpm,
            altitude_ft=0,  # filled from environment
            ambient_temp_c=15,
            ambient_pressure_inhg=29.92,
            flight_time_seconds=engine_state.timestamp,
        )
        
        self.telemetry_history.append({
            "time": engine_state.timestamp,
            "rpm": engine_state.rpm,
            "map": engine_state.manifold_pressure_inhg,
            "egt_mean": engine_state.mean_egt_c,
            "cht_mean": engine_state.mean_cht_c,
            "oil_press": engine_state.oil_pressure_psi,
            "oil_temp": engine_state.oil_temperature_c,
            "vibration": engine_state.vibration_g,
            "voltage": engine_state.bus_voltage,
            "fuel_flow": engine_state.fuel_flow_gph,
            "turbo": engine_state.turbo_boost_psi,
            "power": engine_state.power_hp,
        })

    def update_health(self, scores: HealthScores):
        self.health_scores = scores
        self.health_history.append({
            "time": self.simulation_time,
            "engine": scores.engine,
            "combustion": scores.combustion,
            "cooling": scores.cooling,
            "lubrication": scores.lubrication,
            "turbo": scores.turbo,
            "mechanical": scores.mechanical,
            "electrical": scores.electrical,
            "sensors": scores.sensors,
        })

    def update_diagnosis(self, diagnosis: DiagnosisResult):
        self.diagnosis = diagnosis
        self.anomaly = diagnosis.anomaly
        self.anomaly_history.append({
            "time": self.simulation_time,
            "score": diagnosis.anomaly.anomaly_score,
            "is_anomalous": diagnosis.anomaly.is_anomalous,
        })
        if diagnosis.primary_fault:
            self.diagnosis_history.append({
                "time": self.simulation_time,
                "fault": diagnosis.primary_fault.fault_name,
                "confidence": diagnosis.primary_fault.confidence,
                "severity": diagnosis.primary_fault.severity,
                "category": diagnosis.primary_fault.category.value,
            })

    def get_full_state(self) -> dict:
        """Get complete system state snapshot for API."""
        return {
            "simulation": {
                "simulation_id": self.simulation_id,
                "scenario_id": self.scenario_id,
                "data_source": self.data_source.value,
                "simulation_time": round(self.simulation_time, 2),
                "simulation_speed": self.simulation_speed,
                "is_running": self.is_running,
                "is_paused": self.is_paused,
            },
            "timestamp": round(self.simulation_time, 2),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "mode": "SIMULATION",
            "engine": self.engine_state.model_dump() if self.engine_state else {},
            "telemetry": self.telemetry_frame.model_dump() if self.telemetry_frame else (self.engine_state.model_dump() if self.engine_state else {}),
            "twin": {
                "expected": getattr(self, "expected_values", {}),
                "residuals": self.residuals,
            },
            "health": self.health_scores.model_dump(),
            "anomaly": self.anomaly.model_dump(),
            "diagnosis": self._diagnosis_summary(),
            "rul": self.engine_rul.model_dump() if self.engine_rul else {},
            "safe_horizon": self.mission_safe_horizon.model_dump() if self.mission_safe_horizon else {},
            "prognostics": {
                "engine_rul": self.engine_rul.model_dump() if self.engine_rul else {},
                "mission_safe_horizon": self.mission_safe_horizon.model_dump() if self.mission_safe_horizon else {},
            },
            "mission_risk": self.mission_risk.model_dump() if self.mission_risk else {},
            "residuals": self.residuals,
            "residual_details": self.residual_details,
            "drift": self.drift_info,
            "evidence_chain": self.evidence_chain,
            "active_faults": self.active_faults,
            "recommendation": self.recommendation,
        }

    def _diagnosis_summary(self) -> dict:
        if not self.diagnosis:
            return {}
        d = self.diagnosis
        result = {
            "observation": d.observation,
            "physics_evidence": d.physics_evidence,
            "correlated_signals": d.correlated_signals,
            "diagnosis_summary": d.diagnosis_summary,
            "confidence": d.confidence_explanation,
            "severity": d.severity_explanation,
            "mission_consequence": d.mission_consequence,
            "recommendation": d.recommendation,
        }
        if d.primary_fault:
            result["primary_fault"] = {
                "fault_id": d.primary_fault.fault_id,
                "fault_name": d.primary_fault.fault_name,
                "category": d.primary_fault.category.value,
                "confidence": d.primary_fault.confidence,
                "severity": d.primary_fault.severity,
                "severity_label": d.primary_fault.severity_label.value,
                "subsystem": d.primary_fault.subsystem,
                "affected_components": d.primary_fault.affected_components,
                "evidence": [
                    {"category": e.category, "description": e.description,
                     "deviation_sigma": e.deviation_sigma}
                    for e in d.primary_fault.evidence
                ],
            }
        if d.alternative_hypotheses:
            result["alternatives"] = [
                {
                    "fault_name": h.fault_name,
                    "category": h.category.value,
                    "confidence": h.confidence,
                    "severity": h.severity,
                }
                for h in d.alternative_hypotheses[:3]
            ]
        result["sensor_integrity"] = [
            {
                "sensor": si.sensor_name,
                "integrity": si.integrity_score,
                "is_faulty": si.is_faulty,
                "fault_type": si.fault_type,
            }
            for si in d.sensor_integrity if si.is_faulty
        ]
        return result

    def get_telemetry_history(self) -> list[dict]:
        return list(self.telemetry_history)

    def get_health_history(self) -> list[dict]:
        return list(self.health_history)

    def reset(self):
        self.engine_state = None
        self.sensor_frame = None
        self.telemetry_frame = None
        self.health_scores = HealthScores()
        self.diagnosis = None
        self.anomaly = AnomalyResult()
        self.engine_rul = None
        self.mission_safe_horizon = None
        self.mission_risk = None
        self.residuals = {}
        self.residual_details = {}
        self.drift_info = {}
        self.evidence_chain = {}
        self.active_faults = []
        self.recommendation = "CONTINUE"
        self.simulation_time = 0.0
        self.is_running = False
        self.is_paused = False
        self.telemetry_history.clear()
        self.health_history.clear()
        self.anomaly_history.clear()
        self.diagnosis_history.clear()
