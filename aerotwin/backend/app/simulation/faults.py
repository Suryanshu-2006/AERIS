"""
Fault Injection System
Models physical engine faults and sensor faults with proper propagation.

CRITICAL DESIGN: Physical faults modify engine subsystem state, NOT sensor values directly.
Physical fault → engine subsystem → engine observable → sensor → detection

Sensor faults are handled separately in the SensorModel.
"""
import numpy as np
from typing import Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict


class FaultType(str, Enum):
    # Mechanical / Physical faults
    LEAN_MIXTURE = "LEAN_MIXTURE"
    RICH_MIXTURE = "RICH_MIXTURE"
    COOLING_DEGRADATION = "COOLING_DEGRADATION"
    OIL_PRESSURE_LOSS = "OIL_PRESSURE_LOSS"
    TURBO_BOOST_DEFICIENCY = "TURBO_BOOST_DEFICIENCY"
    CYLINDER_MISFIRE = "CYLINDER_MISFIRE"
    BEARING_WEAR = "BEARING_WEAR"
    
    # Sensor faults
    SENSOR_BIAS = "SENSOR_BIAS"
    SENSOR_STUCK = "SENSOR_STUCK"
    SENSOR_DRIFT = "SENSOR_DRIFT"
    SENSOR_INTERMITTENT = "SENSOR_INTERMITTENT"


class FaultDefinition(BaseModel):
    """Definition of a fault to inject."""
    fault_id: str
    fault_type: FaultType
    target: str  # e.g., "CYL3", "OIL_SYSTEM", "EGT3"
    severity: float = 0.5  # 0.0 -> healthy, 1.0 -> critical
    start_time: float = 0.0
    duration: float = float('inf')
    ramp_time: float = 0.0  # seconds over which severity ramps (0.0 = step fault)
    description: str = ""
    subsystem: str = ""
    is_sensor_fault: bool = False
    
    model_config = ConfigDict(use_enum_values=True)


class ActiveFault:
    """Runtime state of an active fault."""
    def __init__(self, definition: FaultDefinition):
        self.definition = definition
        self.active = False
        self.current_severity = 0.0
        self.ramp_rate = 0.0  # severity increase per second for progressive faults
        self.accumulated_damage = 0.0

    def is_active(self, current_time: float) -> bool:
        start = self.definition.start_time
        end = start + self.definition.duration
        self.active = start <= current_time < end
        return self.active

    def get_severity(self, current_time: float) -> float:
        if not self.is_active(current_time):
            return 0.0
        
        elapsed = current_time - self.definition.start_time
        ramp_time = getattr(self.definition, 'ramp_time', 0.0)
        
        if ramp_time > 0 and elapsed < ramp_time:
            ramp_factor = elapsed / ramp_time
        else:
            ramp_factor = 1.0
        
        self.current_severity = self.definition.severity * ramp_factor
        return self.current_severity


# ─────────────── PREDEFINED FAULT SCENARIOS ───────────────

PREDEFINED_FAULTS = {
    "LEAN_MIXTURE_CYL3": FaultDefinition(
        fault_id="LEAN_MIXTURE_CYL3",
        fault_type=FaultType.LEAN_MIXTURE,
        target="CYL3",
        severity=0.5,
        description="Lean mixture on cylinder 3 — possible fuel injector partial blockage",
        subsystem="COMBUSTION",
    ),
    "RICH_MIXTURE_CYL1": FaultDefinition(
        fault_id="RICH_MIXTURE_CYL1",
        fault_type=FaultType.RICH_MIXTURE,
        target="CYL1",
        severity=0.4,
        description="Rich mixture on cylinder 1 — fuel injector leaking",
        subsystem="COMBUSTION",
    ),
    "COOLING_DEGRADATION_CYL2": FaultDefinition(
        fault_id="COOLING_DEGRADATION_CYL2",
        fault_type=FaultType.COOLING_DEGRADATION,
        target="CYL2",
        severity=0.6,
        description="Cooling fin obstruction on cylinder 2",
        subsystem="COOLING",
    ),
    "OIL_PRESSURE_LOSS": FaultDefinition(
        fault_id="OIL_PRESSURE_LOSS",
        fault_type=FaultType.OIL_PRESSURE_LOSS,
        target="OIL_SYSTEM",
        severity=0.7,
        description="Oil pressure loss — pump wear or leak",
        subsystem="LUBRICATION",
    ),
    "TURBO_BOOST_DEFICIENCY": FaultDefinition(
        fault_id="TURBO_BOOST_DEFICIENCY",
        fault_type=FaultType.TURBO_BOOST_DEFICIENCY,
        target="TURBO",
        severity=0.5,
        description="Turbo boost deficiency — wastegate leak or bearing wear",
        subsystem="TURBO",
    ),
    "CYLINDER_MISFIRE": FaultDefinition(
        fault_id="CYLINDER_MISFIRE",
        fault_type=FaultType.CYLINDER_MISFIRE,
        target="CYL4",
        severity=0.6,
        description="Intermittent misfire on cylinder 4 — ignition issue",
        subsystem="COMBUSTION",
    ),
    "BEARING_WEAR": FaultDefinition(
        fault_id="BEARING_WEAR",
        fault_type=FaultType.BEARING_WEAR,
        target="CRANKSHAFT",
        severity=0.5,
        description="Main bearing wear — increased friction and vibration",
        subsystem="MECHANICAL",
    ),
    # Sensor faults
    "EGT3_BIAS": FaultDefinition(
        fault_id="EGT3_BIAS",
        fault_type=FaultType.SENSOR_BIAS,
        target="EGT3",
        severity=0.6,
        description="EGT3 sensor bias — thermocouple degradation",
        subsystem="SENSORS",
        is_sensor_fault=True,
    ),
    "EGT3_STUCK": FaultDefinition(
        fault_id="EGT3_STUCK",
        fault_type=FaultType.SENSOR_STUCK,
        target="EGT3",
        severity=0.8,
        description="EGT3 sensor stuck — frozen reading",
        subsystem="SENSORS",
        is_sensor_fault=True,
    ),
    "RPM_SENSOR_DRIFT": FaultDefinition(
        fault_id="RPM_SENSOR_DRIFT",
        fault_type=FaultType.SENSOR_DRIFT,
        target="RPM",
        severity=0.4,
        description="RPM sensor drift — magnetic pickup degradation",
        subsystem="SENSORS",
        is_sensor_fault=True,
    ),
    "OIL_PRESSURE_SENSOR_BIAS": FaultDefinition(
        fault_id="OIL_PRESSURE_SENSOR_BIAS",
        fault_type=FaultType.SENSOR_BIAS,
        target="OIL_PRESSURE",
        severity=0.5,
        description="Oil pressure sensor bias — transducer offset",
        subsystem="SENSORS",
        is_sensor_fault=True,
    ),
    "INTERMITTENT_SENSOR": FaultDefinition(
        fault_id="INTERMITTENT_SENSOR",
        fault_type=FaultType.SENSOR_INTERMITTENT,
        target="BUS_VOLTAGE",
        severity=0.5,
        description="Bus voltage sensor intermittent — connector issue",
        subsystem="SENSORS",
        is_sensor_fault=True,
    ),
}


class FaultInjector:
    """
    Manages fault injection into the engine and sensor models.
    
    Physical faults are applied to the ENGINE subsystem models.
    Sensor faults are applied to the SENSOR model.
    
    These are intentionally separate to ensure proper propagation.
    """

    def __init__(self):
        self.active_faults: dict[str, ActiveFault] = {}

    def inject(self, fault_def: FaultDefinition) -> None:
        """Inject a fault into the system."""
        self.active_faults[fault_def.fault_id] = ActiveFault(fault_def)

    def inject_by_id(self, fault_id: str, severity: Optional[float] = None,
                     start_time: float = 0.0, duration: float = float('inf')) -> Optional[FaultDefinition]:
        """Inject a predefined fault by ID."""
        if fault_id not in PREDEFINED_FAULTS:
            return None
        
        fault_def = PREDEFINED_FAULTS[fault_id].model_copy()
        if severity is not None:
            fault_def.severity = severity
        fault_def.start_time = start_time
        fault_def.duration = duration
        
        self.inject(fault_def)
        return fault_def

    def clear(self, fault_id: str) -> None:
        """Clear a specific fault."""
        self.active_faults.pop(fault_id, None)

    def clear_all(self) -> None:
        """Clear all faults."""
        self.active_faults.clear()

    def apply_to_engine(self, engine, current_time: float) -> list[str]:
        """
        Apply active PHYSICAL faults to engine subsystems.
        Returns list of applied fault descriptions.
        
        This ONLY modifies engine subsystem parameters.
        It does NOT touch sensor values.
        """
        applied = []
        
        for fault_id, af in self.active_faults.items():
            defn = af.definition
            if defn.is_sensor_fault:
                continue  # Sensor faults handled separately
            
            severity = af.get_severity(current_time)
            if severity <= 0:
                continue
            
            applied.append(f"{defn.fault_id}: severity={severity:.2f}")
            
            if defn.fault_type == FaultType.LEAN_MIXTURE.value:
                cyl_idx = self._parse_cylinder(defn.target)
                if cyl_idx is not None:
                    engine.combustion.set_mixture_offset(cyl_idx, -severity * 0.3)
            
            elif defn.fault_type == FaultType.RICH_MIXTURE.value:
                cyl_idx = self._parse_cylinder(defn.target)
                if cyl_idx is not None:
                    engine.combustion.set_mixture_offset(cyl_idx, severity * 0.25)
            
            elif defn.fault_type == FaultType.COOLING_DEGRADATION.value:
                cyl_idx = self._parse_cylinder(defn.target)
                if cyl_idx is not None:
                    engine.cooling.set_cooling_health(cyl_idx, 1.0 - severity * 0.7)
            
            elif defn.fault_type == FaultType.OIL_PRESSURE_LOSS.value:
                engine.lubrication.set_pump_efficiency(1.0 - severity * 0.6)
                engine.lubrication.set_leakage_rate(severity * 0.4)
            
            elif defn.fault_type == FaultType.TURBO_BOOST_DEFICIENCY.value:
                engine.turbo.set_health(1.0 - severity * 0.5)
                engine.turbo.set_shaft_efficiency(1.0 - severity * 0.3)
            
            elif defn.fault_type == FaultType.CYLINDER_MISFIRE.value:
                cyl_idx = self._parse_cylinder(defn.target)
                if cyl_idx is not None:
                    engine.combustion.set_cylinder_efficiency(cyl_idx, 1.0 - severity * 0.8)
                    engine.vibration_model.set_misfire_vibration(severity * 0.7)
            
            elif defn.fault_type == FaultType.BEARING_WEAR.value:
                engine.vibration_model.set_bearing_roughness(severity * 0.8)
                engine.lubrication.set_pump_efficiency(1.0 - severity * 0.2)  # bearing wear also affects pump
        
        return applied

    def apply_to_sensors(self, sensor_model, current_time: float) -> list[str]:
        """
        Apply active SENSOR faults to the sensor model.
        Returns list of applied sensor fault descriptions.
        """
        applied = []
        
        for fault_id, af in self.active_faults.items():
            defn = af.definition
            if not defn.is_sensor_fault:
                continue
            
            severity = af.get_severity(current_time)
            if severity <= 0:
                continue
            
            applied.append(f"{defn.fault_id}: severity={severity:.2f}")
            
            # Map fault type to sensor fault type string
            sensor_fault_type = {
                FaultType.SENSOR_BIAS.value: "BIAS",
                FaultType.SENSOR_STUCK.value: "STUCK",
                FaultType.SENSOR_DRIFT.value: "DRIFT",
                FaultType.SENSOR_INTERMITTENT.value: "INTERMITTENT",
            }.get(defn.fault_type, "BIAS")
            
            sensor_model.inject_fault(
                sensor_name=defn.target,
                fault_type=sensor_fault_type,
                severity=severity,
                start_time=defn.start_time,
                duration=defn.duration,
            )
        
        return applied

    def get_active_faults(self, current_time: float) -> list[dict]:
        """Get list of currently active faults."""
        result = []
        for fault_id, af in self.active_faults.items():
            if af.is_active(current_time):
                result.append({
                    "fault_id": af.definition.fault_id,
                    "fault_type": af.definition.fault_type,
                    "target": af.definition.target,
                    "severity": af.get_severity(current_time),
                    "subsystem": af.definition.subsystem,
                    "is_sensor_fault": af.definition.is_sensor_fault,
                    "description": af.definition.description,
                })
        return result

    @staticmethod
    def _parse_cylinder(target: str) -> Optional[int]:
        """Parse cylinder index from target string like 'CYL3' → 2 (0-indexed)."""
        target = target.upper()
        if target.startswith("CYL") and len(target) > 3:
            try:
                return int(target[3:]) - 1
            except ValueError:
                return None
        return None

    @staticmethod
    def list_available_faults() -> list[dict]:
        """List all predefined fault types."""
        return [
            {
                "fault_id": fid,
                "fault_type": f.fault_type,
                "target": f.target,
                "default_severity": f.severity,
                "subsystem": f.subsystem,
                "is_sensor_fault": f.is_sensor_fault,
                "description": f.description,
            }
            for fid, f in PREDEFINED_FAULTS.items()
        ]
