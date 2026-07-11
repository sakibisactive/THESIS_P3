"""Unit tests for the ScenarioExecutor simulation execution engine."""

import pytest
from src.core.network import Network, Node, Edge, ChargingStation
from src.core.vehicle import Vehicle, VehicleState
from src.core.battery import BatteryModel
from src.routing.dijkstra import DijkstraRouter
from src.routing.routing_context import RoutingContext
from src.utils.config import ScenarioConfig, SimulationConfig, BatteryConfig, CommunicationConfig, ChargingStationConfig, RoadClosureConfig
from src.evaluation.scenario_executor import ScenarioExecutor


@pytest.fixture
def test_network() -> Network:
    net = Network()
    # Grid:
    # (n1) --e1--> (n2) --e2--> (n3)
    #               |      ^
    #               |    e_alt
    #               |      |
    #              e3      |
    #               v      |
    #             (n4) (Charging Station)
    #               |
    #              e4
    #               v
    #             (n2)
    net.add_node(Node("n1", 0.0, 0.0))
    net.add_node(Node("n2", 100.0, 0.0))
    net.add_node(Node("n3", 200.0, 0.0))
    net.add_node(Node("n4", 100.0, 100.0))

    net.add_edge(Edge("e1", "n1", "n2", 100.0, 15.0))
    net.add_edge(Edge("e2", "n2", "n3", 100.0, 15.0))
    net.add_edge(Edge("e_alt", "n2", "n3", 150.0, 15.0))
    net.add_edge(Edge("e3", "n2", "n4", 100.0, 15.0))
    net.add_edge(Edge("e4", "n4", "n2", 100.0, 15.0))
    return net


@pytest.fixture
def base_scenario_config(tmp_path) -> ScenarioConfig:
    net_file = tmp_path / "test_net.json"
    net_file.write_text("{}", encoding="utf-8")  # empty dummy file

    sim_cfg = SimulationConfig(
        dt=1.0,
        max_steps=50,
        mode="standalone",
        network_file_path=str(net_file)
    )

    bat_cfg = BatteryConfig(
        capacity_kwh=10.0,  # small capacity to test charging quickly
        mass_kg=1500.0,
        efficiency=0.9,
        drag_coeff=0.25,
        frontal_area=2.2,
        rolling_res_coeff=0.01,
        regen_efficiency=0.7
    )

    comm_cfg = CommunicationConfig(
        v2v_range_m=300.0,
        v2i_range_m=500.0,
        base_packet_loss_rate=0.0,
        base_latency_s=0.002,
        latency_jitter_s=0.001
    )

    cs_cfg = ChargingStationConfig(
        id="cs1",
        node_id="n4",
        capacity=1,
        power_kw=50.0,
        base_price_per_kwh=0.35
    )

    return ScenarioConfig(
        name="test_executor_scenario",
        simulation=sim_cfg,
        battery=bat_cfg,
        communication=comm_cfg,
        charging_stations=[cs_cfg],
        emergencies=[],
        infrastructure_failures=[],
        ambulance_dispatches=[],
        road_closures=[]
    )


def test_executor_basic_run(test_network: Network, base_scenario_config: ScenarioConfig) -> None:
    """Verifies that vehicles spawn, find routes, travel, and successfully arrive."""
    router = DijkstraRouter()
    executor = ScenarioExecutor(
        scenario_config=base_scenario_config,
        router=router,
        reroute_threshold_soc=0.2,
        target_charge_soc=0.95
    )
    
    # Inject pre-built network to avoid config file reading
    executor.network = test_network
    
    # Re-initialize stations on the injected network
    cs_cfg = base_scenario_config.charging_stations[0]
    cs = ChargingStation(
        station_id=cs_cfg.id,
        node_id=cs_cfg.node_id,
        capacity=cs_cfg.capacity,
        power_kw=cs_cfg.power_kw,
        base_price_per_kwh=cs_cfg.base_price_per_kwh
    )
    executor.network.stations[cs.id] = cs

    # Spawn standard vehicle
    battery = BatteryModel(base_scenario_config.battery)
    vehicle = Vehicle("veh_test", "n1", "n3", 0.9, battery)
    executor.add_vehicle(vehicle)

    # Run
    metrics_collector = executor.execute()
    metrics = metrics_collector.metrics

    # Check vehicle arrived
    assert vehicle.state == VehicleState.ARRIVED
    assert "veh_test" in metrics.vehicle_travel_times
    assert metrics.vehicle_travel_times["veh_test"] > 0.0
    assert metrics.stranded_vehicle_count == 0


def test_executor_rerouting_on_closure(test_network: Network, base_scenario_config: ScenarioConfig) -> None:
    """Verifies that vehicles successfully reroute when road closures are encountered."""
    router = DijkstraRouter()
    
    # Set up dynamic closure of e2 at time = 2.0 (duration = 50.0)
    base_scenario_config.road_closures = [
        RoadClosureConfig(id="closure1", start_time=2.0, duration=50.0, edge_id="e2")
    ]
    
    executor = ScenarioExecutor(
        scenario_config=base_scenario_config,
        router=router,
        reroute_threshold_soc=0.1,
        target_charge_soc=0.95
    )
    
    executor.network = test_network
    
    # Spawn vehicle
    battery = BatteryModel(base_scenario_config.battery)
    vehicle = Vehicle("v_reroute", "n1", "n3", 0.9, battery)
    executor.add_vehicle(vehicle)

    # Run executor
    metrics_collector = executor.execute()
    metrics = metrics_collector.metrics

    # Check that rerouting was recorded and vehicle arrived via alternative route
    assert metrics.total_rerouting_events > 0
    assert metrics.vehicle_reroutes["v_reroute"] > 0
    assert vehicle.state == VehicleState.ARRIVED
    assert vehicle.current_route[-1] == "e_alt"


def test_executor_charging_redirection(test_network: Network, base_scenario_config: ScenarioConfig) -> None:
    """Tests EV low-battery charging redirection, queuing, charging, and resuming travel."""
    router = DijkstraRouter()
    
    # Increase max steps to allow charging to complete
    base_scenario_config.simulation.max_steps = 150

    # Reroute when SoC < 0.859 to trigger it immediately on our small network
    executor = ScenarioExecutor(
        scenario_config=base_scenario_config,
        router=router,
        reroute_threshold_soc=0.859,
        target_charge_soc=0.99
    )
    
    executor.network = test_network
    
    # Re-initialize stations on the injected network
    cs_cfg = base_scenario_config.charging_stations[0]
    cs = ChargingStation(
        station_id=cs_cfg.id,
        node_id=cs_cfg.node_id,
        capacity=cs_cfg.capacity,
        power_kw=cs_cfg.power_kw,
        base_price_per_kwh=cs_cfg.base_price_per_kwh
    )
    executor.network.stations[cs.id] = cs

    # Spawn vehicle with SoC close to threshold
    battery = BatteryModel(base_scenario_config.battery)
    vehicle = Vehicle("v_charge", "n1", "n3", 0.86, battery)
    executor.add_vehicle(vehicle)

    # Execute simulation
    metrics_collector = executor.execute()
    metrics = metrics_collector.metrics

    # The vehicle should successfully route to n3 after charging at n4.
    assert vehicle.state == VehicleState.ARRIVED
    assert metrics.total_charging_events > 0
    assert metrics.vehicle_charging_events["v_charge"] > 0
    assert vehicle.soc >= 0.99
