import math

from src.utils.config import BatteryConfig


class BatteryModel:
    """Physics-based Electric Vehicle (EV) battery consumption model.

    Computes energy draw and regenerative braking based on physical forces
    (aerodynamic drag, rolling resistance, gravity, and inertial acceleration).
    """

    # Constants
    GRAVITY: float = 9.81  # m/s^2
    AIR_DENSITY: float = 1.225  # kg/m^3

    def __init__(self, config: BatteryConfig) -> None:
        """Initializes the battery model with physical vehicle parameters.

        Args:
            config: The validated BatteryConfig object.
        """
        self.capacity_kwh = config.capacity_kwh
        self.mass_kg = config.mass_kg
        self.efficiency = config.efficiency
        self.drag_coeff = config.drag_coeff
        self.frontal_area = config.frontal_area
        self.rolling_res_coeff = config.rolling_res_coeff
        self.regen_efficiency = config.regen_efficiency

    def calculate_consumption(
        self,
        distance_m: float,
        speed_m_s: float,
        acceleration_m_s2: float,
        gradient_rad: float,
    ) -> float:
        """Calculates energy consumption in kWh for a given travel segment.

        Uses force equations to estimate power requirements at the wheels,
        incorporating powertrain efficiency and regenerative braking.

        Args:
            distance_m: Travel segment distance in meters.
            speed_m_s: Current velocity of the vehicle in meters/second.
            acceleration_m_s2: Current acceleration in meters/second^2.
            gradient_rad: Road incline angle in radians.

        Returns:
            float: Energy consumed (positive) or generated (negative) in kWh.
        """
        if distance_m <= 0.0 or speed_m_s <= 0.0:
            return 0.0

        # 1. Aerodynamic Drag Force: F_drag = 0.5 * rho * Cd * A * v^2
        f_drag = (
            0.5
            * self.AIR_DENSITY
            * self.drag_coeff
            * self.frontal_area
            * (speed_m_s**2)
        )

        # 2. Rolling Resistance Force: F_roll = m * g * Cr * cos(theta)
        f_roll = (
            self.mass_kg
            * self.GRAVITY
            * self.rolling_res_coeff
            * math.cos(gradient_rad)
        )

        # 3. Gravity Force: F_grav = m * g * sin(theta)
        f_grav = self.mass_kg * self.GRAVITY * math.sin(gradient_rad)

        # 4. Inertial Acceleration Force: F_accel = m * a
        f_accel = self.mass_kg * acceleration_m_s2

        # Total force at the wheels
        f_wheels = f_drag + f_roll + f_grav + f_accel

        # Mechanical Power at wheels (Watts): P = F * v
        p_wheels = f_wheels * speed_m_s

        # Powertrain Power: Apply powertrain or regeneration efficiencies
        if p_wheels >= 0.0:
            p_electrical = p_wheels / self.efficiency
        else:
            p_electrical = p_wheels * self.regen_efficiency

        # Convert Watts to Kilowatts
        p_kw = p_electrical / 1000.0

        # Duration of traversal in hours: t = d / v
        duration_hours = (distance_m / speed_m_s) / 3600.0

        # Energy consumed in kWh: E = P * t
        return p_kw * duration_hours
