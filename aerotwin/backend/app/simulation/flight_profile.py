"""
Flight Profile Model
Defines mission profiles as sequences of phases with altitude, throttle, and duration.
Interpolates between phases for smooth transitions.
"""
from typing import Optional
from ..schemas.mission import MissionPhase, MissionPhaseConfig, MissionProfile


def create_default_mission() -> MissionProfile:
    """Create a standard MALE UAV surveillance mission."""
    phases = [
        MissionPhaseConfig(
            phase=MissionPhase.TAKEOFF,
            duration_minutes=5,
            altitude_ft=1000,
            throttle_percent=95,
            description="Full-power takeoff"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.CLIMB,
            duration_minutes=20,
            altitude_ft=20000,
            throttle_percent=85,
            description="Climb to cruise altitude"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.CRUISE,
            duration_minutes=120,
            altitude_ft=20000,
            throttle_percent=65,
            description="Transit cruise to AO"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.SURVEILLANCE,
            duration_minutes=60,
            altitude_ft=18000,
            throttle_percent=60,
            description="Surveillance over area of operation"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.LOITER,
            duration_minutes=60,
            altitude_ft=15000,
            throttle_percent=55,
            description="Loiter / orbit"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.CRUISE,
            duration_minutes=90,
            altitude_ft=20000,
            throttle_percent=65,
            description="Return cruise"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.DESCENT,
            duration_minutes=15,
            altitude_ft=3000,
            throttle_percent=30,
            description="Descent"
        ),
        MissionPhaseConfig(
            phase=MissionPhase.LANDING,
            duration_minutes=5,
            altitude_ft=0,
            throttle_percent=25,
            description="Approach and landing"
        ),
    ]
    profile = MissionProfile(
        mission_id="DEFAULT_MISSION_01",
        mission_name="Standard MALE Surveillance",
        phases=phases,
        max_altitude_ft=20000,
        payload_kg=50,
        ambient_temperature_c=15.0,
        cruise_duration_minutes=210,
        loiter_duration_minutes=60,
        description="Standard surveillance mission with cruise-loiter-cruise profile"
    )
    profile.compute_total_duration()
    return profile


class FlightProfileInterpolator:
    """
    Interpolates mission profile parameters over continuous simulation time.
    Provides smooth transitions between phases rather than step changes.
    """

    def __init__(self, profile: MissionProfile):
        self.profile = profile
        self._build_timeline()

    def _build_timeline(self):
        """Build cumulative timeline from phases."""
        self.timeline = []
        t = 0.0
        for phase_cfg in self.profile.phases:
            start = t
            end = t + phase_cfg.duration_minutes * 60.0  # seconds
            self.timeline.append({
                "phase": phase_cfg.phase,
                "start_s": start,
                "end_s": end,
                "duration_s": phase_cfg.duration_minutes * 60.0,
                "altitude_ft": phase_cfg.altitude_ft,
                "throttle": phase_cfg.throttle_percent / 100.0,
                "description": phase_cfg.description,
            })
            t = end
        self.total_duration_s = t

    def get_conditions(self, time_s: float) -> dict:
        """Get interpolated flight conditions at a given simulation time."""
        if time_s <= 0:
            first = self.timeline[0]
            return {
                "phase": first["phase"],
                "altitude_ft": 0.0,
                "throttle": first["throttle"] * 0.3,
                "progress": 0.0,
            }

        if time_s >= self.total_duration_s:
            last = self.timeline[-1]
            return {
                "phase": last["phase"],
                "altitude_ft": last["altitude_ft"],
                "throttle": last["throttle"],
                "progress": 1.0,
            }

        # Find current phase
        for i, seg in enumerate(self.timeline):
            if seg["start_s"] <= time_s < seg["end_s"]:
                phase_progress = (time_s - seg["start_s"]) / seg["duration_s"]

                # Interpolate altitude from previous phase
                if i > 0:
                    prev_alt = self.timeline[i - 1]["altitude_ft"]
                else:
                    prev_alt = 0.0
                
                target_alt = seg["altitude_ft"]
                # Smooth altitude transition
                alt = prev_alt + (target_alt - prev_alt) * self._smooth_step(phase_progress)

                # Smooth throttle transition
                if i > 0:
                    prev_throttle = self.timeline[i - 1]["throttle"]
                else:
                    prev_throttle = 0.2
                target_throttle = seg["throttle"]
                throttle = prev_throttle + (target_throttle - prev_throttle) * self._smooth_step(
                    min(phase_progress * 3, 1.0)  # faster throttle transition
                )

                return {
                    "phase": seg["phase"],
                    "altitude_ft": alt,
                    "throttle": throttle,
                    "progress": time_s / self.total_duration_s,
                }

        # Fallback
        return {
            "phase": MissionPhase.CRUISE,
            "altitude_ft": 20000.0,
            "throttle": 0.65,
            "progress": 0.5,
        }

    @staticmethod
    def _smooth_step(t: float) -> float:
        """Hermite smooth step for transitions."""
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    def get_total_duration_s(self) -> float:
        return self.total_duration_s
