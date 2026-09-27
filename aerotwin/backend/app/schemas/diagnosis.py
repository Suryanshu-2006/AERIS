"""
Diagnosis Schemas — Pydantic models for fault diagnosis, anomaly, and explainability.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class FaultCategory(str, Enum):
    MECHANICAL = "MECHANICAL"
    SENSOR = "SENSOR"
    MODEL_MISMATCH = "MODEL_MISMATCH"
    UNKNOWN = "UNKNOWN"


class FaultSeverity(str, Enum):
    HEALTHY = "HEALTHY"        # 0.0
    MILD = "MILD"              # 0.25
    MODERATE = "MODERATE"      # 0.5
    SEVERE = "SEVERE"          # 0.75
    CRITICAL = "CRITICAL"      # 1.0

    @staticmethod
    def from_value(v: float) -> "FaultSeverity":
        if v < 0.1:
            return FaultSeverity.HEALTHY
        elif v < 0.35:
            return FaultSeverity.MILD
        elif v < 0.6:
            return FaultSeverity.MODERATE
        elif v < 0.85:
            return FaultSeverity.SEVERE
        else:
            return FaultSeverity.CRITICAL


class AnomalyResult(BaseModel):
    """Result from anomaly detection engine."""
    timestamp: float = 0.0
    anomaly_score: float = Field(0.0, ge=0.0, le=1.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    persistence: int = 0  # consecutive anomalous frames
    severity: FaultSeverity = FaultSeverity.HEALTHY
    is_anomalous: bool = False
    anomalous_channels: list[str] = []
    description: str = ""


class SensorIntegrityResult(BaseModel):
    """Sensor integrity analysis for a single sensor."""
    sensor_name: str
    integrity_score: float = Field(1.0, ge=0.0, le=1.0)
    is_faulty: bool = False
    fault_type: str = ""  # BIAS, STUCK, DRIFT, INTERMITTENT, HEALTHY
    evidence: list[str] = []
    confidence: float = 0.0


class EvidenceItem(BaseModel):
    """Single piece of evidence in the explainability chain."""
    category: str  # OBSERVATION, PHYSICS, CORRELATION, TEMPORAL, SENSOR_CHECK
    description: str
    signal_name: str = ""
    value: Optional[float] = None
    expected: Optional[float] = None
    deviation_sigma: Optional[float] = None
    supports_hypothesis: str = ""
    weight: float = 1.0


class FaultHypothesis(BaseModel):
    """A fault hypothesis with confidence and evidence."""
    fault_id: str
    fault_name: str
    category: FaultCategory
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    severity: float = Field(0.0, ge=0.0, le=1.0)
    severity_label: FaultSeverity = FaultSeverity.HEALTHY
    subsystem: str = ""
    affected_components: list[str] = []
    evidence: list[EvidenceItem] = []


class DiagnosisResult(BaseModel):
    """Complete diagnosis output with multiple hypotheses."""
    timestamp: float
    primary_fault: Optional[FaultHypothesis] = None
    alternative_hypotheses: list[FaultHypothesis] = []
    sensor_integrity: list[SensorIntegrityResult] = []
    anomaly: AnomalyResult = Field(default_factory=AnomalyResult)
    
    # Evidence chain (for explainability)
    observation: str = ""
    physics_evidence: str = ""
    correlated_signals: str = ""
    diagnosis_summary: str = ""
    confidence_explanation: str = ""
    severity_explanation: str = ""
    mission_consequence: str = ""
    recommendation: str = ""


class Recommendation(str, Enum):
    CONTINUE = "CONTINUE"
    MONITOR = "MONITOR"
    REDUCE_LOAD = "REDUCE_LOAD"
    SHORTEN_LOITER = "SHORTEN_LOITER"
    RETURN_TO_BASE = "RETURN_TO_BASE"
    INSPECT_BEFORE_NEXT = "INSPECT_BEFORE_NEXT_MISSION"
    ABORT_MISSION = "ABORT_MISSION"
