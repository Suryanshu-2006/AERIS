"""
Sensor Model
Converts true engine physics values into noisy, biased sensor readings.
Sensor faults are applied HERE, separate from physical engine faults.
"""
import numpy as np
from typing import Optional
from ..schemas.telemetry import SensorReading, SensorFrame, SensorHealth
from ..schemas.engine import EngineState
from ..config import SensorConfig


class SensorFault:
    """Represents a fault applied to a specific sensor."""
    def __init__(self, fault_type: str, severity: float = 0.0,
                 start_time: float = 0.0, duration: float = float('inf')):
        self.fault_type = fault_type  # BIAS, STUCK, DRIFT, INTERMITTENT
        self.severity = severity
        self.start_time = start_time
        self.duration = duration
        self.stuck_value: Optional[float] = None
        self.drift_rate: float = 0.0
        self.drift_accumulated: float = 0.0
        self.intermittent_prob: float = 0.3

    def is_active(self, current_time: float) -> bool:
        return (current_time >= self.start_time and
                current_time < self.start_time + self.duration)


class SensorModel:
    """
    Simulates realistic sensor measurements from true engine state.
    
    Each sensor has:
    - Noise (Gaussian)
    - Bias (systematic offset)
    - Sampling rate
    - Health status
    - Uncertainty
    - Optional fault injection
    
    IMPORTANT: Sensor faults are separate from engine faults.
    A sensor fault corrupts the measurement, NOT the engine.
    """

    def __init__(self, config: Optional[SensorConfig] = None, num_cylinders: int = 4, seed: int = 42):
        if config is None:
            config = SensorConfig()
        self.config = config
        self.num_cylinders = num_cylinders
        self.rng = np.random.RandomState(seed)
        
        # Sensor definitions: name → (noise_std, unit, nominal_range)
        self.sensor_specs = {}
        for i in range(1, num_cylinders + 1):
            self.sensor_specs[f"EGT{i}"] = {"noise_std": config.egt_noise_std, "unit": "°C", "range": (300, 900)}
            self.sensor_specs[f"CHT{i}"] = {"noise_std": config.cht_noise_std, "unit": "°C", "range": (100, 280)}
        
        self.sensor_specs["OIL_PRESSURE"] = {"noise_std": config.oil_pressure_noise_std, "unit": "psi", "range": (0, 100)}
        self.sensor_specs["OIL_TEMP"] = {"noise_std": config.oil_temp_noise_std, "unit": "°C", "range": (40, 150)}
        self.sensor_specs["MAP"] = {"noise_std": config.map_noise_std, "unit": "inHg", "range": (5, 45)}
        self.sensor_specs["RPM"] = {"noise_std": config.rpm_noise_std, "unit": "RPM", "range": (0, 6200)}
        self.sensor_specs["VIBRATION"] = {"noise_std": config.vibration_noise_std, "unit": "g", "range": (0, 5)}
        self.sensor_specs["BUS_VOLTAGE"] = {"noise_std": config.voltage_noise_std, "unit": "V", "range": (18, 32)}
        self.sensor_specs["FUEL_FLOW"] = {"noise_std": config.fuel_flow_noise_std, "unit": "gal/hr", "range": (0, 20)}
        self.sensor_specs["TURBO_BOOST"] = {"noise_std": config.turbo_boost_noise_std, "unit": "psi", "range": (0, 12)}
        
        # Active sensor faults (sensor_name → SensorFault)
        self.faults: dict[str, SensorFault] = {}
        
        # Sensor degradation over time (sensor_name → degradation factor 0-1)
        self.degradation: dict[str, float] = {name: 0.0 for name in self.sensor_specs}

    def measure(self, engine_state: EngineState, timestamp: float) -> SensorFrame:
        """
        Convert true engine state to sensor readings with noise and faults.
        """
        # Extract true values from engine state
        true_values = self._extract_true_values(engine_state)
        
        sensors = {}
        for name, true_val in true_values.items():
            spec = self.sensor_specs.get(name, {"noise_std": 1.0, "unit": "", "range": (0, 100)})
            
            # Base noise
            noise = self.rng.normal(0, spec["noise_std"])
            
            # Degradation increases noise
            deg = self.degradation.get(name, 0.0)
            if deg > 0:
                noise *= (1.0 + deg * 3.0)
            
            measured = true_val + noise
            health = SensorHealth.HEALTHY
            confidence = 1.0 - deg * 0.3
            raw_value = measured
            
            # Apply sensor fault if active
            fault = self.faults.get(name)
            if fault and fault.is_active(timestamp):
                measured, health, confidence = self._apply_fault(
                    name, measured, true_val, fault, timestamp, spec
                )
            
            sensors[name] = SensorReading(
                name=name,
                value=round(measured, 3),
                unit=spec["unit"],
                timestamp=timestamp,
                noise_std=spec["noise_std"],
                health=health,
                confidence=round(confidence, 3),
                raw_value=round(raw_value, 3),
            )
        
        return SensorFrame(
            timestamp=timestamp,
            simulation_time=engine_state.timestamp,
            sensors=sensors,
        )

    def _extract_true_values(self, state: EngineState) -> dict[str, float]:
        """Extract true physical values from engine state."""
        values = {}
        for i, cyl in enumerate(state.cylinders):
            values[f"EGT{i + 1}"] = cyl.egt_c
            values[f"CHT{i + 1}"] = cyl.cht_c
        
        # Fill defaults if cylinders not populated
        for i in range(len(state.cylinders), self.num_cylinders):
            values[f"EGT{i + 1}"] = state.mean_egt_c
            values[f"CHT{i + 1}"] = state.mean_cht_c
        
        values["OIL_PRESSURE"] = state.oil_pressure_psi
        values["OIL_TEMP"] = state.oil_temperature_c
        values["MAP"] = state.manifold_pressure_inhg
        values["RPM"] = state.rpm
        values["VIBRATION"] = state.vibration_g
        values["BUS_VOLTAGE"] = state.bus_voltage
        values["FUEL_FLOW"] = state.fuel_flow_gph
        values["TURBO_BOOST"] = state.turbo_boost_psi
        return values

    def _apply_fault(self, name: str, measured: float, true_val: float,
                     fault: SensorFault, timestamp: float, spec: dict) -> tuple[float, SensorHealth, float]:
        """Apply sensor fault to measurement."""
        health = SensorHealth.FAULTY
        confidence = max(0.1, 1.0 - fault.severity)
        
        if fault.fault_type == "BIAS":
            # Constant offset proportional to severity and sensor range
            sensor_range = spec["range"][1] - spec["range"][0]
            bias = fault.severity * sensor_range * 0.15
            measured = true_val + bias
            if fault.severity < 0.3:
                health = SensorHealth.DEGRADED
            
        elif fault.fault_type == "STUCK":
            # Sensor frozen at a value
            if fault.stuck_value is None:
                fault.stuck_value = measured  # freeze at first faulty reading
            measured = fault.stuck_value
            
        elif fault.fault_type == "DRIFT":
            # Progressive drift over time
            elapsed = timestamp - fault.start_time
            sensor_range = spec["range"][1] - spec["range"][0]
            fault.drift_accumulated = fault.severity * elapsed * 0.01 * sensor_range * 0.001
            measured = true_val + fault.drift_accumulated
            if abs(fault.drift_accumulated) < sensor_range * 0.05:
                health = SensorHealth.DEGRADED
            
        elif fault.fault_type == "INTERMITTENT":
            # Random dropouts
            if self.rng.random() < fault.intermittent_prob * fault.severity:
                measured = 0.0  # dropout
                health = SensorHealth.FAULTY
                confidence = 0.1
            else:
                health = SensorHealth.DEGRADED
                confidence = 0.7
        
        return measured, health, confidence

    def inject_fault(self, sensor_name: str, fault_type: str, severity: float,
                     start_time: float = 0.0, duration: float = float('inf')):
        """Inject a fault into a specific sensor."""
        fault = SensorFault(
            fault_type=fault_type,
            severity=severity,
            start_time=start_time,
            duration=duration,
        )
        if fault_type == "DRIFT":
            fault.drift_rate = severity * 0.1
        self.faults[sensor_name] = fault

    def clear_fault(self, sensor_name: str):
        """Remove fault from a sensor."""
        self.faults.pop(sensor_name, None)

    def clear_all_faults(self):
        """Remove all sensor faults."""
        self.faults.clear()

    def set_degradation(self, sensor_name: str, level: float):
        """Set gradual degradation level for a sensor."""
        if sensor_name in self.degradation:
            self.degradation[sensor_name] = np.clip(level, 0.0, 1.0)

    def reset(self):
        self.faults.clear()
        self.degradation = {name: 0.0 for name in self.sensor_specs}
