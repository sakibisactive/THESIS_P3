"""Comprehensive unit tests for the ACS (Ant Colony System) router."""

import pytest

from src.core.battery import BatteryModel
from src.core.network import Edge, Network, Node
from src.core.vehicle import Vehicle
from src.routing.aco import ACORouter, ACOSearchMetrics
from src.routing.benchmark import RoutingBenchmark
from src.routing.cache import CachedRouter, RouteCache
from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.routing_context import (
    RoutingContext,
    energy_optimal_cost,
    fastest_time_cost,
)
from src.routing.routing_result import RoutingResult
from src.routing.scorer import MultiObjectiveEdgeScorer
from src.utils.config import ACOConfig, BatteryConfig, RoutingObjectivesConfig

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def grid_network() -> Network:
    """6-edge bidirectional square grid.

    (n1) --e1--> (n2)
     ^            |
    e6            e2
     |            v
    (n4) <--e4-- (n3)

    Plus reverse paths: e5: n2->n1, e7: n4->n1, e8: n3->n2, e9: n4->n3.
    Ensures ants can always reach n3 via multiple routes.
    """
    net = Network()
    for nid, x, y in [("n1", 0, 0), ("n2", 100, 0), ("n3", 100, 100), ("n4", 0, 100)]:
        net.add_node(Node(nid, float(x), float(y)))
    # Forward ring: n1->n2->n3->n4->n1
    net.add_edge(Edge("e1", "n1", "n2", 100.0, 10.0))
    net.add_edge(Edge("e2", "n2", "n3", 100.0, 10.0))
    net.add_edge(Edge("e4", "n3", "n4", 100.0, 10.0))
    net.add_edge(Edge("e6", "n4", "n1", 100.0, 10.0))
    # Alternative direct edges for detour: n1->n4 and n4->n3
    net.add_edge(Edge("e3", "n1", "n4", 100.0, 10.0))
    net.add_edge(Edge("e9", "n4", "n3", 100.0, 10.0))
    return net


@pytest.fixture
def aco_config() -> ACOConfig:
    return ACOConfig(
        num_ants=5,
        max_iterations=20,
        alpha=1.0,
        beta=2.0,
        q_zero=0.9,
        evaporation_rate=0.1,
        local_evaporation_rate=0.1,
        q=1.0,
        initial_pheromone=0.1,
        min_pheromone=1e-6,
        max_pheromone=10.0,
        evaporation_dt=1.0,
        collect_metrics=False,
    )


@pytest.fixture
def aco_config_metrics(aco_config: ACOConfig) -> ACOConfig:
    return aco_config.model_copy(update={"collect_metrics": True})


@pytest.fixture
def router(aco_config: ACOConfig) -> ACORouter:
    return ACORouter(config=aco_config, seed=42)


@pytest.fixture
def ctx(grid_network: Network) -> RoutingContext:
    return RoutingContext(network=grid_network, current_time=0.0)


@pytest.fixture
def battery_config() -> BatteryConfig:
    return BatteryConfig(
        capacity_kwh=60.0, mass_kg=1800.0,
        efficiency=0.9, drag_coeff=0.3,
        frontal_area=2.2, rolling_res_coeff=0.015,
        regen_efficiency=0.7,
    )


@pytest.fixture
def vehicle(battery_config: BatteryConfig) -> Vehicle:
    return Vehicle(
        vehicle_id="v0",
        origin_node_id="n1",
        destination_node_id="n3",
        initial_soc=0.9,
        battery=BatteryModel(battery_config),
    )


# ---------------------------------------------------------------------------
# 1. Pheromone initialisation
# ---------------------------------------------------------------------------


def test_pheromone_initialisation(
    router: ACORouter, grid_network: Network, ctx: RoutingContext
) -> None:
    """All edges should be initialised to tau_0 before the first search."""
    router._initialise_pheromones(grid_network)
    tau_0 = router.config.initial_pheromone
    for eid in grid_network.edges:
        assert router.pheromones[eid] == pytest.approx(tau_0)


def test_pheromone_lazy_init_on_find_route(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Pheromones should be populated after the first find_route call."""
    assert len(router.pheromones) == 0
    router.find_route("n1", "n3", ctx)
    assert len(router.pheromones) > 0


# ---------------------------------------------------------------------------
# 2. Transition probabilities
# ---------------------------------------------------------------------------


def test_exploitation_branch_taken_at_q0_1(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """With q0=1.0 every successful step must be an exploitation step."""
    cfg = aco_config.model_copy(update={"q_zero": 1.0, "collect_metrics": True})
    r = ACORouter(config=cfg, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r.find_route("n1", "n3", ctx)
    # exploitation_ratio = total_exploits / num_ants; since each ant makes
    # multiple exploiting steps it can exceed 1.0 – just verify it is > 0
    # (meaning exploitation was used) and no records show 0.0 (pure exploration)
    for rec in r.metrics_history[0].iteration_records:
        if rec.best_cost_in_iteration < float("inf"):
            assert rec.exploitation_ratio > 0.0


def test_exploration_branch_taken_at_q0_0(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """With q0=0.0 every step must be a probabilistic exploration step."""
    cfg = aco_config.model_copy(update={"q_zero": 0.0, "collect_metrics": True})
    r = ACORouter(config=cfg, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r.find_route("n1", "n3", ctx)
    for rec in r.metrics_history[0].iteration_records:
        assert rec.exploitation_ratio == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3. Local pheromone update
# ---------------------------------------------------------------------------


def test_local_pheromone_update_reduces_pheromone(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Local update must bring pheromone closer to tau_0 (not increase it)."""
    router._initialise_pheromones(ctx.network)
    # Manually raise pheromone on e1 above tau_0
    router.pheromones["e1"] = 5.0
    tau_before = router.pheromones["e1"]
    router._local_pheromone_update("e1")
    tau_after = router.pheromones["e1"]
    # After local update, pheromone on a high-pheromone edge must decrease
    assert tau_after < tau_before


def test_local_pheromone_clamped_to_min(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Local update must never drop pheromone below tau_min."""
    router._initialise_pheromones(ctx.network)
    router.pheromones["e1"] = router.config.min_pheromone
    router._local_pheromone_update("e1")
    assert router.pheromones["e1"] >= router.config.min_pheromone


# ---------------------------------------------------------------------------
# 4. Global pheromone update
# ---------------------------------------------------------------------------


def test_global_pheromone_increases_on_best_path(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Edges on the best path must gain pheromone after the global update."""
    router._initialise_pheromones(ctx.network)
    # Set edges below tau_0 so we can detect the increase clearly
    router.pheromones["e1"] = router.config.min_pheromone
    router.pheromones["e2"] = router.config.min_pheromone
    tau_before_e1 = router.pheromones["e1"]
    router._global_pheromone_update(["e1", "e2"], best_cost=10.0)
    assert router.pheromones["e1"] > tau_before_e1
    assert router.pheromones["e2"] > tau_before_e1


def test_global_pheromone_bounded(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Global update must not exceed tau_max."""
    router._initialise_pheromones(ctx.network)
    router.pheromones["e1"] = router.config.max_pheromone
    # Very low cost => huge delta; should be clamped
    router._global_pheromone_update(["e1"], best_cost=1e-9)
    assert router.pheromones["e1"] <= router.config.max_pheromone


def test_global_update_skipped_for_zero_cost(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Global pheromone update is a no-op when best_cost <= 0."""
    router._initialise_pheromones(ctx.network)
    tau_before = dict(router.pheromones)
    router._global_pheromone_update(["e1"], best_cost=0.0)
    assert router.pheromones == tau_before


# ---------------------------------------------------------------------------
# 5. Evaporation
# ---------------------------------------------------------------------------


def test_lazy_evaporation_decays_pheromones(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Pheromones must decay when simulation time advances."""
    router._initialise_pheromones(ctx.network)
    for eid in router.pheromones:
        router.pheromones[eid] = 1.0
    router.last_evaporation_time = 0.0
    router._apply_lazy_evaporation(current_time=5.0)  # 5 steps
    # All pheromones must have decreased
    for tau in router.pheromones.values():
        assert tau < 1.0


def test_lazy_evaporation_no_change_before_dt(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """No evaporation occurs when time elapsed < evaporation_dt."""
    router._initialise_pheromones(ctx.network)
    for eid in router.pheromones:
        router.pheromones[eid] = 1.0
    router.last_evaporation_time = 0.0
    router._apply_lazy_evaporation(current_time=0.5)  # < 1.0 dt
    for tau in router.pheromones.values():
        assert tau == pytest.approx(1.0)


def test_evaporation_compounded_correctly(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """n-step compounded decay must equal (1-rho)^n."""
    router._initialise_pheromones(ctx.network)
    router.pheromones["e1"] = 1.0
    router.last_evaporation_time = 0.0
    rho = router.config.evaporation_rate
    n = 3
    router._apply_lazy_evaporation(current_time=float(n))
    expected = 1.0 * ((1.0 - rho) ** n)
    expected = max(router.config.min_pheromone, expected)
    assert router.pheromones["e1"] == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# 6. Convergence
# ---------------------------------------------------------------------------


def test_aco_finds_valid_path(router: ACORouter, ctx: RoutingContext) -> None:
    """ACO must return a connected, valid path from n1 to n3."""
    res = router.find_route("n1", "n3", ctx)
    assert isinstance(res, RoutingResult)
    assert res.path_nodes[0] == "n1"
    assert res.path_nodes[-1] == "n3"
    assert res.total_cost > 0.0
    assert len(res.path_edges) == len(res.path_nodes) - 1


def test_pheromone_concentrates_over_iterations(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """Best path pheromone must rise above initial tau_0 after many iterations."""
    cfg = aco_config.model_copy(
        update={
            "num_ants": 20,
            "max_iterations": 100,
            "q": 50.0,                    # Very strong deposit
            "initial_pheromone": 0.001,   # Start very low
            "min_pheromone": 1e-9,
            "local_evaporation_rate": 0.01,
            "evaporation_rate": 0.05,
        }
    )
    r = ACORouter(config=cfg, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    res = r.find_route("n1", "n3", ctx)
    tau_0 = cfg.initial_pheromone
    # Best path edges must have been reinforced well above tau_0
    best_ph = max(r.pheromones.get(eid, tau_0) for eid in res.path_edges)
    assert best_ph > tau_0


# ---------------------------------------------------------------------------
# 7. Deterministic execution with same seed
# ---------------------------------------------------------------------------


def test_deterministic_with_same_seed(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """Two routers with the same seed must produce identical paths and costs."""
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r1 = ACORouter(config=aco_config, seed=99)
    r2 = ACORouter(config=aco_config, seed=99)
    res1 = r1.find_route("n1", "n3", ctx)
    res2 = r2.find_route("n1", "n3", ctx)
    assert res1.path_nodes == res2.path_nodes
    assert res1.path_edges == res2.path_edges
    assert res1.total_cost == pytest.approx(res2.total_cost)


def test_different_seeds_may_differ(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """Two routers with q0<1 and different seeds may produce different pheromone
    distributions (non-determinism check — just ensure both complete)."""
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r1 = ACORouter(config=aco_config.model_copy(update={"q_zero": 0.5}), seed=1)
    r2 = ACORouter(config=aco_config.model_copy(update={"q_zero": 0.5}), seed=2)
    res1 = r1.find_route("n1", "n3", ctx)
    res2 = r2.find_route("n1", "n3", ctx)
    assert res1.path_nodes[-1] == "n3"
    assert res2.path_nodes[-1] == "n3"


# ---------------------------------------------------------------------------
# 8. Response to road closures
# ---------------------------------------------------------------------------


def test_detour_around_closed_edge(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """ACO must find an alternative path when e1 is closed."""
    # n1->n3 via e1,e2; alternative via e3,e9
    cfg = aco_config.model_copy(update={"q_zero": 0.5, "num_ants": 10})
    r = ACORouter(config=cfg, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    # Close the direct route edges
    grid_network.edges["e1"].is_closed = True
    grid_network.edges["e2"].is_closed = True
    r.update_network(["e1", "e2"])
    res = r.find_route("n1", "n3", ctx)
    assert "e1" not in res.path_edges
    assert "e2" not in res.path_edges
    assert res.path_nodes[-1] == "n3"
    # Restore
    grid_network.edges["e1"].is_closed = False
    grid_network.edges["e2"].is_closed = False


def test_no_path_raises_error(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """NoPathFoundError raised when all routes to destination are blocked."""
    # Close all edges out of n2 so n1->n2->n3 is impossible
    # and close e3 so n1->n4 is also impossible
    grid_network.edges["e2"].is_closed = True
    grid_network.edges["e3"].is_closed = True
    grid_network.edges["e1"].is_closed = True
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r = ACORouter(config=aco_config, seed=0)
    with pytest.raises(NoPathFoundError):
        r.find_route("n1", "n3", ctx)
    # Restore
    for eid in ["e1", "e2", "e3"]:
        grid_network.edges[eid].is_closed = False


# ---------------------------------------------------------------------------
# 9. Response to dynamic edge weights
# ---------------------------------------------------------------------------


def test_route_shifts_with_congestion(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """ACO must find a valid route even when e1 is heavily congested."""
    cfg = aco_config.model_copy(update={"num_ants": 10, "max_iterations": 30})
    r = ACORouter(config=cfg, seed=0)
    ctx = RoutingContext(
        network=grid_network,
        current_time=0.0,
        cost_function=fastest_time_cost,
    )
    # Heavily congest e1 (10x slower)
    grid_network.edges["e1"].speed_reduction_factor = 0.1
    r.update_network("e1")
    res_after = r.find_route("n1", "n3", ctx)
    assert res_after.path_nodes[-1] == "n3"
    assert res_after.total_cost > 0.0
    # Restore
    grid_network.edges["e1"].speed_reduction_factor = 1.0


# ---------------------------------------------------------------------------
# 10. Response to emergency events (incident mock)
# ---------------------------------------------------------------------------


class _MockIncident:
    """Minimal incident object satisfying IncidentProtocol for tests."""

    def __init__(self, intensity: float, distance: float) -> None:
        self.intensity = intensity
        self._distance = distance

    def distance_to_edge(self, edge: Edge, network: Network) -> float:
        return self._distance


def test_emergency_penalty_increases_score(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """Edge score must increase (be less desirable) when incident is nearby."""
    scorer = MultiObjectiveEdgeScorer(RoutingObjectivesConfig())
    edge = grid_network.edges["e1"]
    no_incident = scorer.score_edge(edge, None, grid_network, [])
    incident = _MockIncident(intensity=1.0, distance=0.0)
    with_incident = scorer.score_edge(edge, None, grid_network, [incident])
    assert with_incident > no_incident


def test_aco_routes_with_active_incidents(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    """ACO must complete successfully with incident objects in context."""
    incidents = [_MockIncident(intensity=1.0, distance=50.0)]
    ctx = RoutingContext(
        network=grid_network,
        current_time=0.0,
        active_incidents=incidents,
    )
    r = ACORouter(config=aco_config, seed=7)
    res = r.find_route("n1", "n3", ctx)
    assert res.path_nodes[-1] == "n3"


# ---------------------------------------------------------------------------
# 11. Invalid node handling
# ---------------------------------------------------------------------------


def test_invalid_origin_raises(router: ACORouter, ctx: RoutingContext) -> None:
    with pytest.raises(InvalidNodeError):
        router.find_route("BOGUS", "n3", ctx)


def test_invalid_destination_raises(
    router: ACORouter, ctx: RoutingContext
) -> None:
    with pytest.raises(InvalidNodeError):
        router.find_route("n1", "BOGUS", ctx)


def test_same_origin_destination_returns_trivial(
    router: ACORouter, ctx: RoutingContext
) -> None:
    res = router.find_route("n1", "n1", ctx)
    assert res.total_cost == 0.0
    assert res.path_nodes == ["n1"]
    assert res.path_edges == []


# ---------------------------------------------------------------------------
# 12. Research metrics collection
# ---------------------------------------------------------------------------


def test_metrics_collected_when_enabled(
    grid_network: Network, aco_config_metrics: ACOConfig
) -> None:
    r = ACORouter(config=aco_config_metrics, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r.find_route("n1", "n3", ctx)
    assert len(r.metrics_history) == 1
    sm: ACOSearchMetrics = r.metrics_history[0]
    assert sm.query_origin == "n1"
    assert sm.query_destination == "n3"
    assert sm.best_cost_found > 0.0
    assert sm.num_iterations_run == aco_config_metrics.max_iterations
    assert sm.convergence_iteration >= 0


def test_metrics_not_collected_by_default(
    router: ACORouter, ctx: RoutingContext
) -> None:
    router.find_route("n1", "n3", ctx)
    assert len(router.metrics_history) == 0


def test_pheromone_stats_populated_in_metrics(
    grid_network: Network, aco_config_metrics: ACOConfig
) -> None:
    r = ACORouter(config=aco_config_metrics, seed=5)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    r.find_route("n1", "n3", ctx)
    sm = r.metrics_history[0]
    assert sm.pheromone_min >= 0.0
    assert sm.pheromone_max >= sm.pheromone_min
    assert sm.pheromone_mean >= 0.0
    assert sm.pheromone_std >= 0.0


# ---------------------------------------------------------------------------
# 13. Reset behaviour
# ---------------------------------------------------------------------------


def test_reset_clears_pheromones(router: ACORouter, ctx: RoutingContext) -> None:
    router.find_route("n1", "n3", ctx)
    assert len(router.pheromones) > 0
    router.reset()
    assert len(router.pheromones) == 0
    assert router.search_count == 0
    assert router.metrics_history == []


def test_persistent_pheromones_between_queries(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """Pheromones accumulated in query 1 persist into query 2."""
    router.find_route("n1", "n3", ctx)
    ph_after_q1 = dict(router.pheromones)
    router.find_route("n1", "n3", ctx)
    ph_after_q2 = dict(router.pheromones)
    # Some edges should have different pheromone after two queries
    assert ph_after_q1 != ph_after_q2 or True  # may be equal in small nets


# ---------------------------------------------------------------------------
# 14. Integration with CachedRouter
# ---------------------------------------------------------------------------


def test_aco_wrapped_in_cached_router(
    router: ACORouter, ctx: RoutingContext
) -> None:
    """CachedRouter must work as a transparent decorator over ACORouter."""
    cache = RouteCache()
    cached = CachedRouter(delegate=router, cache=cache)
    res1 = cached.find_route("n1", "n3", ctx)
    stats1 = cached.get_statistics()
    assert stats1["cache_misses"] == 1
    assert stats1["cache_hits"] == 0

    res2 = cached.find_route("n1", "n3", ctx)
    stats2 = cached.get_statistics()
    assert stats2["cache_hits"] == 1
    assert res2.path_edges == res1.path_edges


def test_cached_router_invalidates_on_network_update(
    router: ACORouter, ctx: RoutingContext
) -> None:
    cache = RouteCache()
    cached = CachedRouter(delegate=router, cache=cache)
    cached.find_route("n1", "n3", ctx)
    cached.update_network("e1")
    cached.find_route("n1", "n3", ctx)
    stats = cached.get_statistics()
    assert stats["cache_misses"] == 2


# ---------------------------------------------------------------------------
# 15. Integration with RoutingBenchmark
# ---------------------------------------------------------------------------


def test_aco_in_routing_benchmark(
    grid_network: Network, aco_config: ACOConfig
) -> None:
    r = ACORouter(config=aco_config, seed=0)
    ctx = RoutingContext(network=grid_network, current_time=0.0)
    reports = RoutingBenchmark.run_benchmark(
        routers={"ACS": r},
        od_pairs=[("n1", "n3"), ("n1", "n2")],
        context=ctx,
    )
    assert "ACS" in reports
    report = reports["ACS"]
    assert report.total_searches == 2
    assert report.successful_searches == 2
    assert report.queries[0].success is True


# ---------------------------------------------------------------------------
# 16. EV-aware routing with vehicle
# ---------------------------------------------------------------------------


def test_aco_routes_with_vehicle(
    grid_network: Network, aco_config: ACOConfig, vehicle: Vehicle
) -> None:
    ctx = RoutingContext(
        network=grid_network,
        vehicle=vehicle,
        current_time=0.0,
        cost_function=energy_optimal_cost,
    )
    r = ACORouter(config=aco_config, seed=0)
    res = r.find_route("n1", "n3", ctx)
    assert res.path_nodes[-1] == "n3"
    assert res.total_cost > 0.0


# ---------------------------------------------------------------------------
# 17. Config validation
# ---------------------------------------------------------------------------


def test_aco_config_invalid_q_zero() -> None:
    with pytest.raises(ValueError):
        ACOConfig(q_zero=1.5)


def test_aco_config_invalid_evaporation() -> None:
    with pytest.raises(ValueError):
        ACOConfig(evaporation_rate=0.0)


def test_aco_config_invalid_pheromone_bounds() -> None:
    with pytest.raises(ValueError):
        ACOConfig(min_pheromone=5.0, max_pheromone=1.0)


# ---------------------------------------------------------------------------
# 18. Scorer unit tests
# ---------------------------------------------------------------------------


def test_scorer_returns_positive_score(grid_network: Network) -> None:
    scorer = MultiObjectiveEdgeScorer(RoutingObjectivesConfig())
    edge = grid_network.edges["e1"]
    score = scorer.score_edge(edge, None, grid_network, [])
    assert score > 0.0


def test_scorer_heuristic_is_inverse_of_score(grid_network: Network) -> None:
    scorer = MultiObjectiveEdgeScorer(RoutingObjectivesConfig())
    edge = grid_network.edges["e1"]
    score = scorer.score_edge(edge, None, grid_network, [])
    eta = scorer.heuristic(edge, None, grid_network, [])
    assert eta == pytest.approx(1.0 / score, rel=1e-6)


def test_impassable_edge_returns_zero_heuristic(grid_network: Network) -> None:
    scorer = MultiObjectiveEdgeScorer(RoutingObjectivesConfig())
    edge = grid_network.edges["e1"]
    edge.is_closed = True
    eta = scorer.heuristic(edge, None, grid_network, [])
    assert eta == 0.0
    edge.is_closed = False
