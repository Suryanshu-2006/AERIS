# AERIS — Aerospace Engine Risk & Intelligence System
### AI-Enabled Real-Time Digital Twin System for Aero Piston Engines in MALE UAVs
**Smart India Hackathon (SIH 2026) — Problem Statement: SIH26054 | Organization: DRDO**

[![Tests](https://img.shields.io/badge/Tests-14%2F14%20Passing-emerald)](#)
[![Validation](https://img.shields.io/badge/Validation-6%2F6%20Checks%20100%25-cyan)](#)
[![Architecture](https://img.shields.io/badge/Architecture-Digital%20Twin%2020Hz-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-slate)](#)

---

## 1. Executive Summary & Problem Statement

Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicles (UAVs) rely heavily on turbocharged aero piston engines (Rotax 914 class) for extended surveillance and reconnaissance missions (12 to 24+ hours) at altitudes up to 28,000 ft.

Traditional condition monitoring systems suffer from three critical flaws:
1. **Isolated threshold alarms**: Flag abnormal telemetry only after catastrophic threshold exceedance occurs.
2. **False alarms from sensor anomalies**: A single damaged thermocouple or sensor bias is frequently misdiagnosed as critical mechanical engine failure, causing unnecessary mission aborts.
3. **No mission-awareness**: Existing systems cannot answer whether an engine with minor degradation can safely complete a 6-hour loiter, or what happens if the UAV climbs to 25,000 ft or ambient temperature shifts from 15°C to 40°C.

**AERIS** solves this through a unified digital twin architecture:

$$\textbf{Engine Digital Twin} + \textbf{Mission Digital Twin} + \textbf{Predictive Intelligence} + \textbf{Counterfactual Simulation}$$

---

## 2. The Three Core Operational Answers

| Operational Question | AERIS Digital Twin Mechanism | Output Provided |
|---|---|---|
| **1. What is happening now?** | Continuous 20Hz non-linear physics simulation vs telemetry state estimation + cross-channel peer sensor validation | Sensor integrity score, residual decomposition ($z$-scores), multivariate anomaly flag |
| **2. What is likely to happen next?** | Stress-weighted component degradation tracking + trend extrapolation with uncertainty intervals | Component Remaining Useful Life (RUL), Mission-Safe Horizon hours, subsystem health indices (0-100) |
| **3. Can the engine safely complete the mission under changed conditions?** | Counterfactual What-If Simulator: dynamically alters flight profiles (altitude, temp, loiter) and reruns full engine physics | Comparative risk delta ($\Delta$), safe horizon margin ($\Delta$), critical flight phase, and operational advisory |

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    AERIS GROUND CONTROL                    │
│      React • TypeScript • TailwindCSS • Three.js 3D Twin   │
└─────────────────────────────▲──────────────────────────────┘
                              │ WebSocket (20Hz) / REST API
┌─────────────────────────────┴──────────────────────────────┐
│                    FASTAPI BACKEND CORE                    │
│                                                            │
│  ┌─────────────────────────┐    ┌────────────────────────┐ │
│  │   ENGINE DIGITAL TWIN   │    │  MISSION DIGITAL TWIN  │ │
│  │ • 4-Cyl Boxer Physics   │    │ • Flight Phases        │ │
│  │ • Combustion & Cooling  │    │ • Risk Engine          │ │
│  │ • Lubrication & Turbo   │    │ • What-If Simulator    │ │
│  └────────────┬────────────┘    └───────────┬────────────┘ │
│               │                             │              │
│  ┌────────────▼─────────────────────────────▼────────────┐ │
│  │                   AI & INTELLIGENCE                   │ │
│  │ • Sensor Integrity (Stuck/Bias/Drift Disentanglement) │ │
│  │ • Multi-Hypothesis Fault Diagnosis                   │ │
│  │ • Degradation Tracking & RUL Estimation               │ │
│  │ • Explainability Evidence Chains                      │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

## 4. Quickstart & Installation

### Prerequisites
- Python 3.10+ (Tested on Python 3.12 / 3.14)
- Node.js v18+ and npm

### 4.1 Backend Setup
```bash
# Install backend dependencies
pip install -r requirements.txt
```

### 4.2 Frontend Setup
```bash
cd aerotwin/frontend
npm install
```

---

## 5. Running the System

### 5.0 Windows One-Click Batch Launchers (.bat)
For quick local execution on Windows, double-click any of the following scripts from the project root:
* **[`start_aeris.bat`](file:///d:/Workshop/SIH/A.E.R.I.S/start_aeris.bat)**: Launches backend server, starts frontend dev server, and automatically opens `http://localhost:5173` in your default browser.
* **[`run_demo_cli.bat`](file:///d:/Workshop/SIH/A.E.R.I.S/run_demo_cli.bat)**: Runs the 17-step operational storyline terminal demo and holds the window open for review.
* **[`run_validation.bat`](file:///d:/Workshop/SIH/A.E.R.I.S/run_validation.bat)**: Executes the complete automated verification & validation suite.
* **[`install_dependencies.bat`](file:///d:/Workshop/SIH/A.E.R.I.S/install_dependencies.bat)**: Installs both Python backend and Node frontend dependencies.

### 5.1 Interactive Terminal Storyline Demo
Runs the complete 17-step operational narrative from pre-flight to degradation, diagnosis, what-if counterfactual rerun, and operational recommendation:
```bash
python scripts/run_demo.py
```

### 5.2 Launching the Complete Web Ground Control System

**Terminal 1 — Backend Server:**
```bash
python scripts/run_demo.py --server
# Starts FastAPI server on http://localhost:8000
# WebSocket stream active on ws://localhost:8000/ws/telemetry
```

**Terminal 2 — Frontend Cockpit:**
```bash
cd aerotwin/frontend
npm run dev
# Open http://localhost:5173 in browser
```

### 5.3 Automated Engineering Validation Suite
Runs the physics consistency checks, sensor fault separation test, counterfactual fidelity evaluation, and all 14 unit/integration tests:
```bash
python scripts/run_validation.py
```

### 5.4 Predefined Scenario Dataset Generator
Generates reproducible CSV telemetry and JSON summary datasets for all 10 validation scenarios into `data/scenarios/`:
```bash
python scripts/generate_scenarios.py
```

---

## 6. Predefined Validation Scenarios

1. `SCENARIO_01`: **Healthy Cruise** (Baseline nominal 20k ft surveillance)
2. `SCENARIO_02`: **Oil Pressure Loss** (Progressive seal degradation, friction, and vibration rise)
3. `SCENARIO_03`: **Turbo Boost Deficiency** (Wastegate leak causing manifold pressure deficit at altitude)
4. `SCENARIO_04`: **Cylinder 2 Cooling Degradation** (Cooling fin obstruction causing localized CHT rise)
5. `SCENARIO_05`: **Crankshaft Bearing Wear** (Journal bearing wear with elevated vibration spectrum)
6. `SCENARIO_06`: **EGT3 Sensor Fault** (Isolated thermocouple bias; **proven sensor vs engine fault separation**)
7. `SCENARIO_07`: **Combined Sensor + Engine Anomaly** (Simultaneous oil sensor bias and bearing wear)
8. `SCENARIO_08`: **Unknown Anomaly** (Open-world non-cataloged anomaly pattern)
9. `SCENARIO_09`: **High-Altitude Mission** (28,000 ft operational ceiling stress)
10. `SCENARIO_10`: **Long-Duration Loiter Mission** (Extended 3-hour surveillance wear accumulation)

---

## 7. Interactive Ground Control Dashboard

- **3D Engine Digital Twin**: Three.js WebGL canvas displaying 4 opposed cylinders, crankcase, turbocharger, oil sump, propeller spinning at engine RPM, and live color-coded thermal halos (green healthy, amber caution, red degraded).
- **Subsystem Health Index**: Circular health gauge (0-100), predicted RUL with confidence intervals, and Mission-Safe Horizon hours.
- **Decomposed Telemetry**: View mode toggle between **Measured (Sensor)**, **Expected (Digital Twin Truth)**, and **Residuals ($\sigma$)**.
- **Root Cause Diagnosis**: Multi-hypothesis scoring, sensor integrity table, step-by-step evidence chain, and operational recommendation banner.
- **Counterfactual Mission Simulator**: Sliders for altitude, ambient temperature, loiter duration, and throttle with live physics recalculation.
- **Fault Injector Matrix**: Modal to inject mechanical or sensor faults at specified severities.

---

## 8. Limitations & Engineering Disclaimers

1. **Demonstrator Model**: The engine physics model represents a physics-informed demonstrator based on general principles of 4-stroke turbocharged aircraft engines. It is **not** an exact certified DRDO engine model.
2. **Advisory Decision Support**: All RUL estimates, safe horizon bounds, and operational recommendations are software decision-support calculations and do **not** constitute certified flight clearance.
