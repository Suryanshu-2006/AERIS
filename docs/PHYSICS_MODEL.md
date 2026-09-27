# AERIS Engine Physics Model

**Physics-Informed Demonstrator Model: Rotax 914 Class Aero Piston Engine**

> **Notice**: This model is a physics-informed engineering demonstrator for prototype simulation and validation. It is **NOT** an exact DRDO engine model or certified flight software.

---

## 1. International Standard Atmosphere (ISA)

Ambient conditions are calculated from geopotential altitude $h$ (ft):

### 1.1 Temperature
Below the tropopause ($h \le 36,089\text{ ft}$):
$$T(h) = T_0 - L \cdot h$$
where $T_0 = 15^\circ\text{C} = 288.15\text{ K}$, and $L \approx 1.981 \times 10^{-3}\ ^\circ\text{C/ft}$ ($6.5^\circ\text{C/km}$).

### 1.2 Pressure
$$P(h) = P_0 \cdot \left( \frac{T(h)}{T_0} \right)^{\frac{g}{L \cdot R}} = 29.92 \cdot \left( \frac{T(h)}{288.15} \right)^{5.2559} \text{ [inHg]}$$

---

## 2. Turbocharger & Airflow Model

The turbocharger maintains sea-level manifold pressure at high UAV altitudes.

### 2.1 Turbine Spool Dynamics
Exhaust energy driving the turbine:
$$E_{exh} = \left(\frac{\text{RPM}}{\text{RPM}_{max}}\right) \cdot \theta \cdot \eta_{turbo}$$
where $\theta$ is throttle ($0 \le \theta \le 1$), and $\eta_{turbo}$ is turbo health.

Spool-up lag is governed by a first-order lag with time constant $\tau_{spool} = 2.5\text{ s}$:
$$\frac{d\omega_{turbo}}{dt} = \frac{\omega_{target} - \omega_{turbo}}{\tau_{spool}}$$

### 2.2 Manifold Absolute Pressure (MAP)
$$\text{MAP} = \left[ P_{amb} + P_{boost} \cdot 2.036 \right] \cdot (0.30 + 0.70 \cdot \theta) \text{ [inHg]}$$

---

## 3. Combustion & Cylinder Thermodynamics

For a 4-cylinder, 4-stroke cycle with displacement $V_d = 1211\text{ cc}$:

### 3.1 Air Mass Flow
$$\dot{m}_{air} = \frac{\text{MAP}}{29.92} \cdot \left(\frac{V_d \cdot 10^{-6}}{2}\right) \cdot \left(\frac{\text{RPM}}{60}\right) \cdot \rho_{air} \cdot \eta_v$$
where $\eta_v \approx 0.85$ is volumetric efficiency.

### 3.2 Heat Release and Exhaust Gas Temperature (EGT)
Fuel flow $\dot{m}_f = \frac{\dot{m}_{air}}{\text{AFR}_{stoich}} \cdot \phi$.  
Heat released: $\dot{Q}_{comb} = \dot{m}_f \cdot \text{LHV} \cdot \eta_c$, where $\text{LHV} = 44\text{ MJ/kg}$.  
Exhaust gas temperature:
$$\text{EGT}_i = T_{amb} + 50 + \frac{0.60 \cdot \dot{Q}_{comb} \cdot (1 - \eta_{th})}{\dot{m}_{exh} \cdot C_{p,exh}} + \Delta T_{\phi}$$

### 3.3 Cylinder Head Temperature (CHT)
Heat transferred to the cylinder head ($\approx 30\%$ of rejected heat):
$$T_{head, target} = T_{amb} + \frac{\text{CHT}_{combustion} - T_{amb}}{\eta_{cooling, i}}$$
CHT dynamically approaches target with thermal inertia $\tau_{cool} = \frac{M_{th}}{h_{eff}}$:
$$\frac{d\text{CHT}_i}{dt} = \frac{T_{head, target} - \text{CHT}_i}{\tau_{cool}}$$

---

## 4. Lubrication & Friction Model

Oil pressure $P_{oil}$ is modeled as a balance between pump volumetric displacement and hydraulic flow resistance:
$$P_{oil} = \left[ P_{base} \cdot \left(\frac{\text{RPM}}{\text{RPM}_{idle}}\right)^{0.5} \cdot \eta_{pump} \cdot \nu(T_{oil}) \right] - \Delta P_{leak}$$

Oil temperature changes as friction work is absorbed:
$$\frac{dT_{oil}}{dt} = \frac{\dot{Q}_{friction} - \dot{Q}_{cooler}}{M_{oil} \cdot C_{p,oil}}$$

---

## 5. Vibration Spectral Model

Vibration amplitude ($g$) combines mechanical harmonics and bearing roughness:
$$g_{vib} = g_{base} \cdot \left(\frac{\text{RPM}}{\text{RPM}_{max}}\right)^2 + g_{bearing} + g_{misfire}$$
