"""Tests for the E3-Hybrid Cooperative Swarm Router."""

import pytest

from src.core.network import Edge, Network, Node
from src.core.battery import BatteryModel
from src.core.vehicle import Vehicle
from src.routing.e3_hybrid import E3HybridRouter
from src.routing.routing_context import RoutingContext, fastest_time_cost
from src.utils.config import AlgorithmConfig, E3HybridConfig, BatteryConfig


@pytest.fixture
def simple_network() -> Network:
    """A small network with multiple paths from A to D.
    
    A -> B -> D (cost 10 + 10 = 20)
    A -> C -> D (cost 15 + 15 = 30)
    """
    net = Network()
    net.add_node(Node("A", 0.0, 0.0))
    net.add_node(Node("B", 1.0, 1.0))
    net.add_node(Node("C", 1.0, -1.0))
    net.add_node(Node("D", 2.0, 0.0))
    
    net.add_edge(Edge("A-B", "A", "B", length=1000, speed_limit=100))  # 10s
    net.add_edge(Edge("B-D", "B", "D", length=1000, speed_limit=100))  # 10s
    net.add_edge(Edge("A-C", "A", "C", length=1500, speed_limit=100))  # 15s
    net.add_edge(Edge("C-D", "C", "D", length=1500, speed_limit=100))  # 15s
    
    return net


@pytest.fixture
def context(simple_network: Network) -> RoutingContext:
    battery_config = BatteryConfig(capacity_kwh=50.0, mass_kg=1500.0)
    battery = BatteryModel(battery_config)
    veh = Vehicle(
        vehicle_id="test_ev",
        origin_node_id="A",
        destination_node_id="D",
        initial_soc=1.0,
        battery=battery
    )
    return RoutingContext(
        network=simple_network,
        vehicle=veh,
        current_time=0.0,
        cost_function=fastest_time_cost,
    )


@pytest.fixture
def base_config() -> AlgorithmConfig:
    config = AlgorithmConfig()
    config.aco.num_ants = 2
    config.bco.colony_size = 2
    config.pso.swarm_size = 2
    config.e3_hybrid.max_iterations = 2
    return config


def test_e3_hybrid_finds_valid_optimal_path(context: RoutingContext, base_config: AlgorithmConfig):
    router = E3HybridRouter(base_config, seed=42)
    result = router.find_route("A", "D", context)
    
    assert result.path_nodes == ["A", "B", "D"]
    assert result.path_edges == ["A-B", "B-D"]
    assert result.total_cost == pytest.approx(20.0)


def test_ablation_toggles_can_be_disabled(context: RoutingContext, base_config: AlgorithmConfig):
    base_config.e3_hybrid.share_aco_to_pso = False
    base_config.e3_hybrid.share_gbest_to_pso = False
    base_config.e3_hybrid.share_gbest_to_bco = False
    base_config.e3_hybrid.share_bco_pso_to_aco = False
    
    router = E3HybridRouter(base_config, seed=42)
    result = router.find_route("A", "D", context)
    
    assert result.path_nodes == ["A", "B", "D"]


def test_deterministic_execution_with_same_seed(context: RoutingContext, base_config: AlgorithmConfig):
    r1 = E3HybridRouter(base_config, seed=12345)
    res1 = r1.find_route("A", "D", context)
    
    r2 = E3HybridRouter(base_config, seed=12345)
    res2 = r2.find_route("A", "D", context)
    
    assert res1.path_nodes == res2.path_nodes
    assert res1.total_cost == res2.total_cost
    assert r1.gbest_source == r2.gbest_source


def test_dynamic_adaptation_routes_around_closures(context: RoutingContext, base_config: AlgorithmConfig):
    router = E3HybridRouter(base_config, seed=42)
    
    # First query finds A-B-D
    res1 = router.find_route("A", "D", context)
    assert res1.path_edges == ["A-B", "B-D"]
    
    # Close A-B
    context.network.edges["A-B"].is_closed = True
    router.update_network("A-B")
    
    # Second query must find A-C-D
    res2 = router.find_route("A", "D", context)
    assert res2.path_edges == ["A-C", "C-D"]
    assert res2.total_cost == pytest.approx(30.0)


def test_metrics_collection(context: RoutingContext, base_config: AlgorithmConfig):
    base_config.e3_hybrid.collect_metrics = True
    base_config.e3_hybrid.max_iterations = 3
    router = E3HybridRouter(base_config, seed=42)
    
    router.find_route("A", "D", context)
    
    assert len(router.metrics_history) == 1
    m = router.metrics_history[0]
    
    assert m.num_iterations_run == 3
    assert m.best_cost_found == pytest.approx(20.0)
    assert m.gbest_source in ["ACO", "BCO", "PSO"]
    assert len(m.iteration_records) == 3
    
    iter0 = m.iteration_records[0]
    assert iter0.iteration == 0
    assert iter0.global_best_cost >= 20.0
    # The sum of valid routes should equal the sum of active agents
    total_agents = base_config.aco.num_ants + base_config.bco.colony_size + base_config.pso.swarm_size
    assert iter0.aco_valid_routes + iter0.bco_valid_routes + iter0.pso_valid_routes <= total_agents
    assert iter0.aco_contribution + iter0.bco_contribution + iter0.pso_contribution == pytest.approx(1.0)


def test_subsystems_statistics(context: RoutingContext, base_config: AlgorithmConfig):
    router = E3HybridRouter(base_config, seed=42)
    router.find_route("A", "D", context)
    
    stats = router.get_statistics()
    assert stats["algorithm"] == "E3-Hybrid"
    assert stats["search_count"] == 1
    assert "subsystems" in stats
    assert "aco" in stats["subsystems"]
    assert "bco" in stats["subsystems"]
    assert "pso" in stats["subsystems"]
    
    # The sub-engines should not have recorded monolithic search_count because they 
    # were orchestrated via execute_iteration, not find_route.
    assert stats["subsystems"]["aco"]["search_count"] == 0


def test_e3_hybrid_ablation(context: RoutingContext, base_config: AlgorithmConfig):
    # Disable ACO and PSO, only keep BCO
    base_config.e3_hybrid.disable_aco = True
    base_config.e3_hybrid.disable_pso = True
    base_config.e3_hybrid.disable_bco = False
    
    router = E3HybridRouter(base_config, seed=42)
    result = router.find_route("A", "D", context)
    
    # It should still find a valid route using only BCO
    assert result.path_nodes == ["A", "B", "D"]
    assert router.gbest_source == "BCO"


def test_e3_hybrid_adaptive_weighting(context: RoutingContext, base_config: AlgorithmConfig):
    base_config.e3_hybrid.enable_adaptive_weighting = True
    base_config.objectives.w_time = 0.7
    base_config.objectives.w_energy = 0.2
    base_config.objectives.w_emergency = 0.1
    base_config.objectives.w_distance = 0.0
    base_config.objectives.w_congestion = 0.0
    
    # Set custom feedback values in routing context
    context.traffic_speed_ratio = 0.5  # 50% speed degradation (congestion)
    context.energy_depletion_index = 0.8  # high battery depletion
    context.emergency_alert_status = 1.0  # active emergency
    
    router = E3HybridRouter(base_config, seed=42)
    router.find_route("A", "D", context)
    
    # Check that weights were dynamically adjusted from the base (0.7, 0.2, 0.1)
    # wt_raw = 0.7 + 0.15 * 0.5 = 0.775 -> max(0.3, 0.775) = 0.775
    # we_raw = 0.2 + 0.15 * 0.8 = 0.32 -> max(0.05, 0.32) = 0.32
    # ws_raw = 0.1 + 0.15 * 1.0 = 0.25 -> max(0.02, 0.25) = 0.25
    # w_sum = 0.775 + 0.32 + 0.25 = 1.345
    # w_time = 0.775 / 1.345 ≈ 0.576
    # w_energy = 0.32 / 1.345 ≈ 0.238
    # w_emergency = 0.25 / 1.345 ≈ 0.186
    assert router.scorer.config.w_time == pytest.approx(0.775 / 1.345)
    assert router.scorer.config.w_energy == pytest.approx(0.32 / 1.345)
    assert router.scorer.config.w_emergency == pytest.approx(0.25 / 1.345)
    assert router.scorer.config.w_distance == 0.0
    assert router.scorer.config.w_congestion == 0.0

