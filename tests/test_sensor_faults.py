"""
Sensor vs Engine Fault Separation Tests
Verifies that:
1. A single sensor fault (e.g. EGT3 bias or stuck) is detected as a SENSOR fault
2. Single sensor fault does NOT trigger mechanical engine failure diagnosis
3. Cross-channel discrepancy is flagged by the SensorIntegrityAnalyzer
"""
import pytest
import numpy as np
from app.ai.severity import SensorIntegrityAnalyzer
from app.ai.diagnosis import DiagnosisEngine
from app.schemas.diagnosis import AnomalyResult, FaultCategory, SensorIntegrityResult


def test_sensor_integrity_detects_stuck_sensor():
    """Verify that a stuck sensor value is identified by SensorIntegrityAnalyzer."""
    analyzer = SensorIntegrityAnalyzer(window_size=30)
    
    # Send stuck value with zero variance for 25 steps
    for _ in range(25):
        sensor_values = {"egt_3": 750.0, "egt_1": 740.0 + np.random.randn() * 3.0}
        residuals = {"egt_3": 5.0, "egt_1": 0.5}
        confidences = {"egt_3": 1.0, "egt_1": 1.0}
        results = analyzer.analyze(sensor_values, residuals, confidences)
        
    egt3_result = next((r for r in results if r.sensor_name == "egt_3"), None)
    assert egt3_result is not None
    assert egt3_result.fault_type == "STUCK" or egt3_result.is_faulty, "Stuck sensor must be flagged"


def test_sensor_integrity_detects_isolated_bias():
    """Verify single channel large residual with normal sister channels is flagged as sensor fault."""
    analyzer = SensorIntegrityAnalyzer(window_size=30)
    
    # EGT 1, 2, 4 are ~720, but EGT 3 is reading 880 (isolated sensor bias)
    for _ in range(25):
        sensor_values = {
            "egt_1": 720.0 + np.random.randn() * 2.0,
            "egt_2": 722.0 + np.random.randn() * 2.0,
            "egt_3": 880.0 + np.random.randn() * 2.0,  # Biased sensor
            "egt_4": 718.0 + np.random.randn() * 2.0,
        }
        residuals = {
            "egt_1": 0.5,
            "egt_2": 0.5,
            "egt_3": 8.5,  # High sigma residual
            "egt_4": 0.2,
        }
        confidences = {k: 1.0 for k in sensor_values}
        results = analyzer.analyze(sensor_values, residuals, confidences)
        
    egt3_res = next((r for r in results if r.sensor_name == "egt_3"), None)
    assert egt3_res is not None
    assert egt3_res.fault_type in ["DRIFT", "BIAS", "SUSPECT_ISOLATED", "SUSPECT"] or egt3_res.integrity_score < 0.9


def test_egt3_sensor_fault_does_not_cause_mechanical_failure_diagnosis():
    """Verify that an EGT3 sensor fault does NOT trigger catastrophic mechanical engine failure."""
    engine = DiagnosisEngine()
    
    # Anomaly flagged primarily on EGT3
    anomaly = AnomalyResult(
        timestamp=100.0,
        is_anomalous=True,
        anomaly_score=0.85,
        anomalous_channels=["egt_3"],
        confidence=0.9,
    )
    
    # Sensor integrity explicitly marks egt_3 as faulty/low integrity
    sensor_health = [
        SensorIntegrityResult(
            sensor_name="egt_3",
            integrity_score=0.2,
            is_faulty=True,
            fault_type="BIAS",
            confidence=0.95,
        ),
        SensorIntegrityResult(
            sensor_name="oil_pressure",
            integrity_score=1.0,
            is_faulty=False,
            fault_type="HEALTHY",
            confidence=1.0,
        ),
    ]
    
    residuals = {"egt_3": 150.0, "oil_pressure": 0.0, "cht_3": 2.0}
    raw_residuals = {"egt_3": 150.0, "oil_pressure": 0.0, "cht_3": 2.0}
    
    diagnosis = engine.diagnose(
        residuals=residuals,
        raw_residuals=raw_residuals,
        anomaly=anomaly,
        sensor_integrity=sensor_health,
        timestamp=100.0,
    )
    
    assert diagnosis.primary_fault is not None
    assert diagnosis.primary_fault.category in [FaultCategory.SENSOR, FaultCategory.UNKNOWN], (
        f"Single sensor anomaly must not be diagnosed as mechanical engine failure, got {diagnosis.primary_fault.category}"
    )
    assert diagnosis.primary_fault.fault_id != "BEARING_WEAR"
    assert diagnosis.primary_fault.fault_id != "OIL_PRESSURE_LOSS"
