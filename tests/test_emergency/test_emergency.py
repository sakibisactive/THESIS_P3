from typing import Any

import pytest

from src.communication.channel import CommunicationChannel
from src.core.battery import BatteryModel
from src.core.network import ChargingStation, Edge, Network, Node
from src.core.vehicle import Vehicle
from src.emergency.ambulance import Ambulance
from src.emergency.corridor import EmergencyCorridor
from src.emergency.failure import InfrastructureFailure
from src.emergency.incident import Incident
from src.emergency.scenario_loader import ScenarioLoader
from src.emergency.scheduler import (
    EventScheduler,
    SimulationEvent,
)
from src.utils.config import (
    AmbulanceDispatchConfig,
    BatteryConfig,
    CommunicationConfig,
    EmergencyEventConfig,
    InfrastructureFailureConfig,
    InfrastructureFailureType,
    ScenarioConfig,
    SimulationConfig,
)


@pytest.fixture
def test_network() -> Network:
    """Creates a basic road network for tests.

    Layout:
    n1 (0,0) ---- e1 (100m) ---- n2 (100,0) ---- e2 (100m) ---- n3 (200,0)
    """
    net = Network()
    n1 = Node("n1", 0.0, 0.0)
    n2 = Node("n2", 100.0, 0.0)
    n3 = Node("n3", 200.0, 0.0)
    net.add_node(n1)
    net.add_node(n2)
    net.add_node(n3)

    e1 = Edge("e1", "n1", "n2", 100.0, 20.0)
    e2 = Edge("e2", "n2", "n3", 100.0, 20.0)
    net.add_edge(e1)
    net.add_edge(e2)

    cs1 = ChargingStation(
        "cs1", "n2", capacity=1, power_kw=50.0, base_price_per_kwh=0.3
    )
    net.stations["cs1"] = cs1

    return net


@pytest.fixture
def test_channel() -> CommunicationChannel:
    config = CommunicationConfig(
        v2v_range_m=300.0,
        v2i_range_m=500.0,
        base_packet_loss_rate=0.0,
        base_latency_s=0.0,
        latency_jitter_s=0.0,
        blackout_start_time=None,
        blackout_end_time=None,
        blackout_area=None,
    )
    return CommunicationChannel(config, seed=42)


@pytest.fixture
def test_battery_config() -> BatteryConfig:
    return BatteryConfig(
        capacity_kwh=80.0,
        mass_kg=2000.0,
        efficiency=0.9,
        drag_coeff=0.3,
        frontal_area=2.2,
        rolling_res_coeff=0.015,
        regen_efficiency=0.7,
    )


def test_incident_propagation(test_network: Network) -> None:
    # Epicenter at n2 (100, 0)
    cfg = EmergencyEventConfig(
        id="inc1",
        epicenter_node_id="n2",
        start_time=10.0,
        duration=30.0,
        initial_radius_m=10.0,
        propagation_rate=2.0,
        intensity=0.8,
    )
    incident = Incident(cfg)

    assert incident.is_active(5.0) is False
    assert incident.is_active(15.0) is True
    assert incident.is_active(45.0) is False

    # Initialize epicenter position
    incident.initialize_epicenter_position(test_network)
    assert incident.epicenter_x == 100.0
    assert incident.epicenter_y == 0.0

    # At t = 10, radius is 10m
    # Edge e1 (0,0 -> 100,0) ends at n2, so part of it (from 90m to 100m) is within 10m.
    # Edge e2 (100,0 -> 200,0) starts at n2, so part of it (from 100m
    # to 110m) is within 10m.
    edges_t10 = incident.get_affected_edges(test_network, 10.0)
    assert "e1" in edges_t10
    assert "e2" in edges_t10

    # At t = 15, radius is 10 + 2 * (15 - 10) = 20m
    # Edge e1 is within 20m of n2.
    assert incident.get_radius(15.0) == 20.0


def test_ambulance_beacon_and_movement(
    test_network: Network,
    test_channel: CommunicationChannel,
    test_battery_config: BatteryConfig,
) -> None:
    battery = BatteryModel(test_battery_config)
    ambulance = Ambulance(
        vehicle_id="amb1",
        origin_node_id="n1",
        destination_node_id="n3",
        initial_soc=1.0,
        battery=battery,
        speed_m_s=25.0,
    )

    ambulance.assign_route(["e1", "e2"])
    test_channel.register_transceiver(ambulance.transceiver)

    # Calculate position at start
    x, y = ambulance.get_position(test_network)
    assert x == 0.0
    assert y == 0.0

    # Trigger beacon broadcast
    ambulance.step_beacon(current_time=1.0, channel=test_channel, network=test_network)
    assert len(test_channel.pending_deliveries) == 0  # No other transceiver registered

    # Move ambulance at free-flow speed
    # Edge limit is 20m/s. Ambulance speed target is 25m/s. So speed is capped at 20m/s.
    ambulance.step_movement_ambulance(dt=2.0, network=test_network)
    # Distance covered = 20 * 2.0 = 40m
    assert ambulance.distance_on_current_edge == 40.0
    x, y = ambulance.get_position(test_network)
    assert x == 40.0
    assert y == 0.0


def test_emergency_corridor_yielding(test_battery_config: BatteryConfig) -> None:
    battery = BatteryModel(test_battery_config)
    # Set up a standard vehicle on edge e1
    car = Vehicle("car1", "n1", "n3", 1.0, battery)
    car.assign_route(["e1", "e2"])
    car.distance_on_current_edge = 50.0

    # Set up ambulance on edge e1 behind the car
    ambulance = Ambulance(
        vehicle_id="amb1",
        origin_node_id="n1",
        destination_node_id="n3",
        initial_soc=1.0,
        battery=battery,
    )
    ambulance.assign_route(["e1", "e2"])
    ambulance.distance_on_current_edge = 30.0

    vehicles = {"car1": car, "amb1": ambulance}
    ambulances = {"amb1": ambulance}

    # Evaluate yield rules
    EmergencyCorridor.update_yield_states(vehicles, ambulances, yield_speed_m_s=3.0)
    assert car.is_yielding is True
    assert car.yield_speed_limit == 3.0

    # Move ambulance past the car
    ambulance.distance_on_current_edge = 60.0
    EmergencyCorridor.update_yield_states(vehicles, ambulances, yield_speed_m_s=3.0)
    # The car is now behind the ambulance, yielding should reset
    assert car.is_yielding is False


def test_infrastructure_failures(
    test_network: Network, test_channel: CommunicationChannel
) -> None:
    # 1. Road failure
    road_cfg = InfrastructureFailureConfig(
        id="f_road",
        failure_type=InfrastructureFailureType.ROAD_FAILURE,
        start_time=10.0,
        duration=20.0,
        target_id="e1",
    )
    failure = InfrastructureFailure(road_cfg)

    # Active timeframe check
    assert failure.is_within_timeframe(5.0) is False
    assert failure.is_within_timeframe(15.0) is True

    # Apply
    charging_stations = {"cs1": test_network.stations["cs1"]}
    failure.update(15.0, test_network, test_channel, charging_stations)
    edge_closed = bool(test_network.edges["e1"].is_closed)
    assert edge_closed is True
    assert test_network.edges["e1"].current_speed_limit == 0.0

    # Reverse
    failure.update(35.0, test_network, test_channel, charging_stations)
    edge_closed_after = bool(test_network.edges["e1"].is_closed)
    assert edge_closed_after is False
    assert test_network.edges["e1"].current_speed_limit == 20.0

    # 2. Charging station failure
    cs_cfg = InfrastructureFailureConfig(
        id="f_cs",
        failure_type=InfrastructureFailureType.CHARGING_STATION,
        start_time=5.0,
        duration=15.0,
        target_id="cs1",
    )
    failure_cs = InfrastructureFailure(cs_cfg)
    failure_cs.update(10.0, test_network, test_channel, charging_stations)
    assert test_network.stations["cs1"].is_operational is False
    assert test_network.stations["cs1"].get_estimated_wait_time() == float("inf")
    assert test_network.stations["cs1"].start_charging("v1") is False

    failure_cs.update(25.0, test_network, test_channel, charging_stations)
    assert test_network.stations["cs1"].is_operational is True


def test_event_scheduler_priority_and_expiration() -> None:
    scheduler = EventScheduler()

    class TestEvent(SimulationEvent):
        def __init__(
            self,
            event_id: str,
            t: float,
            p: int = 0,
            exp: float | None = None,
            callback: Any = None,
        ) -> None:
            super().__init__(event_id, t, p, exp)
            self.executed = False
            self.callback = callback

        def execute(self, manager: Any, context: Any) -> None:
            self.executed = True
            if self.callback:
                self.callback()

    executed_order = []

    e1 = TestEvent("e1", 10.0, p=1, callback=lambda: executed_order.append("e1"))
    e2 = TestEvent(
        "e2", 10.0, p=5, callback=lambda: executed_order.append("e2")
    )  # Higher priority, should run first
    e3 = TestEvent(
        "e3", 10.0, p=0, exp=12.0, callback=lambda: executed_order.append("e3")
    )  # Expired by t=15.0
    e4 = TestEvent("e4", 8.0)

    scheduler.schedule(e1)
    scheduler.schedule(e2)
    scheduler.schedule(e3)
    scheduler.schedule(e4)

    # Step at t = 9.0 -> e4 should trigger
    scheduler.step(9.0, None, None)
    assert e4.executed is True
    assert e1.executed is False

    # Step at t = 15.0 -> e3 should expire and not execute. e2 runs before e1.
    scheduler.step(15.0, None, None)
    assert executed_order == ["e2", "e1"]
    assert e3.executed is False


def test_scenario_loader_and_manager_integration(
    test_network: Network,
    test_channel: CommunicationChannel,
    test_battery_config: BatteryConfig,
) -> None:
    # Construct ScenarioConfig
    sim_cfg = SimulationConfig(
        dt=1.0,
        max_steps=100,
        mode="standalone",
        network_file_path="mock_network.json",
    )
    inc_cfg = EmergencyEventConfig(
        id="inc1",
        epicenter_node_id="n2",
        start_time=10.0,
        duration=20.0,
        initial_radius_m=10.0,
        propagation_rate=1.0,
        intensity=0.5,
    )
    fail_cfg = InfrastructureFailureConfig(
        id="fail1",
        failure_type=InfrastructureFailureType.ROAD_FAILURE,
        start_time=15.0,
        duration=10.0,
        target_id="e2",
    )
    amb_cfg = AmbulanceDispatchConfig(
        id="amb_vehicle",
        start_time=5.0,
        origin_node_id="n1",
        destination_node_id="n3",
        battery_capacity_kwh=100.0,
        initial_soc=1.0,
        v2v_range_m=300.0,
        v2i_range_m=500.0,
        speed_m_s=20.0,
        route=["e1", "e2"],
    )

    scenario_cfg = ScenarioConfig(
        name="Test Scenario",
        simulation=sim_cfg,
        battery=test_battery_config,
        emergencies=[inc_cfg],
        infrastructure_failures=[fail_cfg],
        ambulance_dispatches=[amb_cfg],
        road_closures=[],
    )

    # Load Scenario
    manager = ScenarioLoader.load_scenario(scenario_cfg)
    assert (
        len(manager.scheduler.events) == 3
    )  # SpawnIncident, ApplyFailure, DispatchAmbulance

    vehicles: dict[str, Vehicle] = {}
    charging_stations = {"cs1": test_network.stations["cs1"]}

    # Step simulation
    # At t=0, nothing is spawned yet
    manager.step(1.0, 0.0, test_network, test_channel, charging_stations, vehicles)
    assert len(manager.active_incidents) == 0
    assert len(manager.ambulances) == 0

    # Step to t=5.0 -> Ambulance should spawn
    manager.step(1.0, 5.0, test_network, test_channel, charging_stations, vehicles)
    assert "amb_vehicle" in manager.ambulances
    assert "amb_vehicle" in vehicles

    # Step to t=10.0 -> Incident should spawn
    manager.step(1.0, 10.0, test_network, test_channel, charging_stations, vehicles)
    assert "inc1" in manager.active_incidents

    # Step to t=15.0 -> Road failure should apply
    manager.step(1.0, 15.0, test_network, test_channel, charging_stations, vehicles)
    assert test_network.edges["e2"].is_closed is True
