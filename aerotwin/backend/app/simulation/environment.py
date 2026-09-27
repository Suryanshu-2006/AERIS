"""
Flight Environment Model
Computes atmospheric conditions as a function of altitude and provides
mission-phase-aware operating conditions for the engine simulator.

Uses the International Standard Atmosphere (ISA) model for pressure/temperature.
"""
import numpy as np
from ..schemas.mission import MissionPhase


class FlightEnvironment:
    """
    Models the atmospheric environment and flight conditions.
    ISA model: T decreases ~6.5°C/km up to 11km tropopause, then isothermal.
    """

    # ISA constants
    SEA_LEVEL_TEMP_C = 15.0
    SEA_LEVEL_PRESSURE_INHG = 29.92
    LAPSE_RATE_C_PER_FT = 0.001981  # ~6.5°C per 1000m ≈ 1.981°C per 1000ft
    TROPOPAUSE_FT = 36089.0
    TROPOPAUSE_TEMP_C = -56.5

    def __init__(self):
        self.altitude_ft: float = 0.0
        self.ambient_temp_c: float = self.SEA_LEVEL_TEMP_C
        self.ambient_pressure_inhg: float = self.SEA_LEVEL_PRESSURE_INHG
        self.density_ratio: float = 1.0
        self.mission_phase: MissionPhase = MissionPhase.GROUND
        self.wind_speed_kts: float = 0.0
        self.isa_deviation_c: float = 0.0  # deviation from ISA (hot/cold day)

    def update(self, altitude_ft: float, isa_deviation_c: float = 0.0) -> None:
        """Update environment for given altitude."""
        self.altitude_ft = max(0.0, altitude_ft)
        self.isa_deviation_c = isa_deviation_c
        self.ambient_temp_c = self._compute_temperature(self.altitude_ft) + isa_deviation_c
        self.ambient_pressure_inhg = self._compute_pressure(self.altitude_ft)
        self.density_ratio = self._compute_density_ratio()

    def _compute_temperature(self, alt_ft: float) -> float:
        """ISA temperature at altitude."""
        if alt_ft <= self.TROPOPAUSE_FT:
            return self.SEA_LEVEL_TEMP_C - self.LAPSE_RATE_C_PER_FT * alt_ft
        return self.TROPOPAUSE_TEMP_C

    def _compute_pressure(self, alt_ft: float) -> float:
        """ISA pressure at altitude using barometric formula."""
        if alt_ft <= self.TROPOPAUSE_FT:
            # Troposphere: p = p0 * (T/T0)^(g/(L*R))
            temp_ratio = (self.SEA_LEVEL_TEMP_C + 273.15 - self.LAPSE_RATE_C_PER_FT * alt_ft) / (
                self.SEA_LEVEL_TEMP_C + 273.15
            )
            return self.SEA_LEVEL_PRESSURE_INHG * (temp_ratio ** 5.2559)
        else:
            # Stratosphere: isothermal, exponential decay
            tropo_pressure = self.SEA_LEVEL_PRESSURE_INHG * (
                (self.SEA_LEVEL_TEMP_C + 273.15 - self.LAPSE_RATE_C_PER_FT * self.TROPOPAUSE_FT)
                / (self.SEA_LEVEL_TEMP_C + 273.15)
            ) ** 5.2559
            delta_alt = alt_ft - self.TROPOPAUSE_FT
            return tropo_pressure * np.exp(-delta_alt / 20806.0)

    def _compute_density_ratio(self) -> float:
        """Air density ratio relative to sea level (sigma)."""
        temp_k = self.ambient_temp_c + 273.15
        sea_temp_k = self.SEA_LEVEL_TEMP_C + 273.15
        pressure_ratio = self.ambient_pressure_inhg / self.SEA_LEVEL_PRESSURE_INHG
        temp_ratio = sea_temp_k / temp_k
        return pressure_ratio * temp_ratio

    def get_phase_conditions(self, phase: MissionPhase) -> dict:
        """Return typical operating conditions for a mission phase."""
        conditions = {
            MissionPhase.GROUND:       {"throttle": 0.20, "altitude_ft": 0,     "load_factor": 0.3},
            MissionPhase.TAKEOFF:      {"throttle": 1.00, "altitude_ft": 500,   "load_factor": 1.0},
            MissionPhase.CLIMB:        {"throttle": 0.85, "altitude_ft": 10000, "load_factor": 0.85},
            MissionPhase.CRUISE:       {"throttle": 0.65, "altitude_ft": 20000, "load_factor": 0.65},
            MissionPhase.SURVEILLANCE: {"throttle": 0.60, "altitude_ft": 18000, "load_factor": 0.60},
            MissionPhase.LOITER:       {"throttle": 0.55, "altitude_ft": 15000, "load_factor": 0.55},
            MissionPhase.DESCENT:      {"throttle": 0.30, "altitude_ft": 5000,  "load_factor": 0.40},
            MissionPhase.LANDING:      {"throttle": 0.25, "altitude_ft": 200,   "load_factor": 0.50},
            MissionPhase.EMERGENCY:    {"throttle": 0.40, "altitude_ft": 5000,  "load_factor": 0.70},
        }
        return conditions.get(phase, conditions[MissionPhase.CRUISE])

    def to_dict(self) -> dict:
        return {
            "altitude_ft": self.altitude_ft,
            "ambient_temp_c": round(self.ambient_temp_c, 2),
            "ambient_pressure_inhg": round(self.ambient_pressure_inhg, 3),
            "density_ratio": round(self.density_ratio, 4),
            "mission_phase": self.mission_phase.value,
            "isa_deviation_c": self.isa_deviation_c,
        }
