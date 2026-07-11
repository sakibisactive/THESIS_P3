"""Comprehensive unit tests for the Bee Colony Optimization (BCO) router."""

import pytest

from src.core.network import Edge, Network, Node
from src.core.vehicle import Vehicle
from src.emergency.incident import Incident
from src.utils.config import EmergencyEventConfig
from src.routing.bco import BCORouter
from src.routing.benchmark import RoutingBenchmark
from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.routing_context import RoutingContext
from src.utils.config import BCOConfig


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
    # Add nodes
    for i in range(1, 10):
        net.add_node(Node(node_id=f"n{i}", x=(i - 1) % 3 * 100.0, y=(i - 1) // 3 * 100.0))

    # Add horizontal edges (bidirectional)
    for row in range(3):
        for col in range(2):
            n_left = f"n{row * 3 + col + 1}"
            n_right = f"n{row * 3 + col + 2}"
            eid_lr = f"e_{n_left}_{n_right}"
            eid_rl = f"e_{n_right}_{n_left}"
            net.add_edge(Edge(edge_id=eid_lr, from_node=n_left, to_node=n_right, length=100.0, speed_limit=10.0))
            net.add_edge(Edge(edge_id=eid_rl, from_node=n_right, to_node=n_left, length=100.0, speed_limit=10.0))

    # Add vertical edges (bidirectional)
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
def bco_config() -> BCOConfig:
    return BCOConfig(
        colony_size=10,
        max_iterations=10,
        scout_ratio=0.3,
        recruitment_factor=0.8,
        abandonment_threshold=0.1,
        elite_route_seeding=False,
        collect_metrics=True,
    )


def test_scout_path_construction(grid_network: Network, bco_config: BCOConfig) -> None:
    """Scout bees should find valid paths through the network."""
    # Run scout constructions until one succeeds (random walks can hit dead-ends)
    for s in range(100):
        router = BCORouter(config=bco_config, seed=s)
        ctx = RoutingContext(network=grid_network, current_time=0.0)
        path, exp = router._construct_scout_path("n1", "n9", ctx)
        if path is not None:
            break
            
    assert path is not None
    nodes, edges, cost = path
    assert nodes[0] == "n1"
    assert nodes[-1] == "n9"
    assert len(nodes) == len(edges) + 1
    assert exp > 0


def test_neighborhood_search_prefix_retention(grid_network: Network, bco_config: BCOConfig) -> None:
    """Recruited bees must retain a valid prefix of the recruiter's path."""
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    recruiter_path = (
        ["n1", "n2", "n3", "n6", "n9"],
        ["e_n1_n2", "e_n2_n3", "e_n3_n6", "e_n6_n9"],
        40.0
    )
    
    path, _ = router._neighborhood_search(recruiter_path, "n1", "n9", ctx)
    
    assert path is not None
    nodes, edges, cost = path
    assert nodes[0] == "n1"
    assert nodes[-1] == "n9"
    
    # Find the divergence point
    match_len = 0
    for r_node, n_node in zip(recruiter_path[0], nodes, strict=False):
        if r_node == n_node:
            match_len += 1
        else:
            break
            
    # Should share at least the origin
    assert match_len >= 1


def test_loyalty_calculation_and_abandonment(bco_config: BCOConfig) -> None:
    """Waggle dance logic correctly computes loyalty and forces abandonment."""
    router = BCORouter(config=bco_config, seed=42)
    
    # Three paths with varying costs
    valid_paths = [
        (["a", "b"], ["e1"], 10.0),  # Best
        (["a", "c"], ["e2"], 15.0),  # Middle
        (["a", "d"], ["e3"], 50.0),  # Worst
    ]
    
    # We set a high abandonment threshold to force the worst to abandon
    router.config.abandonment_threshold = 0.5
    router.config.recruitment_factor = 1.0  # best bee loyalty = 1.0
    
    recruiters, abandoning = router._waggle_dance(valid_paths)
    
    # Best bee cost=10, max=50. 
    # Worst bee exponent: -(50-10)/(50-10) = -1. loyalty = 1.0 * exp(-1) = 0.36
    # Since 0.36 < 0.5, the worst bee must abandon
    assert abandoning >= 1


def test_bco_finds_valid_optimal_path(grid_network: Network, bco_config: BCOConfig) -> None:
    """The algorithm must converge to a valid, optimal path on a grid."""
    # Ensure sufficient iterations to converge
    bco_config.max_iterations = 20
    bco_config.colony_size = 20
    router = BCORouter(config=bco_config, seed=1)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res = router.find_route("n1", "n9", ctx)
    
    assert res.total_cost == pytest.approx(400.0)  # 4 edges * 100m
    assert len(res.path_edges) == 4
    assert res.path_nodes[0] == "n1"
    assert res.path_nodes[-1] == "n9"


def test_deterministic_with_same_seed(grid_network: Network, bco_config: BCOConfig) -> None:
    """Repeated runs with the same seed must yield identical metrics and paths."""
    r1 = BCORouter(config=bco_config, seed=123)
    r2 = BCORouter(config=bco_config, seed=123)
    
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res1 = r1.find_route("n1", "n9", ctx)
    res2 = r2.find_route("n1", "n9", ctx)
    
    assert res1.path_edges == res2.path_edges
    assert res1.total_cost == res2.total_cost
    assert r1.metrics_history[0].convergence_iteration == r2.metrics_history[0].convergence_iteration


def test_detour_around_closed_edge(grid_network: Network, bco_config: BCOConfig) -> None:
    """BCO must route around closed edges."""
    grid_network.edges["e_n2_n3"].is_closed = True
    grid_network.edges["e_n5_n6"].is_closed = True
    
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    res = router.find_route("n1", "n9", ctx)
    
    assert "e_n2_n3" not in res.path_edges
    assert "e_n5_n6" not in res.path_edges
    assert res.path_nodes[-1] == "n9"


def test_no_path_raises_error(grid_network: Network, bco_config: BCOConfig) -> None:
    """If destination is unreachable, BCO must raise NoPathFoundError."""
    # Isolate n9
    grid_network.edges["e_n6_n9"].is_closed = True
    grid_network.edges["e_n8_n9"].is_closed = True
    
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    with pytest.raises(NoPathFoundError):
        router.find_route("n1", "n9", ctx)


def test_bco_metrics_collection(grid_network: Network, bco_config: BCOConfig) -> None:
    """BCO should track iteration-by-iteration research metrics."""
    bco_config.collect_metrics = True
    router = BCORouter(config=bco_config, seed=10)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    router.find_route("n1", "n9", ctx)
    
    assert len(router.metrics_history) == 1
    m = router.metrics_history[0]
    
    assert m.query_origin == "n1"
    assert m.query_destination == "n9"
    assert m.num_iterations_run == bco_config.max_iterations
    assert len(m.iteration_records) == bco_config.max_iterations
    
    # Check that iteration records are populated
    for rec in m.iteration_records:
        assert 0.0 <= rec.scout_success_rate <= 1.0
        assert 0.0 <= rec.recruitment_effectiveness <= 1.0
        assert rec.colony_diversity > 0.0


def test_elite_route_seeding(grid_network: Network, bco_config: BCOConfig) -> None:
    """Elite seeding should inject the previous global best route into the next query."""
    bco_config.elite_route_seeding = True
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    # First query establishes global best
    res1 = router.find_route("n1", "n9", ctx)
    assert router._global_best_edges == res1.path_edges
    
    # Second query should use the seed (if config is true, it won't crash)
    res2 = router.find_route("n1", "n9", ctx)
    assert len(res2.path_edges) > 0


def test_elite_seeding_invalidation_on_update(grid_network: Network, bco_config: BCOConfig) -> None:
    """Network updates should invalidate seeded routes if they contain affected edges."""
    bco_config.elite_route_seeding = True
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    
    router.find_route("n1", "n9", ctx)
    assert len(router._global_best_edges) > 0
    
    # Update an edge that is NOT in the path
    unaffected = "e_n1_n2" if "e_n1_n2" not in router._global_best_edges else "e_n2_n3"
    router.update_network([unaffected]) 
    assert len(router._global_best_edges) > 0  # Should still be seeded
    
    # Update an edge that IS in the path
    affected_edge = router._global_best_edges[0]
    router.update_network([affected_edge])
    assert len(router._global_best_edges) == 0  # Seed should be wiped


def test_bco_in_routing_benchmark(grid_network: Network, bco_config: BCOConfig) -> None:
    """BCO must be compatible with the RoutingBenchmark suite."""
    router = BCORouter(config=bco_config, seed=1)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    res = RoutingBenchmark.run_benchmark({"BCO": router}, [("n1", "n9")], ctx)
    
    assert "BCO" in res
    assert res["BCO"].successful_searches == 1


def test_invalid_origin_raises(grid_network: Network, bco_config: BCOConfig) -> None:
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    with pytest.raises(InvalidNodeError):
        router.find_route("n99", "n9", ctx)


def test_same_origin_destination_returns_trivial(grid_network: Network, bco_config: BCOConfig) -> None:
    router = BCORouter(config=bco_config, seed=42)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    res = router.find_route("n1", "n1", ctx)
    assert res.total_cost == 0.0
    assert res.path_nodes == ["n1"]
    assert len(res.path_edges) == 0


def test_emergency_penalty_increases_score(grid_network: Network, bco_config: BCOConfig) -> None:
    """BCO should respect multi-objective scoring, such as emergency penalties."""
    # High emergency weight to force BCO to avoid incidents
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    bco_config.max_iterations = 20
    bco_config.colony_size = 20
    
    r_no_incident = BCORouter(config=bco_config, seed=5)
    r_no_incident.scorer.config.w_emergency = 100.0
    res_normal = r_no_incident.find_route("n1", "n9", ctx)
    
    # Create incident on the normal path
    incident_edge = res_normal.path_edges[1]
    # Incident centered on a node along the path
    inc_node = res_normal.path_nodes[1]  # n4 or n2
    inc_config = EmergencyEventConfig(
        id="inc1",
        epicenter_node_id=inc_node,
        start_time=0.0,
        duration=100.0,
        initial_radius_m=20.0,  # small radius so it only affects this specific area
        propagation_rate=0.0,
        intensity=1.0,
    )
    inc = Incident(inc_config)
    inc.epicenter_x = grid_network.nodes[inc_node].x
    inc.epicenter_y = grid_network.nodes[inc_node].y
    
    ctx_incident = RoutingContext(
        network=grid_network, current_time=0.0, active_incidents=[inc]
    )
    # Increase iteration count to ensure convergence to detour
    bco_config.max_iterations = 50
    bco_config.colony_size = 50
    r_incident = BCORouter(config=bco_config, seed=5)
    r_incident.scorer.config.w_emergency = 1000.0
    
    res_incident = r_incident.find_route("n1", "n9", ctx_incident)
    
    # Should take a detour
    assert incident_edge not in res_incident.path_edges
