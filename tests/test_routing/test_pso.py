"""Comprehensive unit tests for the Particle Swarm Optimization (PSO) router."""

import pytest

from src.core.network import Edge, Network, Node
from src.emergency.incident import Incident
from src.routing.benchmark import RoutingBenchmark
from src.routing.exceptions import NoPathFoundError
from src.routing.pso import PSORouter
from src.routing.routing_context import RoutingContext
from src.utils.config import EmergencyEventConfig, PSOConfig


@pytest.fixture
def grid_network() -> Network:
    """Creates a 3x3 grid network for routing tests.
    
    n1 --100m-- n2 --100m-- n3
    |           |           |
    100m        100m        100m
    |           |           |
    n4 --100m-- n5 --100m-- n6
    |           |           |
    100m        100m        100m
    |           |           |
    n7 --100m-- n8 --100m-- n9
    """
    net = Network()
    for i in range(1, 10):
        net.add_node(Node(node_id=f"n{i}", x=(i - 1) % 3 * 100.0, y=(i - 1) // 3 * 100.0))

    for row in range(3):
        for col in range(2):
            n_left = f"n{row * 3 + col + 1}"
            n_right = f"n{row * 3 + col + 2}"
            eid_lr = f"e_{n_left}_{n_right}"
            eid_rl = f"e_{n_right}_{n_left}"
            net.add_edge(Edge(edge_id=eid_lr, from_node=n_left, to_node=n_right, length=100.0, speed_limit=10.0))
            net.add_edge(Edge(edge_id=eid_rl, from_node=n_right, to_node=n_left, length=100.0, speed_limit=10.0))

    for row in range(2):
        for col in range(3):
            n_top = f"n{row * 3 + col + 1}"
            n_bot = f"n{(row + 1) * 3 + col + 1}"
            eid_tb = f"e_{n_top}_{n_bot}"
            eid_bt = f"e_{n_bot}_{n_top}"
            net.add_edge(Edge(edge_id=eid_tb, from_node=n_top, to_node=n_bot, length=100.0, speed_limit=10.0))
            net.add_edge(Edge(edge_id=eid_bt, from_node=n_bot, to_node=n_top, length=100.0, speed_limit=10.0))

    return net


@pytest.fixture
def pso_config() -> PSOConfig:
    return PSOConfig(
        swarm_size=20,
        max_iterations=20,
        inertia_weight=0.7,
        cognitive_weight=1.5,
        social_weight=1.5,
        v_max=5.0,
        collect_metrics=True,
    )


def test_priority_based_decoding(grid_network: Network, pso_config: PSOConfig) -> None:
    """The DFS decoder should find a valid path using custom priority weights."""
    router = PSORouter(config=pso_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    # We create a priority vector that heavily favors a specific zig-zag path:
    # n1 -> n4 -> n5 -> n2 -> n3 -> n6 -> n9
    # This proves the decoder respects the continuous position vector (X).
    X_i = {
        "e_n1_n4": 100.0,
        "e_n4_n5": 100.0,
        "e_n5_n2": 100.0,
        "e_n2_n3": 100.0,
        "e_n3_n6": 100.0,
        "e_n6_n9": 100.0,
    }
    
    nodes, edges, cost, exp = router._decode_path("n1", "n9", X_i, ctx)
    
    assert nodes == ["n1", "n4", "n5", "n2", "n3", "n6", "n9"]
    assert len(edges) == 6
    assert cost > 0.0


def test_decoder_backtracking(grid_network: Network, pso_config: PSOConfig) -> None:
    """The decoder should backtrack out of dead ends to find a valid path."""
    # We close the direct route to n9, leaving only one narrow passage.
    grid_network.edges["e_n6_n9"].is_closed = True
    
    router = PSORouter(config=pso_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    # We force the priority vector to heavily favor the path to the dead end (n6)
    X_i = {
        "e_n1_n2": 1000.0,
        "e_n2_n3": 1000.0,
        "e_n3_n6": 1000.0,  # Trap
    }
    
    nodes, edges, cost, exp = router._decode_path("n1", "n9", X_i, ctx)
    
    # It must find n8 -> n9 instead, despite being led to n6 first
    assert len(nodes) > 0
    assert nodes[-1] == "n9"
    assert "e_n8_n9" in edges
    # Check that expansion count is higher due to backtracking
    assert exp > 5


def test_pso_finds_valid_optimal_path(grid_network: Network, pso_config: PSOConfig) -> None:
    """The PSO algorithm must converge to a valid, optimal path on a grid."""
    pso_config.max_iterations = 30
    pso_config.swarm_size = 30
    router = PSORouter(config=pso_config, seed=1)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res = router.find_route("n1", "n9", ctx)
    
    assert res.total_cost == pytest.approx(400.0)  # 4 edges * 100m
    assert len(res.path_edges) == 4
    assert res.path_nodes[0] == "n1"
    assert res.path_nodes[-1] == "n9"


def test_deterministic_with_same_seed(grid_network: Network, pso_config: PSOConfig) -> None:
    """Repeated runs with the same seed must yield identical behavior."""
    r1 = PSORouter(config=pso_config, seed=123)
    r2 = PSORouter(config=pso_config, seed=123)
    
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res1 = r1.find_route("n1", "n9", ctx)
    res2 = r2.find_route("n1", "n9", ctx)
    
    assert res1.path_edges == res2.path_edges
    assert res1.total_cost == res2.total_cost
    assert r1.metrics_history[0].convergence_iteration == r2.metrics_history[0].convergence_iteration
    
    # Verify particle states are identical
    for p1, p2 in zip(r1.particles, r2.particles, strict=True):
        assert p1.X == p2.X
        assert p1.V == p2.V


def test_detour_around_closed_edge(grid_network: Network, pso_config: PSOConfig) -> None:
    """PSO must route around closed edges."""
    grid_network.edges["e_n2_n3"].is_closed = True
    grid_network.edges["e_n5_n6"].is_closed = True
    
    router = PSORouter(config=pso_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res = router.find_route("n1", "n9", ctx)
    
    assert "e_n2_n3" not in res.path_edges
    assert "e_n5_n6" not in res.path_edges
    assert res.path_nodes[-1] == "n9"


def test_no_path_raises_error(grid_network: Network, pso_config: PSOConfig) -> None:
    """If destination is unreachable, PSO must raise NoPathFoundError."""
    # Isolate n9
    grid_network.edges["e_n6_n9"].is_closed = True
    grid_network.edges["e_n8_n9"].is_closed = True
    
    router = PSORouter(config=pso_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    with pytest.raises(NoPathFoundError):
        router.find_route("n1", "n9", ctx)


def test_pso_metrics_collection(grid_network: Network, pso_config: PSOConfig) -> None:
    """PSO should track iteration-by-iteration research metrics."""
    pso_config.collect_metrics = True
    router = PSORouter(config=pso_config, seed=10)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    router.find_route("n1", "n9", ctx)
    
    assert len(router.metrics_history) == 1
    m = router.metrics_history[0]
    
    assert m.query_origin == "n1"
    assert m.query_destination == "n9"
    assert m.num_iterations_run == pso_config.max_iterations
    assert len(m.iteration_records) == pso_config.max_iterations
    
    # Check that iteration records are populated
    for rec in m.iteration_records:
        assert rec.global_best_cost > 0
        assert rec.avg_particle_cost > 0
        assert rec.swarm_diversity >= 0.0
        assert rec.avg_velocity_magnitude >= 0.0


def test_dynamic_adaptation_on_update(grid_network: Network, pso_config: PSOConfig) -> None:
    """Network updates should trigger fitness re-evaluation of global bests without a reset."""
    router = PSORouter(config=pso_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    router.find_route("n1", "n9", ctx)
    initial_best_cost = router.g_best_cost
    assert initial_best_cost < float("inf")
    
    # Close an edge that is guaranteed to be in the global best path
    affected_edge = router.g_best_path_edges[0]
    grid_network.edges[affected_edge].is_closed = True
    
    # Flag the network as updated
    router.update_network([affected_edge]) 
    assert router._environment_dirty is True
    
    # Force re-evaluation manually to check the logic
    router._re_evaluate_bests(ctx)
    assert router.g_best_cost == float("inf")  # The old path is now blocked
    
    # Re-running search should find a new valid path since environment dirty flag handles it
    res2 = router.find_route("n1", "n9", ctx)
    assert res2.total_cost < float("inf")
    assert affected_edge not in res2.path_edges


def test_pso_in_routing_benchmark(grid_network: Network, pso_config: PSOConfig) -> None:
    """PSO must be compatible with the RoutingBenchmark suite."""
    router = PSORouter(config=pso_config, seed=1)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    res = RoutingBenchmark.run_benchmark({"PSO": router}, [("n1", "n9")], ctx)
    
    assert "PSO" in res
    assert res["PSO"].successful_searches == 1


def test_emergency_penalty_increases_score(grid_network: Network, pso_config: PSOConfig) -> None:
    """PSO should respect multi-objective scoring, such as emergency penalties."""
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    pso_config.max_iterations = 40
    pso_config.swarm_size = 30
    
    r_no_incident = PSORouter(config=pso_config, seed=5)
    r_no_incident.scorer.config.w_emergency = 100.0
    res_normal = r_no_incident.find_route("n1", "n9", ctx)
    
    # Create incident on the normal path
    inc_node = res_normal.path_nodes[1]
    inc_config = EmergencyEventConfig(
        id="inc1",
        epicenter_node_id=inc_node,
        start_time=0.0,
        duration=100.0,
        initial_radius_m=20.0,
        propagation_rate=0.0,
        intensity=1.0,
    )
    inc = Incident(inc_config)
    inc.epicenter_x = grid_network.nodes[inc_node].x
    inc.epicenter_y = grid_network.nodes[inc_node].y
    
    ctx_incident = RoutingContext(
        network=grid_network, current_time=0.0, active_incidents=[inc]
    )
    
    r_incident = PSORouter(config=pso_config, seed=5)
    r_incident.scorer.config.w_emergency = 1000.0
    
    res_incident = r_incident.find_route("n1", "n9", ctx_incident)
    
    # Should take a detour to avoid the incident node
    assert inc_node not in res_incident.path_nodes[1:-1]
