import pytest

from src.core.battery import BatteryModel
from src.core.network import Edge, Network, Node
from src.core.vehicle import Vehicle, VehicleState
from src.utils.config import BatteryConfig


@pytest.fixture
def sample_battery() -> BatteryModel:
    config = BatteryConfig(
        capacity_kwh=50.0,
        mass_kg=1500.0,
        efficiency=0.9,
        drag_coeff=0.25,
        frontal_area=2.0,
        rolling_res_coeff=0.01,
        regen_efficiency=0.7,
    )
    return BatteryModel(config)


@pytest.fixture
def sample_network() -> Network:
    network = Network()
    network.add_node(Node("n1", 0.0, 0.0))
    network.add_node(Node("n2", 100.0, 0.0))
    network.add_node(Node("n3", 200.0, 0.0))

    network.add_edge(Edge("e1", "n1", "n2", 100.0, 15.0))
    network.add_edge(Edge("e2", "n2", "n3", 100.0, 15.0))
    return network


def test_vehicle_initialization(sample_battery: BatteryModel) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 0.8, sample_battery)
    assert vehicle.id == "v1"
    assert vehicle.origin_node_id == "n1"
    assert vehicle.destination_node_id == "n3"
    assert vehicle.soc == 0.8
    assert vehicle.state == VehicleState.EN_ROUTE
    assert vehicle.accumulated_travel_time == 0.0
    assert vehicle.accumulated_energy_consumed == 0.0


def test_vehicle_invalid_soc(sample_battery: BatteryModel) -> None:
    with pytest.raises(ValueError, match="Initial SoC must be between"):
        Vehicle("v1", "n1", "n3", 1.5, sample_battery)

    with pytest.raises(ValueError, match="Initial SoC must be between"):
        Vehicle("v1", "n1", "n3", -0.1, sample_battery)


def test_assign_route(sample_battery: BatteryModel) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 0.8, sample_battery)
    route = ["e1", "e2"]
    vehicle.assign_route(route)
    assert vehicle.current_route == route
    assert vehicle.current_edge_idx == 0
    assert vehicle.distance_on_current_edge == 0.0


def test_step_movement_within_edge(
    sample_battery: BatteryModel, sample_network: Network
) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 1.0, sample_battery)
    vehicle.assign_route(["e1", "e2"])

    # Move at 10 m/s for 5 seconds (total 50m, less than e1's length of 100m)
    vehicle.step_movement(5.0, 10.0, 0.0, sample_network)

    assert vehicle.current_edge_idx == 0
    assert vehicle.distance_on_current_edge == 50.0
    assert vehicle.state == VehicleState.EN_ROUTE
    assert vehicle.accumulated_travel_time == 5.0
    assert vehicle.soc < 1.0


def test_step_movement_boundary_transition(
    sample_battery: BatteryModel, sample_network: Network
) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 1.0, sample_battery)
    vehicle.assign_route(["e1", "e2"])

    # Move at 10 m/s for 15 seconds.
    # First 10 seconds: travels 100m to end of e1.
    # Remaining 5 seconds: travels 50m on e2.
    vehicle.step_movement(15.0, 10.0, 0.0, sample_network)

    assert vehicle.current_edge_idx == 1
    assert vehicle.distance_on_current_edge == 50.0
    assert vehicle.state == VehicleState.EN_ROUTE
    assert vehicle.accumulated_travel_time == 15.0


def test_step_movement_arrival(
    sample_battery: BatteryModel, sample_network: Network
) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 1.0, sample_battery)
    vehicle.assign_route(["e1", "e2"])

    # Travel 250m at 10 m/s (takes 25 seconds). Total route is 200m.
    vehicle.step_movement(25.0, 10.0, 0.0, sample_network)

    assert vehicle.state == VehicleState.ARRIVED
    # Time spent should be limited to reaching the destination: 200m / 10m/s = 20s
    assert vehicle.accumulated_travel_time == 20.0
    assert vehicle.distance_on_current_edge == 100.0  # End of e2


def test_step_movement_stranded(
    sample_battery: BatteryModel, sample_network: Network
) -> None:
    # Very low starting SoC (0.00005) so it runs out of battery during movement
    vehicle = Vehicle("v1", "n1", "n3", 0.00005, sample_battery)
    vehicle.assign_route(["e1"])

    # Run for 10 seconds at 10 m/s. This should deplete the tiny charge.
    vehicle.step_movement(10.0, 10.0, 0.0, sample_network)

    assert vehicle.state == VehicleState.STRANDED
    assert vehicle.soc == 0.0


def test_step_charging(sample_battery: BatteryModel) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 0.2, sample_battery)
    vehicle.state = VehicleState.CHARGING

    # Charge at 50 kW for 360 seconds (0.1 hours).
    # Energy added: 50 * 0.1 = 5 kWh.
    # SoC increase: 5 / 50 (capacity) = 0.1 -> total SoC = 0.3
    vehicle.step_charging(360.0, 50.0)

    assert pytest.approx(vehicle.soc, rel=1e-3) == 0.3
    assert vehicle.accumulated_charge_time == 360.0


def test_step_waiting(sample_battery: BatteryModel) -> None:
    vehicle = Vehicle("v1", "n1", "n3", 0.2, sample_battery)
    vehicle.state = VehicleState.WAITING_IN_QUEUE

    vehicle.step_waiting(10.0)
    assert vehicle.accumulated_queue_time == 10.0
