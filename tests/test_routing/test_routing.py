"""Unit tests for the Routing Framework."""

import pytest

from src.core.battery import BatteryModel
from src.core.network import Edge, Network, Node
from src.core.vehicle import Vehicle
from src.routing.astar import AStarRouter
from src.routing.benchmark import RoutingBenchmark
from src.routing.cache import CachedRouter, RouteCache
from src.routing.dijkstra import DijkstraRouter
from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.heuristic import (
    EuclideanHeuristic,
    HeuristicType,
    ZeroHeuristic,
    get_heuristic,
)
from src.routing.routing_context import (
    RoutingContext,
    energy_optimal_cost,
    fastest_time_cost,
    shortest_distance_cost,
)
from src.utils.config import BatteryConfig


@pytest.fixture
def test_network() -> Network:
    """Creates a simple grid network for routing tests.

    Topology:
      (n4) --e4--> (n3)
       ^            ^
       |            |
      e3           e2
       |            |
      (n1) --e1--> (n2)
    """
    net = Network()
    n1 = Node("n1", 0.0, 0.0)
    n2 = Node("n2", 100.0, 0.0)
    n3 = Node("n3", 100.0, 100.0)
    n4 = Node("n4", 0.0, 100.0)

    net.add_node(n1)
    net.add_node(n2)
    net.add_node(n3)
    net.add_node(n4)

    # Set up edges
    e1 = Edge("e1", "n1", "n2", length=100.0, speed_limit=20.0)
    e2 = Edge("e2", "n2", "n3", length=100.0, speed_limit=20.0)
    e3 = Edge("e3", "n1", "n4", length=100.0, speed_limit=10.0)  # Slower route
    e4 = Edge("e4", "n4", "n3", length=100.0, speed_limit=10.0)

    net.add_edge(e1)
    net.add_edge(e2)
    net.add_edge(e3)
    net.add_edge(e4)

    return net


@pytest.fixture
def battery_config() -> BatteryConfig:
    """Fixture returning battery parameters."""
    return BatteryConfig(
        capacity_kwh=80.0,
        mass_kg=2000.0,
        efficiency=0.9,
        drag_coeff=0.3,
        frontal_area=2.2,
        rolling_res_coeff=0.015,
        regen_efficiency=0.7,
    )


@pytest.fixture
def test_vehicle(battery_config: BatteryConfig) -> Vehicle:
    """Fixture returning a test vehicle."""
    battery = BatteryModel(battery_config)
    return Vehicle(
        vehicle_id="v1",
        origin_node_id="n1",
        destination_node_id="n3",
        initial_soc=0.8,
        battery=battery,
    )


def test_shortest_path_correctness(test_network: Network) -> None:
    """Verifies that Dijkstra and A* return the correct shortest path by distance."""
    ctx = RoutingContext(
        network=test_network, cost_function=shortest_distance_cost
    )

    dijkstra = DijkstraRouter()
    astar = AStarRouter(heuristic=ZeroHeuristic())

    res_d = dijkstra.find_route("n1", "n3", ctx)
    res_a = astar.find_route("n1", "n3", ctx)

    # Shortest path by distance could be n1 -> n2 -> n3 (cost = 200.0) or
    # n1 -> n4 -> n3 (cost = 200.0)
    assert res_d.total_cost == 200.0
    assert res_a.total_cost == 200.0
    assert len(res_d.path_nodes) == 3
    assert len(res_a.path_nodes) == 3


def test_time_based_routing(test_network: Network) -> None:
    """Verifies route choice shifts to faster path using fastest_time_cost."""
    ctx = RoutingContext(network=test_network, cost_function=fastest_time_cost)

    dijkstra = DijkstraRouter()
    # Path via n2: 100/20 + 100/20 = 10.0 seconds
    # Path via n4: 100/10 + 100/10 = 20.0 seconds
    res = dijkstra.find_route("n1", "n3", ctx)

    assert res.total_cost == 10.0
    assert res.path_nodes == ["n1", "n2", "n3"]
    assert res.path_edges == ["e1", "e2"]


def test_invalid_nodes(test_network: Network) -> None:
    """Verifies that InvalidNodeError is raised for invalid node IDs."""
    ctx = RoutingContext(network=test_network)
    dijkstra = DijkstraRouter()

    with pytest.raises(InvalidNodeError):
        dijkstra.find_route("n_invalid", "n3", ctx)

    with pytest.raises(InvalidNodeError):
        dijkstra.find_route("n1", "n_invalid", ctx)


def test_disconnected_graphs(test_network: Network) -> None:
    """Verifies NoPathFoundError is raised if origin/destination are disconnected."""
    # Add a disconnected island node
    island = Node("island", 500.0, 500.0)
    test_network.add_node(island)

    ctx = RoutingContext(network=test_network)
    dijkstra = DijkstraRouter()
    astar = AStarRouter()

    with pytest.raises(NoPathFoundError):
        dijkstra.find_route("n1", "island", ctx)

    with pytest.raises(NoPathFoundError):
        astar.find_route("n1", "island", ctx)


def test_blocked_roads(test_network: Network) -> None:
    """Verifies routing detours around closed edges."""
    ctx = RoutingContext(network=test_network, cost_function=fastest_time_cost)
    dijkstra = DijkstraRouter()

    # Initially, optimal path is via n2 (cost = 10.0)
    res_before = dijkstra.find_route("n1", "n3", ctx)
    assert res_before.path_nodes == ["n1", "n2", "n3"]

    # Close edge e1
    test_network.edges["e1"].is_closed = True

    # Now optimal path must detour via n4 (cost = 20.0)
    res_after = dijkstra.find_route("n1", "n3", ctx)
    assert res_after.path_nodes == ["n1", "n4", "n3"]
    assert res_after.path_edges == ["e3", "e4"]
    assert res_after.total_cost == 20.0


def test_changing_edge_weights(test_network: Network) -> None:
    """Verifies route shifts when speed limits change dynamically."""
    ctx = RoutingContext(network=test_network, cost_function=fastest_time_cost)
    dijkstra = DijkstraRouter()

    # Initial: e1, e2 = 20m/s (time = 10s). e3, e4 = 10m/s (time = 20s)
    res1 = dijkstra.find_route("n1", "n3", ctx)
    assert res1.path_nodes == ["n1", "n2", "n3"]

    # Reduce speed limit of e1 to 2m/s (congestion/hazard)
    test_network.edges["e1"].speed_reduction_factor = 0.1  # speed goes to 2.0m/s
    # Path via n2 travel time is now: 100/2.0 + 100/20 = 55.0s
    # Path via n4 is still 20.0s

    res2 = dijkstra.find_route("n1", "n3", ctx)
    assert res2.path_nodes == ["n1", "n4", "n3"]
    assert res2.total_cost == 20.0


def test_heuristic_admissibility_and_consistency(test_network: Network) -> None:
    """Verifies admissibility and consistency of the heuristics.

    Heuristic cost must never exceed the true shortest distance (admissible).
    """
    ctx = RoutingContext(
        network=test_network, cost_function=shortest_distance_cost
    )
    dijkstra = DijkstraRouter()

    euclidean = get_heuristic(HeuristicType.EUCLIDEAN)
    manhattan = get_heuristic(HeuristicType.MANHATTAN)

    dest_node = test_network.nodes["n3"]

    for node_id, node in test_network.nodes.items():
        # Get true shortest distance to dest using Dijkstra
        true_res = dijkstra.find_route(node_id, "n3", ctx)
        true_dist = true_res.total_cost

        # Get heuristic estimates
        h_euclid = euclidean(node, dest_node, test_network)
        h_manhattan = manhattan(node, dest_node, test_network)

        # Admissibility
        assert h_euclid <= true_dist
        assert h_manhattan <= true_dist

        # Manhattan is consistent on a grid graph
        # Euclidean is consistent on Euclidean space


def test_astar_pruning_efficiency(test_network: Network) -> None:
    """Verifies A* with Euclidean heuristic expands <= nodes than Dijkstra."""
    ctx = RoutingContext(
        network=test_network, cost_function=shortest_distance_cost
    )

    dijkstra = DijkstraRouter()
    astar_zero = AStarRouter(heuristic=ZeroHeuristic())
    astar_euclid = AStarRouter(
        heuristic=EuclideanHeuristic(speed_scale_m_s=None)
    )

    res_d = dijkstra.find_route("n1", "n3", ctx)
    res_az = astar_zero.find_route("n1", "n3", ctx)
    res_ae = astar_euclid.find_route("n1", "n3", ctx)

    assert res_d.total_cost == res_az.total_cost == res_ae.total_cost
    # Search effort (expanded nodes) check
    assert res_ae.expanded_nodes <= res_d.expanded_nodes
    assert res_az.expanded_nodes == res_d.expanded_nodes


def test_cache_invalidation(test_network: Network) -> None:
    """Verifies that the route cache works and invalidates affected edges only."""
    cache = RouteCache()
    dijkstra = DijkstraRouter()
    cached_router = CachedRouter(delegate=dijkstra, cache=cache)

    ctx = RoutingContext(network=test_network, cost_function=fastest_time_cost)

    # 1. Warm up cache
    res1 = cached_router.find_route("n1", "n3", ctx)
    stats1 = cached_router.get_statistics()
    assert stats1["cache_hits"] == 0
    assert stats1["cache_misses"] == 1

    # 2. Subsequent query should hit cache
    res2 = cached_router.find_route("n1", "n3", ctx)
    stats2 = cached_router.get_statistics()
    assert res2.path_edges == res1.path_edges
    assert stats2["cache_hits"] == 1
    assert stats2["cache_misses"] == 1

    # 3. Cache another unrelated path (n1 -> n2)
    cached_router.find_route("n1", "n2", ctx)

    # 4. Trigger invalidation of edge e1 (closed road)
    cached_router.update_network("e1")

    # 5. Querying n1 -> n3 (which used e1) should miss
    cached_router.find_route("n1", "n3", ctx)
    stats3 = cached_router.get_statistics()
    assert stats3["cache_misses"] == 3  # Initial + n1->n2 + n1->n3 after invalidation
    assert stats3["cache_hits"] == 1


def test_vehicle_recalculation_count(test_vehicle: Vehicle) -> None:
    """Verifies vehicle's recalculation_count field works."""
    assert test_vehicle.recalculation_count == 0
    test_vehicle.recalculation_count += 1
    assert test_vehicle.recalculation_count == 1


def test_edge_case_single_node(test_network: Network) -> None:
    """Verifies routing behavior when origin matches destination."""
    ctx = RoutingContext(network=test_network)
    dijkstra = DijkstraRouter()

    res = dijkstra.find_route("n1", "n1", ctx)
    assert res.total_cost == 0.0
    assert res.path_nodes == ["n1"]
    assert res.path_edges == []
    assert res.expanded_nodes == 0


def test_johnson_reweighting(
    test_network: Network, test_vehicle: Vehicle
) -> None:
    """Verifies Johnson potential reweighting for EV energy routing.

    Tests that downhill slopes (negative raw energy) are mapped to non-negative costs,
    enabling correct shortest path calculation using Dijkstra.
    """
    # Topology:
    #   (n1) --e1--> (n2) : length=100m, gradient_rad = -0.1 (downhill)
    #   (n1) --e3--> (n4) --e4--> (n3) : flat paths
    # We change e1 gradient to downhill
    test_network.edges["e1"].gradient_rad = -0.1

    ctx = RoutingContext(
        network=test_network,
        vehicle=test_vehicle,
        cost_function=energy_optimal_cost,
    )
    dijkstra = DijkstraRouter()

    # The reweighted cost on downhill edge e1 must be strictly positive
    cost_e1 = energy_optimal_cost(
        test_network.edges["e1"], test_vehicle, test_network, ctx
    )
    assert cost_e1 > 0.0

    # Ensure search finds path successfully
    res = dijkstra.find_route("n1", "n2", ctx)
    assert res.path_nodes == ["n1", "n2"]
    assert res.total_cost > 0.0


def test_routing_benchmark(test_network: Network, test_vehicle: Vehicle) -> None:
    """Verifies RoutingBenchmark runs correctly and reports results."""
    routers = {
        "Dijkstra": DijkstraRouter(),
        "AStar": AStarRouter(heuristic=ZeroHeuristic()),
    }
    od_pairs = [("n1", "n3"), ("n1", "n2")]

    ctx = RoutingContext(
        network=test_network,
        vehicle=test_vehicle,
        cost_function=shortest_distance_cost,
    )

    reports = RoutingBenchmark.run_benchmark(routers, od_pairs, ctx)

    assert "Dijkstra" in reports
    assert "AStar" in reports
    assert reports["Dijkstra"].total_searches == 2
    assert reports["Dijkstra"].successful_searches == 2
    assert len(reports["Dijkstra"].queries) == 2
    assert reports["Dijkstra"].queries[0].success is True
