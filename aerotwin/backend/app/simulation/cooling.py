"""
Cooling System Model
Models air-cooled cylinder head heat transfer for the aero piston engine.
Cooling effectiveness depends on airspeed (altitude/flight mode), ambient temp, and cylinder health.
"""
import numpy as np


class CoolingModel:
    """
    Simplified air-cooling model for cylinder heads.
    Heat rejection depends on:
    - Temperature differential (CHT - ambient)
    - Airflow over cylinder fins (function of airspeed / RPM-driven fan)
    - Cooling system health (degradation)
    """

    def __init__(self, num_cylinders: int = 4):
        self.num_cylinders = num_cylinders
        # Thermal mass per cylinder (simplified: J/°C)
        self.thermal_mass = 2500.0  # approx 2.5 kJ/°C
        # Heat transfer coefficient (W/°C) at nominal airflow
        self.base_htc = 150.0
        # Per-cylinder cooling degradation (1.0 = healthy)
        self.cooling_health = np.ones(num_cylinders)
        # Current CHT values
        self.cht_values = np.full(num_cylinders, 120.0)
        # Max CHT redline
        self.cht_redline = 260.0  # °C

    def update(self, dt: float, cyl_heat_inputs: list[float],
               ambient_temp_c: float, airspeed_factor: float = 1.0) -> list[float]:
        """
        Update CHT values for all cylinders.
        
        Args:
            dt: time step in seconds
            cyl_heat_inputs: heat input to each cylinder (°C equivalent from combustion)
            ambient_temp_c: ambient temperature
            airspeed_factor: 0-1.5, proportional to cooling airflow
        
        Returns:
            Updated CHT values
        """
        for i in range(self.num_cylinders):
            # Heat input from combustion
            q_in = cyl_heat_inputs[i] if i < len(cyl_heat_inputs) else 0.0
            
            # Effective heat transfer coefficient
            htc = self.base_htc * airspeed_factor * self.cooling_health[i]
            htc = max(htc, 10.0)  # minimum natural convection
            
            # Heat rejection rate
            delta_t = self.cht_values[i] - ambient_temp_c
            q_out = htc * delta_t  # W
            
            # Target CHT is higher when cooling health is degraded
            target_cht = ambient_temp_c + (q_in - ambient_temp_c) / max(self.cooling_health[i], 0.1)
            
            # Thermal lag: exponential approach to target
            tau = self.thermal_mass / htc  # thermal time constant (seconds)
            tau = max(tau, 1.0)
            alpha = 1.0 - np.exp(-dt / tau)
            
            self.cht_values[i] += alpha * (target_cht - self.cht_values[i])
        
        return self.cht_values.tolist()

    def set_cooling_health(self, cylinder_id: int, health: float):
        """Degrade cooling for a specific cylinder (0.1 = severely degraded)."""
        if 0 <= cylinder_id < self.num_cylinders:
            self.cooling_health[cylinder_id] = np.clip(health, 0.1, 1.5)

    def get_thermal_margins(self) -> list[float]:
        """Get margin to redline for each cylinder."""
        return [self.cht_redline - cht for cht in self.cht_values]

    def reset(self):
        self.cooling_health = np.ones(self.num_cylinders)
        self.cht_values = np.full(self.num_cylinders, 120.0)
