# AERIS Validation & Verification Methodology

**SIH26054 — Engineering Validation Suite**

---

## 1. Principles of Non-Circular Validation

In AI-enabled digital twin systems, circular validation occurs when synthetic training distributions mirror validation datasets without variation.

AERIS enforces strict non-circularity:
1. **Model Generates Physics Truth**: Baseline digital twin has zero knowledge of injected fault IDs or timestamps.
2. **Independent Disturbance Seeds**: Scenarios vary altitude (0 to 28,000 ft), ambient temperature (-20°C to +45°C), and random seed noise.
3. **Cross-Domain Separation**: The anomaly detector flags deviations purely on statistical residual sigma levels ($z > 3.0$), without knowing ground-truth fault classifications.
4. **Unknown Anomaly Assessment**: Scenario 8 introduces a non-cataloged anomaly pattern to test open-world robustness.

---

## 2. Predefined Validation Scenarios (10 Scenarios)

| Scenario ID | Name | Subsystem / Fault Tested | Expected Behavior |
|---|---|---|---|
| `SCENARIO_01` | Healthy Cruise | Baseline Normal | 0 anomalies, health > 95%, RUL > 15h |
| `SCENARIO_02` | Oil Pressure Loss | Lubrication | $P_{oil}$ drops, friction rises, risk increases, RTB recommended |
| `SCENARIO_03` | Turbo Boost Deficiency | Turbocharger | Boost loss at 20k ft, MAP decreases, climb throttled |
| `SCENARIO_04` | Cylinder 2 Cooling Degradation | Cooling System | CYL 2 CHT rises > 220°C, peer CHTs normal |
| `SCENARIO_05` | Bearing Wear | Mechanical | High-frequency vibration rises, pump wear increases |
| `SCENARIO_06` | EGT3 Sensor Fault | Sensor Integrity | EGT3 reading biased +150°C; **diagnosed as SENSOR FAULT, NOT mechanical failure** |
| `SCENARIO_07` | Combined Sensor + Engine Anomaly | Dual Subsystems | Oil sensor bias AND bearing wear correctly separated |
| `SCENARIO_08` | Unknown Anomaly | Open-World AI | Unclassified anomaly flagged as `UNKNOWN_ANOMALY` |
| `SCENARIO_09` | High-Altitude Mission | Operational Envelope | 28,000 ft ceiling testing turbo and thermal margin |
| `SCENARIO_10` | Long Loiter Mission | Prognostics | 3-hour continuous loiter wear accumulation |

---

## 3. Automated Test Suite Metrics

Validation tests are automated via `pytest` and `scripts/run_validation.py`:

```
=================================================================
  VALIDATION SUMMARY: 6/6 PASSED (100.0%)
=================================================================
  [PASS] Physics :: ISA Atmosphere Pressure/Temp Lapse
  [PASS] Physics :: Throttle Power Scaling
  [PASS] Physics :: Cylinder Thermal Heat Transfer
  [PASS] Sensor Integrity :: Isolated Sensor Bias Disentanglement
  [PASS] Counterfactual :: Full Physics Rerun on Parameter Alteration
  [PASS] Test Suite :: Pytest Suite (14 unit/integration tests)
```
Report is automatically exported to `data/validation_report.json`.
