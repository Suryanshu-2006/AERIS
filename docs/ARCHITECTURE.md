# AERIS System Architecture

**Aerospace Engine Risk & Intelligence System (AERIS)**  
*Smart India Hackathon SIH26054 — AI-Enabled Real-Time Digital Twin System for Aero Piston Engines in MALE UAVs*

---

## 1. High-Level Concept

AERIS is structured around the core paradigm:

$$\textbf{Engine Digital Twin} + \textbf{Mission Digital Twin} + \textbf{Predictive Intelligence} + \textbf{Counterfactual Simulation}$$

The system answers three mission-critical questions in real time at 20 Hz:
1. **What is happening to the engine now?** (State estimation, sensor integrity, and anomaly detection)
2. **What is likely to happen next?** (Physics degradation tracking, component RUL, and Mission-Safe Horizon)
3. **Can the engine safely complete the mission, and what happens if conditions change?** (Mission risk engine and counterfactual what-if simulation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             FLIGHT ENVIRONMENT                              │
│                    (Altitude, ISA Pressure/Temp, Wind)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────┐                     ┌───────────────────────────┐
│     PHYSICAL ENGINE       │                     │    DIGITAL TWIN MODEL     │
│   (True Subsystem State)  │                     │   (Physics-Based Truth)   │
└─────────────┬─────────────┘                     └─────────────┬─────────────┘
              │                                                 │
              ▼                                                 │
┌───────────────────────────┐                                   │
│       SENSOR MODEL        │                                   │
│  (Noise, Bias, Transducer)│                                   │
└─────────────┬─────────────┘                                   │
              │                                                 │
              └────────────────────────┬────────────────────────┘
                                       ▼
                        ┌───────────────────────────┐
                        │      RESIDUAL ENGINE      │
                        │     $r = (y - \hat{y})/\sigma$   │
                        └──────────────┬────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────┐
                        │     INTELLIGENCE SUITE    │
                        │ • Sensor Integrity        │
                        │ • Anomaly Detection       │
                        │ • Multi-Hypothesis Diag   │
                        │ • Degradation & RUL       │
                        │ • Explainability Chain    │
                        └──────────────┬────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────┐
                        │    MISSION DIGITAL TWIN   │
                        │ • Per-Phase Stress        │
                        │ • Mission Risk Engine     │
                        │ • Counterfactual What-If  │
                        │ • Operational Advisory    │
                        └──────────────┬────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────┐
                        │   GROUND CONTROL STATION  │
                        │ (FastAPI + WebSocket + UI)│
                        └───────────────────────────┘
```

---

## 2. Subsystem Breakdown

### 2.1 Backend Modules (`aerotwin/backend/app/`)

| Module | Location | Purpose |
|---|---|---|
| **Simulation** | `simulation/` | Master engine physics, combustion, cooling, lubrication, turbocharger, vibration, and sensor modeling |
| **Faults** | `simulation/faults.py` | Injects physical and sensor faults with progressive ramp-up dynamics |
| **Digital Twin** | `twin/` | Expected behavior model, state estimator, residual engine, and model drift monitor |
| **AI / Diagnosis** | `ai/` | Multivariate anomaly detection, sensor integrity analyzer, multi-hypothesis diagnosis engine |
| **Prognostics** | `prognostics/` | Component degradation tracking, RUL estimation with uncertainty bounds, and Mission-Safe Horizon |
| **Explainability** | `explainability/` | Evidence chain constructor and human-readable operational explainer |
| **Mission Twin** | `mission/` | Multi-phase mission model, mission risk engine, readiness assessor, and counterfactual what-if simulator |
| **Core** | `core/` | Central `Orchestrator`, `StateManager`, and decoupled `EventBus` |
| **API** | `api/` | FastAPI REST endpoints for telemetry, simulation control, missions, faults, and WebSocket streaming |

---

## 3. Real-Time Data Pipeline (20 Hz)

Each simulation tick executes in exact sequence:
1. **Flight Conditions**: Interpolates mission profile altitude, target throttle, and flight phase; updates ISA atmospheric model.
2. **Physical Fault Application**: Adjusts internal subsystem parameters (pump efficiency, fin airflow, wastegate).
3. **Engine Simulation**: Advances continuous non-linear differential and algebraic engine equations.
4. **Sensor Measurement**: Applies sensor transfer functions, thermal noise, and active sensor faults (bias, stuck, drift).
5. **Twin Prediction**: Physics model calculates healthy expected values for all observed channels.
6. **State Estimation**: Computes fused state estimates combining sensor observations with model truth.
7. **Residual Calculation**: Computes normalized statistical residuals $z_i = \frac{y_i - \hat{y}_i}{\sigma_i}$.
8. **Sensor Integrity Analysis**: Cross-validates peer sensors (e.g. EGT1..4) to detect single-channel bias/stuck conditions.
9. **Multivariate Anomaly Detection**: Evaluates multi-channel residual vectors against dynamic threshold boundaries.
10. **Fault Diagnosis**: Matches residual signatures against fault matrix; separates sensor artifacts from mechanical engine failure.
11. **Health Scoring**: Updates subsystem and aggregate health indices (0-100).
12. **Degradation Tracking**: Integrates thermal, pressure, and mechanical wear over operating hours.
13. **RUL & Safe Horizon**: Projects remaining hours to failure threshold and calculates mission safe horizon under current phase stress.
14. **Mission Risk Evaluation**: Assesses remaining phase risks, critical phase, and overall flight readiness.
15. **Explainability Audit**: Assembles evidence chain and generates operational advisory recommendation.
16. **Broadcast**: Dispatches JSON state snapshot to connected ground control clients over WebSockets.
