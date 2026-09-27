"""
Generate Scenarios Script
Runs all 10 validation scenarios through the AERIS Digital Twin engine
and outputs telemetry, residual, and diagnosis datasets in CSV and JSON formats.
"""
import os
import sys
import json
import csv

# Ensure backend is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "aerotwin", "backend")))

from app.core.orchestrator import Orchestrator
from app.data.scenarios import SCENARIOS, apply_scenario
from app.config import get_config


def generate_all_scenarios(output_dir="data/scenarios", duration_seconds=60.0, step_dt=0.05):
    """Run each scenario and export telemetry and diagnosis timeline."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"============================================================")
    print(f"  AERIS — Scenario Dataset Generator")
    print(f"  Exporting 10 Predefined UAV Engine Scenarios to {output_dir}")
    print(f"============================================================\n")

    summary_manifest = []

    for sc_id, scenario in SCENARIOS.items():
        print(f"[*] Generating {sc_id}: {scenario.name}...")
        orch = Orchestrator()
        apply_scenario(orch, scenario)
        
        # Collect timeseries
        telemetry_rows = []
        events = []
        
        steps = int(duration_seconds / step_dt)
        for step_i in range(steps):
            # Advance simulation step
            orch.step(dt=step_dt)
            state_snap = orch.state_manager.get_full_state()
            
            t = state_snap.get("timestamp", step_i * step_dt)
            tel = state_snap.get("telemetry", {})
            diag = state_snap.get("diagnosis", {})
            health = state_snap.get("health", {})
            risk = state_snap.get("mission_risk", {})
            
            row = {
                "timestamp": round(t, 2),
                "rpm": tel.get("rpm", 0.0),
                "manifold_pressure_inhg": tel.get("manifold_pressure_inhg", 0.0),
                "egt_mean": tel.get("mean_egt_c", 0.0),
                "egt_1": tel.get("egt_1", 0.0),
                "egt_2": tel.get("egt_2", 0.0),
                "egt_3": tel.get("egt_3", 0.0),
                "egt_4": tel.get("egt_4", 0.0),
                "cht_mean": tel.get("mean_cht_c", 0.0),
                "cht_1": tel.get("cht_1", 0.0),
                "cht_2": tel.get("cht_2", 0.0),
                "cht_3": tel.get("cht_3", 0.0),
                "cht_4": tel.get("cht_4", 0.0),
                "oil_pressure_psi": tel.get("oil_pressure_psi", 0.0),
                "oil_temp_c": tel.get("oil_temperature_c", 0.0),
                "vibration_g": tel.get("vibration_g", 0.0),
                "fuel_flow_gph": tel.get("fuel_flow_gph", 0.0),
                "engine_health": health.get("engine", 100.0),
                "anomaly_score": diag.get("anomaly", {}).get("anomaly_score", 0.0),
                "is_anomalous": diag.get("anomaly", {}).get("is_anomalous", False),
                "mission_risk_score": risk.get("mission_risk_score", 0.0),
            }
            telemetry_rows.append(row)
            
            if row["is_anomalous"] and not any(e["type"] == "ANOMALY_START" for e in events):
                events.append({
                    "timestamp": round(t, 2),
                    "type": "ANOMALY_START",
                    "details": diag.get("anomaly", {}).get("description", "Anomaly detected"),
                })
        
        # Save CSV
        csv_path = os.path.join(output_dir, f"{sc_id.lower()}_telemetry.csv")
        if telemetry_rows:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(telemetry_rows[0].keys()))
                writer.writeheader()
                writer.writerows(telemetry_rows)
        
        # Save JSON metadata & summary
        meta_path = os.path.join(output_dir, f"{sc_id.lower()}_summary.json")
        sc_data = {
            "scenario_id": sc_id,
            "name": scenario.name,
            "description": scenario.description,
            "seed": scenario.seed,
            "duration_seconds": duration_seconds,
            "events": events,
            "final_health": telemetry_rows[-1]["engine_health"] if telemetry_rows else 100.0,
            "final_risk": telemetry_rows[-1]["mission_risk_score"] if telemetry_rows else 0.0,
            "csv_file": f"{sc_id.lower()}_telemetry.csv",
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(sc_data, f, indent=2)
            
        summary_manifest.append(sc_data)
        print(f"    [+] Saved {csv_path} ({len(telemetry_rows)} frames)")

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary_manifest, f, indent=2)
    print(f"\n[OK] Generated all 10 scenarios successfully. Manifest saved to {manifest_path}\n")


if __name__ == "__main__":
    generate_all_scenarios()
