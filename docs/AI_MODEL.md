# AERIS AI & Predictive Intelligence Methodology

**Predictive Intelligence, Sensor Disentanglement & Decision Support**

---

## 1. Sensor vs Physical Engine Fault Disentanglement

A critical vulnerability of naive AI monitoring is misdiagnosing a faulty sensor (e.g. an EGT thermocouple loose wire or bias) as catastrophic mechanical engine failure.

AERIS solves this with a **three-tier disentanglement strategy**:

```
                ┌───────────────────────────────────┐
                │       SENSOR OBSERVATION $y_i$    │
                └─────────────────┬─────────────────┘
                                  ▼
                ┌───────────────────────────────────┐
                │   Cross-Channel Peer Consistency  │
                │     $|y_i - \text{mean}(y_{peers})| > 3\sigma$    │
                └─────────────────┬─────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       Peer Sensors Normal?              Peer Sensors Anomalous?
                  ▼                               ▼
     ┌────────────────────────┐       ┌────────────────────────┐
     │  SENSOR INTEGRITY LOW  │       │  PHYSICAL ENGINE FAULT │
     │ (Bias / Stuck / Drift) │       │ (Combustion / Cooling) │
     └────────────────────────┘       └────────────────────────┘
```

1. **Temporal Variance Verification**: A frozen or stuck sensor exhibits near-zero variance $\sigma_{window} < 0.1 \cdot \sigma_{noise}$.
2. **Peer Redundancy**: 4 independent EGT and CHT sensors monitor identical thermal cycles. If only 1 sensor deviates while 3 peer cylinders operate normally and overall torque is maintained, the diagnosis engine flags a `SENSOR_FAULT`.
3. **Correlated Channel Physics**: Physical mechanical faults exhibit multi-channel signatures (e.g., true low oil pressure causes elevated oil temperature and increased bearing vibration).

---

## 2. Multi-Hypothesis Diagnosis Engine

The diagnosis engine evaluates likelihood scores across candidate hypotheses $H_k$:
$$P(H_k | z) \propto \prod_{j \in \text{required}} \Phi(z_j) \cdot \prod_{m \in \text{supporting}} \Psi(z_m) \cdot \prod_{n \in \text{contradicting}} [1 - \Omega(z_n)]$$

Where $z$ is the normalized residual vector. Hypotheses include:
- `LEAN_MIXTURE_CYL`
- `RICH_MIXTURE_CYL`
- `COOLING_DEGRADATION`
- `OIL_PRESSURE_LOSS`
- `TURBO_BOOST_DEFICIENCY`
- `BEARING_WEAR`
- `CYLINDER_MISFIRE`
- `SENSOR_FAULT`
- `MODEL_MISMATCH / OPERATING_REGIME_SHIFT`
- `UNKNOWN_ANOMALY`

---

## 3. Prognostics & Mission-Safe Horizon

### 3.1 Degradation Tracking
Degradation accumulates monotonically as a function of thermal, mechanical, and pressure stresses:
$$\Delta D_i = \left( r_{base} + \alpha_{thermal} \cdot S_{th} + \alpha_{lub} \cdot S_{lub} \right) \cdot \Delta t$$

### 3.2 Remaining Useful Life (RUL)
$$RUL_i = \frac{D_{fail} - D_{current}}{\max(\dot{D}_i \cdot S_{mission}, 10^{-6})}$$
Confidence intervals are derived from running variance:
$$RUL_{bounds} = RUL \pm z_{\alpha/2} \cdot \sigma_{extrap}$$

### 3.3 Mission-Safe Horizon
The system computes the earliest time any critical subsystem reaches its conservative operational threshold ($D = 0.80$) under projected mission profile stresses:
$$\text{Safe Horizon} = \min_{i} \left\{ \frac{0.80 - D_i}{\dot{D}_i \cdot S_{phase}} \right\}$$
