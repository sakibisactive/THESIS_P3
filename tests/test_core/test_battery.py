import pytest

from src.core.battery import BatteryModel
from src.utils.config import BatteryConfig


@pytest.fixture
def sample_battery_config() -> BatteryConfig:
    return BatteryConfig(
        capacity_kwh=75.0,
        mass_kg=2000.0,
        efficiency=0.9,
        drag_coeff=0.25,
        frontal_area=2.2,
        rolling_res_coeff=0.01,
        regen_efficiency=0.7,
    )


def test_battery_initialization(sample_battery_config: BatteryConfig) -> None:
    model = BatteryModel(sample_battery_config)
    assert model.capacity_kwh == 75.0
    assert model.mass_kg == 2000.0
    assert model.efficiency == 0.9
    assert model.drag_coeff == 0.25
    assert model.frontal_area == 2.2
    assert model.rolling_res_coeff == 0.01
    assert model.regen_efficiency == 0.7


def test_calculate_consumption_zero_cases(sample_battery_config: BatteryConfig) -> None:
    model = BatteryModel(sample_battery_config)
    # Zero distance
    assert model.calculate_consumption(0.0, 10.0, 0.0, 0.0) == 0.0
    # Zero speed
    assert model.calculate_consumption(100.0, 0.0, 0.0, 0.0) == 0.0


def test_calculate_consumption_flat_constant_speed(
    sample_battery_config: BatteryConfig,
) -> None:
    model = BatteryModel(sample_battery_config)
    # At constant speed, acceleration = 0, slope = 0
    # Forces: F_drag + F_roll
    # F_drag = 0.5 * 1.225 * 0.25 * 2.2 * (20^2) = 134.75 N
    # F_roll = 2000 * 9.81 * 0.01 * cos(0) = 196.2 N
    # F_wheels = 330.95 N
    # P_wheels = 330.95 * 20 = 6619.0 Watts
    # P_elec = 6619.0 / 0.9 = 7354.4 Watts -> 7.354 kW
    # Time for 1000m at 20m/s: 50s -> 50 / 3600 hours = 0.0138 hours
    # Energy: 7.354 * 0.0138 = 0.102 kWh
    energy = model.calculate_consumption(
        distance_m=1000.0,
        speed_m_s=20.0,
        acceleration_m_s2=0.0,
        gradient_rad=0.0,
    )
    assert energy > 0.0
    assert pytest.approx(energy, rel=1e-2) == 0.10215


def test_calculate_consumption_incline(sample_battery_config: BatteryConfig) -> None:
    model = BatteryModel(sample_battery_config)
    # Moving uphill (slope = 0.1 rad, approx 5.7 degrees)
    # Extra force from gravity: F_grav = m * g * sin(theta)
    # Assert uphill consumes more energy than flat
    energy_flat = model.calculate_consumption(1000.0, 20.0, 0.0, 0.0)
    energy_uphill = model.calculate_consumption(1000.0, 20.0, 0.0, 0.1)
    assert energy_uphill > energy_flat


def test_calculate_consumption_regen(sample_battery_config: BatteryConfig) -> None:
    model = BatteryModel(sample_battery_config)
    # Moving steep downhill (gradient = -0.1 rad), constant speed
    # Gravity force acts as propulsion: F_grav = 2000 * 9.81 * sin(-0.1) = -1958.6 N
    # F_drag = 134.75 N, F_roll = 196.2 N
    # F_wheels = 134.75 + 196.2 - 1958.6 = -1627.65 N (regenerative)
    # Assert downhill returns negative consumption (energy generation)
    energy = model.calculate_consumption(1000.0, 20.0, 0.0, -0.1)
    assert energy < 0.0
