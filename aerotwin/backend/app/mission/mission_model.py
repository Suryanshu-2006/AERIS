"""
Mission Model
Creates and manages mission profiles as sequences of phases.
Computes mission stress factors for each phase.
"""
import uuid
from ..schemas.mission import MissionProfile, MissionPhaseConfig, MissionPhase
from ..simulation.flight_profile import create_default_mission


class MissionModel:
    """
    Manages mission profiles and computes per-phase stress factors.
    """

    def __init__(self):
        self.current_mission: MissionProfile = create_default_mission()
        self.missions: dict[str, MissionProfile] = {
            self.current_mission.mission_id: self.current_mission
        }

    def create_mission(self, name: str, phases: list[dict],
                       payload_kg: float = 50.0,
                       ambient_temp_c: float = 15.0) -> MissionProfile:
        """Create a new mission profile from phase definitions."""
        phase_configs = []
        for p in phases:
            phase_configs.append(MissionPhaseConfig(
                phase=MissionPhase(p.get("phase", "CRUISE")),
                duration_minutes=p.get("duration_minutes", 30),
                altitude_ft=p.get("altitude_ft", 20000),
                throttle_percent=p.get("throttle_percent", 65),
                description=p.get("description", ""),
            ))
        
        mission = MissionProfile(
            mission_id=f"MISSION_{uuid.uuid4().hex[:8].upper()}",
            mission_name=name,
            phases=phase_configs,
            payload_kg=payload_kg,
            ambient_temperature_c=ambient_temp_c,
        )
        mission.compute_total_duration()
        mission.max_altitude_ft = max(p.altitude_ft for p in phase_configs) if phase_configs else 20000
        mission.cruise_duration_minutes = sum(
            p.duration_minutes for p in phase_configs if p.phase == MissionPhase.CRUISE
        )
        mission.loiter_duration_minutes = sum(
            p.duration_minutes for p in phase_configs if p.phase == MissionPhase.LOITER
        )
        
        self.missions[mission.mission_id] = mission
        return mission

    def set_current_mission(self, mission_id: str) -> bool:
        if mission_id in self.missions:
            self.current_mission = self.missions[mission_id]
            return True
        return False

    def get_phase_stress_factor(self, phase: MissionPhase, altitude_ft: float,
                                 throttle: float, ambient_temp_c: float) -> float:
        """
        Compute stress factor for a mission phase.
        Higher stress = faster degradation.
        """
        # Altitude stress: higher = more thermal cycling, less cooling
        alt_stress = 1.0 + 0.5 * min(altitude_ft / 30000.0, 1.0)
        
        # Throttle stress: higher = more thermal load
        throttle_stress = 0.5 + 1.5 * throttle
        
        # Temperature stress: hotter ambient = harder to cool
        temp_stress = 1.0 + max(0, (ambient_temp_c - 15) / 30.0)
        
        # Phase-specific factors
        phase_factors = {
            MissionPhase.TAKEOFF: 2.0,
            MissionPhase.CLIMB: 1.5,
            MissionPhase.CRUISE: 1.0,
            MissionPhase.SURVEILLANCE: 0.9,
            MissionPhase.LOITER: 0.8,
            MissionPhase.DESCENT: 0.6,
            MissionPhase.LANDING: 1.2,
            MissionPhase.GROUND: 0.3,
            MissionPhase.EMERGENCY: 2.5,
        }
        
        phase_mult = phase_factors.get(phase, 1.0)
        
        return alt_stress * throttle_stress * temp_stress * phase_mult

    def get_mission_summary(self, mission_id: str = None) -> dict:
        mission = self.missions.get(mission_id) if mission_id else self.current_mission
        if not mission:
            return {}
        return {
            "mission_id": mission.mission_id,
            "mission_name": mission.mission_name,
            "total_duration_hours": mission.total_duration_hours,
            "max_altitude_ft": mission.max_altitude_ft,
            "payload_kg": mission.payload_kg,
            "phases": [
                {
                    "phase": p.phase.value,
                    "duration_minutes": p.duration_minutes,
                    "altitude_ft": p.altitude_ft,
                    "throttle_percent": p.throttle_percent,
                }
                for p in mission.phases
            ],
        }
