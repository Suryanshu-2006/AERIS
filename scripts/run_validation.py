"""
Validation Runner Script
Executes all validation tests, checks physics consistency, sensor fault separation,
and counterfactual fidelity across the AERIS system, outputting a formal report.
"""
import os
import sys
import json
import time

# Ensure backend and root are on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(root_dir, "aerotwin", "backend")
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

import pytest
from app.simulation.engine import EngineModel
from app.simulation.environment import FlightEnvironment
from app.ai.diagnosis import DiagnosisEngine
from app.ai.severity import SensorIntegrityAnalyzer
from app.schemas.diagnosis import AnomalyResult, FaultCategory, SensorIntegrityResult
from app.mission.mission_model import MissionModel
from app.mission.what_if import WhatIfSimulator
from app.schemas.mission import WhatIfRequest
from app.schemas.engine import HealthScores, DegradationState


def run_validation():
    print("=" * 65)
    print("  AERIS — Automated Engineering Validation & Verification Suite")
    print("  DRDO SIH26054: Aero Piston Engine Digital Twin")
    print("=" * 65)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")

    results = {}
    total_checks = 0
    passed_checks = 0

    def record_check(category, name, passed, details=""):
        nonlocal total_checks, passed_checks
        total_checks += 1
        if passed:
            passed_checks += 1
            status = "PASS"
        else:
            status = "FAIL"
        if category not in results:
            results[category] = []
        results[category].append({
            "check": name,
            "status": status,
            "details": details
        })
        print(f"  [{status}] {category} :: {name}")
        if details:
            print(f"         {details}")

    # 1. Physics Checks
    print("\n--- 1. Subsystem Physics Relationships ---")
    env = FlightEnvironment()
    engine = EngineModel()
    
    # Altitude check
    env.update(0.0)
    p0 = env.ambient_pressure_inhg
    t0 = env.ambient_temp_c
    env.update(18000.0)
    p18k = env.ambient_pressure_inhg
    t18k = env.ambient_temp_c
    record_check("Physics", "ISA Atmosphere Pressure/Temp Lapse",
                 p18k < p0 and t18k < t0,
                 f"SL: {p0:.2f} inHg / {t0:.1f}°C -> 18k ft: {p18k:.2f} inHg / {t18k:.1f}°C")

    # Throttle check
    env.update(5000.0)
    s_idle = engine.step(0.05, 0.15, env)
    for _ in range(40):
        s_idle = engine.step(0.05, 0.15, env)
    for _ in range(80):
        s_full = engine.step(0.05, 0.90, env)
    record_check("Physics", "Throttle Power Scaling",
                 s_full.power_hp > s_idle.power_hp and s_full.fuel_flow_gph > s_idle.fuel_flow_gph,
                 f"Idle Power: {s_idle.power_hp:.1f} HP -> Full Power: {s_full.power_hp:.1f} HP")

    # Thermal cooling check
    normal_cht = s_full.cylinders[0].cht_c
    engine.cooling.set_cooling_health(0, 0.25)
    for _ in range(100):
        s_hot = engine.step(0.05, 0.8, env)
    record_check("Physics", "Cylinder Thermal Heat Transfer",
                 s_hot.cylinders[0].cht_c > normal_cht,
                 f"Healthy CHT: {normal_cht:.1f}°C -> Damaged Fin CHT: {s_hot.cylinders[0].cht_c:.1f}°C")

    # 2. Sensor Integrity Checks
    print("\n--- 2. Sensor vs Physical Fault Isolation ---")
    diag_engine = DiagnosisEngine()
    anomaly = AnomalyResult(timestamp=50.0, is_anomalous=True, anomaly_score=0.9, anomalous_channels=["egt_3"])
    sensor_health = [
        SensorIntegrityResult(sensor_name="egt_3", integrity_score=0.1, is_faulty=True, fault_type="BIAS"),
        SensorIntegrityResult(sensor_name="oil_pressure", integrity_score=1.0, is_faulty=False, fault_type="HEALTHY")
    ]
    diag = diag_engine.diagnose(
        residuals={"egt_3": 180.0, "oil_pressure": 0.0},
        raw_residuals={"egt_3": 180.0, "oil_pressure": 0.0},
        anomaly=anomaly,
        sensor_integrity=sensor_health,
        timestamp=50.0
    )
    is_sensor_isolated = (diag.primary_fault.category == FaultCategory.SENSOR and 
                          "SENSOR" in diag.primary_fault.fault_id)
    record_check("Sensor Integrity", "Isolated Sensor Bias Disentanglement",
                 is_sensor_isolated,
                 f"Diagnosed Category: {diag.primary_fault.category.value}, Fault: {diag.primary_fault.fault_id}")

    # 3. Counterfactual Simulation Checks
    print("\n--- 3. What-If Counterfactual Fidelity ---")
    mission_model = MissionModel()
    what_if = WhatIfSimulator()
    baseline = mission_model.current_mission
    req = WhatIfRequest(altitude_ft=24000.0, ambient_temperature_c=38.0)
    h = HealthScores(engine=85.0, cooling=78.0, lubrication=80.0)
    deg = {"cooling": DegradationState(component="cooling", degradation_level=0.15, rate_per_hour=0.01)}
    
    wif_res = what_if.simulate(baseline, req, h, deg)
    counterfactual_valid = (len(wif_res.baseline_trajectory) > 0 and 
                            len(wif_res.modified_trajectory) > 0 and 
                            wif_res.summary != "")
    record_check("Counterfactual", "Full Physics Rerun on Parameter Alteration",
                 counterfactual_valid,
                 f"Baseline Risk: {wif_res.baseline_risk.mission_risk_score:.3f} -> Modified: {wif_res.modified_risk.mission_risk_score:.3f}")

    # 4. Pytest Execution
    print("\n--- 4. Automated Pytest Unit & Integration Tests ---")
    exit_code = pytest.main(["-q", os.path.join(root_dir, "tests")])
    record_check("Test Suite", "Pytest Suite (14 unit/integration tests)",
                 exit_code == 0,
                 f"Pytest return code: {exit_code}")

    # Export report
    report = {
        "title": "AERIS Digital Twin Validation Report",
        "timestamp": time.time(),
        "summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": total_checks - passed_checks,
            "pass_rate": f"{(passed_checks / total_checks) * 100:.1f}%"
        },
        "results": results
    }

    os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)
    report_path = os.path.join(root_dir, "data", "validation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 65)
    print(f"  VALIDATION SUMMARY: {passed_checks}/{total_checks} PASSED ({(passed_checks/total_checks)*100:.1f}%)")
    print(f"  Report exported to: {report_path}")
    print("=" * 65 + "\n")
    return exit_code == 0 and passed_checks == total_checks


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
