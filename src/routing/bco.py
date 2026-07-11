"""Bee Colony Optimization (BCO) routing algorithm for dynamic EV urban routing.

Algorithm Reference
-------------------
Lučić, P. & Teodorović, D. (2001). Bee System: Solving routing problems
by artificial bees. Journal of Heuristics, 7, 507–526.
https://doi.org/10.1023/A:1011400619864

BCO Variant Description
-----------------------
This is a constructive Bee Colony Optimization approach adapted for shortest-path
routing in dynamic, multi-objective environments.

The colony consists of B bees. In each iteration:
1.  **Forward Pass (Scout/Recruit Phase)**:
    -   *Scouts* construct entirely new paths from origin to destination using a
        heuristic-guided probabilistic random walk (exploration).
    -   *Recruits* follow an advertised path prefix from a recruiter bee up to a
        randomly chosen node, then perform a heuristic-guided random walk to the
        destination from that point (neighborhood search / local exploitation).
2.  **Backward Pass (Waggle Dance Phase)**:
    -   All bees evaluate the multi-objective cost of their constructed paths.
    -   Bees calculate a Loyalty Probability based on their route quality relative
        to the colony's performance in the current iteration.
    -   Bees probabilistically decide to become *Recruiters* (loyal) or *Abandon*
        their routes.
    -   Abandoning bees select a recruiter using roulette-wheel selection,
        proportional to the recruiter's path quality.

Loyalty Probability Formula
---------------------------
For a bee b with valid path cost C_b:
    p_b = recruitment_factor * exp( - (C_b - C_best) / (C_max - C_best + epsilon) )

Where C_best and C_max are the minimum and maximum costs found in the iteration.

Deviations from the Original Paper
-----------------------------------
1.  **Dynamic EV Environment**: Evaluates paths using the injected
    `MultiObjectiveEdgeScorer` (travel time, energy, hazards) rather than simple
    Euclidean distance.
2.  **Elite Route Seeding**: An optional, configurable mechanism that seeds the
    initial iteration of a new query with the global best path from previous
    queries. This replaces BCO's typical lack of inter-query memory, enabling
    faster convergence in continuous simulations where origin-destination pairs
    are frequently queried. This must be disabled for independent benchmarks.
3.  **Path Dead-ends**: In directed graphs, bees may hit dead-ends. Such paths
    are marked invalid (cost = infinity) and the bee is forced to abandon.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.routing.base_swarm import SwarmIterationResult
from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult
from src.routing.scorer import MultiObjectiveEdgeScorer
from src.utils.config import BCOConfig, RoutingObjectivesConfig

# ---------------------------------------------------------------------------
# Research metrics data structures
# ---------------------------------------------------------------------------


@dataclass
class BCOIterationMetrics:
    """Stores per-iteration diagnostics for one BCO search call."""

    iteration: int
    best_cost_in_iteration: float
    avg_cost_in_iteration: float
    # Fraction of scouts that found a valid path to the destination
    scout_success_rate: float
    # Fraction of recruits that successfully constructed a valid path
    recruitment_effectiveness: float
    # Number of unique routes divided by colony size
    colony_diversity: float
    # Fraction of the colony acting as recruiters for the next iteration
    loyalty_distribution: float
    # Fraction of the colony that abandoned their routes
    abandonment_rate: float


@dataclass
class BCOSearchMetrics:
    """Aggregate research metrics for a single find_route() call."""

    query_origin: str
    query_destination: str
    num_iterations_run: int
    # Iteration index at which the globally best solution was last improved
    convergence_iteration: int
    best_cost_found: float
    # Fraction of iterations where the best path remained identical to the previous
    route_stability: float
    # Per-iteration diagnostic records
    iteration_records: list[BCOIterationMetrics] = field(default_factory=list)


# Internal tuple representing a candidate edge for heuristic selection
_Candidate = tuple[str, str, float, float]  # (to_node, edge_id, desirability, cost)

# Internal tuple representing a bee's constructed path
# (path_nodes, path_edges, total_cost)
_BeePath = tuple[list[str], list[str], float]


# ---------------------------------------------------------------------------
# BCO Router
# ---------------------------------------------------------------------------


class BCORouter(Router):
    """Bee Colony Optimization (BCO) router for dynamic urban networks."""

    def __init__(
        self,
        config: BCOConfig,
        scorer: MultiObjectiveEdgeScorer | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialises the BCO router.

        Args:
            config: Full BCO hyperparameter configuration.
            scorer: Optional pre-built MultiObjectiveEdgeScorer. If None,
                a default scorer is constructed internally.
            seed: Optional random seed for fully reproducible execution.
        """
        self.config = config
        self.scorer = scorer or MultiObjectiveEdgeScorer(
            RoutingObjectivesConfig()
        )
        self._rng = random.Random(seed)

        # Inter-query memory (used only if elite_route_seeding is True)
        self._global_best_cost: float = float("inf")
        self._global_best_nodes: list[str] = []
        self._global_best_edges: list[str] = []

        # Execution statistics
        self.search_count: int = 0
        self.total_search_time: float = 0.0
        self.total_expanded_nodes: int = 0
        self.metrics_history: list[BCOSearchMetrics] = []

    # ------------------------------------------------------------------
    # Router interface
    # ------------------------------------------------------------------

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds a high-quality route using the BCO algorithm.

        Executes up to config.max_iterations. In each iteration, bees construct
        paths (forward pass) and then perform a waggle dance to recruit peers
        (backward pass).

        Args:
            origin_node_id: ID of the starting node.
            destination_node_id: ID of the target node.
            context: RoutingContext containing network, vehicle, and time.

        Returns:
            RoutingResult: Best path found.

        Raises:
            InvalidNodeError: If node IDs are absent.
            NoPathFoundError: If no bee can reach the destination.
        """
        self.search_count += 1
        start_wall = time.perf_counter()

        self._validate_nodes(origin_node_id, destination_node_id, context)

        if origin_node_id == destination_node_id:
            return self._trivial_result(origin_node_id, start_wall)

        best_nodes, best_edges, best_cost, conv_iter, total_expanded = (
            self._run_bco_iterations(
                origin_node_id, destination_node_id, context
            )
        )

        if not best_nodes:
            raise NoPathFoundError(
                f"No bee path found from '{origin_node_id}' to "
                f"'{destination_node_id}'."
            )

        if best_cost < self._global_best_cost:
            self._global_best_cost = best_cost
            self._global_best_nodes = list(best_nodes)
            self._global_best_edges = list(best_edges)

        elapsed = time.perf_counter() - start_wall
        self.total_search_time += elapsed
        self.total_expanded_nodes += total_expanded

        return RoutingResult(
            path_nodes=best_nodes,
            path_edges=best_edges,
            total_cost=best_cost,
            expanded_nodes=total_expanded,
            search_time_s=elapsed,
        )

    def update_network(self, network_update: Any) -> None:
        """Handles dynamic network changes.

        Unlike ACO, BCO does not maintain a persistent pheromone matrix.
        However, if elite_route_seeding is enabled, we invalidate the global
        best path if it contains affected edges so it isn't seeded into the
        next query.
        """
        if not self.config.elite_route_seeding:
            return

        edge_ids: list[str] = []
        if isinstance(network_update, str):
            edge_ids = [network_update]
        elif isinstance(network_update, list):
            edge_ids = [e for e in network_update if isinstance(e, str)]

        for eid in edge_ids:
            if eid in self._global_best_edges:
                self._global_best_cost = float("inf")
                self._global_best_nodes = []
                self._global_best_edges = []
                break

    def reset(self) -> None:
        """Resets all execution statistics and elite route memory.

        Should be called when beginning a new independent experiment.
        """
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0
        self._global_best_cost = float("inf")
        self._global_best_nodes = []
        self._global_best_edges = []
        self.metrics_history.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Returns cumulative execution statistics."""
        return {
            "algorithm": "BCO",
            "search_count": self.search_count,
            "total_search_time_s": self.total_search_time,
            "avg_search_time_s": (
                self.total_search_time / self.search_count
                if self.search_count > 0 else 0.0
            ),
            "total_expanded_nodes": self.total_expanded_nodes,
            "global_best_cost": self._global_best_cost,
            "metrics_records": len(self.metrics_history),
        }

    def get_pheromone_matrix(self) -> dict[str, float] | None:
        """BCO does not use pheromones."""
        return None

    def inject_pheromone_matrix(self, matrix: dict[str, float]) -> None:
        """Not applicable for BCO."""
        pass

    def inject_global_best(self, path_nodes: list[str], path_edges: list[str], cost: float) -> None:
        """Injects a globally discovered best path into the engine.
        For BCO, this seeds the recruiter pool.
        """
        if path_edges and cost < float("inf"):
            self._current_recruiters.append((path_nodes, path_edges, cost))

    # ------------------------------------------------------------------
    # Private: Search Orchestration
    # ------------------------------------------------------------------

    def _validate_nodes(
        self, origin_node_id: str, destination_node_id: str, context: RoutingContext
    ) -> None:
        if origin_node_id not in context.network.nodes:
            raise InvalidNodeError(f"Origin '{origin_node_id}' not in network.")
        if destination_node_id not in context.network.nodes:
            raise InvalidNodeError(f"Destination '{destination_node_id}' not found.")

    def _trivial_result(self, node_id: str, start_wall: float) -> RoutingResult:
        elapsed = time.perf_counter() - start_wall
        self.total_search_time += elapsed
        return RoutingResult(
            path_nodes=[node_id],
            path_edges=[],
            total_cost=0.0,
            expanded_nodes=0,
            search_time_s=elapsed,
        )

    def _run_bco_iterations(
        self, origin: str, dest: str, context: RoutingContext
    ) -> tuple[list[str], list[str], float, int, int]:
        """Main BCO loop running forward and backward passes."""
        metrics: BCOSearchMetrics | None = None
        if self.config.collect_metrics:
            metrics = BCOSearchMetrics(
                query_origin=origin,
                query_destination=dest,
                num_iterations_run=0,
                convergence_iteration=0,
                best_cost_found=float("inf"),
                route_stability=0.0,
            )

        best_cost = float("inf")
        best_nodes: list[str] = []
        best_edges: list[str] = []
        conv_iter = 0
        total_expanded = 0
        identical_best_count = 0

        self.initialize_search(origin, dest, context)

        for iteration in range(self.config.max_iterations):
            iter_result = self.execute_iteration(origin, dest, context)
            
            iter_best_cost = float("inf")
            iter_best_path: _BeePath | None = None
            
            valid_paths = []
            for nodes, edges, cost in zip(iter_result.path_nodes, iter_result.path_edges, iter_result.costs):
                valid_paths.append((nodes, edges, cost))
                if cost < iter_best_cost:
                    iter_best_cost = cost
                    iter_best_path = (nodes, edges, cost)

            total_expanded += iter_result.nodes_expanded

            if iter_best_cost < best_cost and iter_best_path:
                best_cost = iter_best_cost
                best_nodes = iter_best_path[0]
                best_edges = iter_best_path[1]
                conv_iter = iteration
            elif iter_best_cost == best_cost and valid_paths:
                identical_best_count += 1

            if metrics:
                self._record_iteration_metrics(
                    metrics,
                    iteration,
                    valid_paths,
                    iter_best_cost,
                    int(iter_result.custom_metrics.get("scouts_succeeded", 0)),
                    int(iter_result.custom_metrics.get("actual_scouts", 0)),
                    int(iter_result.custom_metrics.get("recruits_succeeded", 0)),
                    int(iter_result.custom_metrics.get("actual_recruits", 0)),
                    int(iter_result.custom_metrics.get("num_recruiters", 0)),
                    int(iter_result.custom_metrics.get("abandoning", 0)),
                )

        if metrics:
            metrics.num_iterations_run = self.config.max_iterations
            metrics.convergence_iteration = conv_iter
            metrics.best_cost_found = best_cost
            if self.config.max_iterations > 1:
                metrics.route_stability = identical_best_count / (self.config.max_iterations - 1)
            self.metrics_history.append(metrics)

        return best_nodes, best_edges, best_cost, conv_iter, total_expanded

    def initialize_search(self, origin: str, dest: str, context: RoutingContext) -> None:
        """Initializes per-query state."""
        self._current_recruiters: list[_BeePath] = []
        if self.config.elite_route_seeding and self._global_best_edges:
            self._current_recruiters.append(
                (self._global_best_nodes, self._global_best_edges, self._global_best_cost)
            )

    def execute_iteration(
        self, origin: str, dest: str, context: RoutingContext
    ) -> SwarmIterationResult:
        """Executes one single iteration of the BCO algorithm."""
        result = SwarmIterationResult()
        
        iter_paths: list[_BeePath | None] = []
        iter_expanded = 0
        scouts_succeeded = 0
        recruits_succeeded = 0
        actual_scouts = 0
        actual_recruits = 0
        
        num_scouts = max(1, int(self.config.colony_size * self.config.scout_ratio))

        # Forward Pass
        for i in range(self.config.colony_size):
            if i < num_scouts or not getattr(self, "_current_recruiters", []):
                actual_scouts += 1
                path, exp = self._construct_scout_path(origin, dest, context)
                iter_paths.append(path)
                iter_expanded += exp
                if path:
                    scouts_succeeded += 1
            else:
                actual_recruits += 1
                recruiter_path = self._rng.choice(self._current_recruiters)
                path, exp = self._neighborhood_search(
                    recruiter_path, origin, dest, context
                )
                iter_paths.append(path)
                iter_expanded += exp
                if path:
                    recruits_succeeded += 1

        valid_paths = [p for p in iter_paths if p is not None]
        
        # Backward Pass
        self._current_recruiters, abandoning = self._waggle_dance(valid_paths)
        
        # If all bees abandoned (e.g., tough constraints), force the best bee
        # to recruit so the colony doesn't completely lose direction, unless
        # even the best bee failed.
        if not self._current_recruiters and valid_paths:
            best_bee = min(valid_paths, key=lambda p: p[2])
            self._current_recruiters.append(best_bee)

        for p in valid_paths:
            result.path_nodes.append(p[0])
            result.path_edges.append(p[1])
            result.costs.append(p[2])
            
        result.nodes_expanded = iter_expanded
        
        result.custom_metrics["scouts_succeeded"] = float(scouts_succeeded)
        result.custom_metrics["actual_scouts"] = float(actual_scouts)
        result.custom_metrics["recruits_succeeded"] = float(recruits_succeeded)
        result.custom_metrics["actual_recruits"] = float(actual_recruits)
        result.custom_metrics["num_recruiters"] = float(len(self._current_recruiters))
        result.custom_metrics["abandoning"] = float(abandoning)
        
        return result

    # ------------------------------------------------------------------
    # Private: Forward Pass Mechanics
    # ------------------------------------------------------------------

    def _construct_scout_path(
        self, origin: str, dest: str, context: RoutingContext
    ) -> tuple[_BeePath | None, int]:
        """Performs heuristic-guided probabilistic path construction from scratch."""
        return self._random_walk(origin, dest, [origin], [], 0.0, context)

    def _neighborhood_search(
        self,
        recruiter_path: _BeePath,
        origin: str,
        dest: str,
        context: RoutingContext,
    ) -> tuple[_BeePath | None, int]:
        """Follows a prefix of the recruiter's path, then searches randomly.
        
        This models BCO's local exploration/neighborhood search.
        """
        nodes, edges, _ = recruiter_path
        
        # Must diverge at some point before the destination
        if len(nodes) <= 2:
            split_idx = 0
        else:
            # Diverge at any node from the origin up to the node before destination
            split_idx = self._rng.randint(0, len(nodes) - 2)

        prefix_nodes = nodes[: split_idx + 1]
        prefix_edges = edges[:split_idx]
        
        # Calculate the deterministic cost of the prefix
        prefix_cost = 0.0
        net = context.network
        veh = context.vehicle
        for eid in prefix_edges:
            edge = net.edges[eid]
            prefix_cost += context.cost_function(edge, veh, net, context)

        # Start random walk from the split node
        current = prefix_nodes[-1]
        return self._random_walk(
            current, dest, list(prefix_nodes), list(prefix_edges), prefix_cost, context
        )

    def _random_walk(
        self,
        current: str,
        dest: str,
        tabu_nodes: list[str],
        current_edges: list[str],
        current_cost: float,
        context: RoutingContext,
    ) -> tuple[_BeePath | None, int]:
        """Probabilistic step-by-step path construction from current node.
        
        Returns:
            Tuple (BeePath or None, nodes_expanded).
        """
        net = context.network
        veh = context.vehicle
        active_incidents = context.active_incidents
        
        tabu = set(tabu_nodes)
        nodes_expanded = 0

        while current != dest:
            candidates: list[_Candidate] = []
            for edge in net.get_outgoing_edges(current):
                if edge.is_closed or edge.current_speed_limit <= 0.0:
                    continue
                if edge.to_node in tabu:
                    continue
                
                eta = self.scorer.heuristic(edge, veh, net, active_incidents)
                # BCO primarily uses heuristic desirability directly
                attract = eta
                edge_cost = context.cost_function(edge, veh, net, context)
                candidates.append((edge.to_node, edge.id, attract, edge_cost))

            if not candidates:
                return None, nodes_expanded  # Hit a dead-end

            # Roulette wheel selection based on heuristic desirability
            chosen_node, chosen_edge, chosen_cost = self._weighted_choice(candidates)
            
            tabu.add(chosen_node)
            tabu_nodes.append(chosen_node)
            current_edges.append(chosen_edge)
            current_cost += chosen_cost
            current = chosen_node
            nodes_expanded += 1

            if nodes_expanded > len(net.nodes):
                return None, nodes_expanded  # Guard against infinite loops

        return (tabu_nodes, current_edges, current_cost), nodes_expanded

    def _weighted_choice(self, candidates: list[_Candidate]) -> tuple[str, str, float]:
        """Selects a candidate proportionally to its desirability."""
        total_attract = sum(c[2] for c in candidates)
        if total_attract <= 0.0:
            chosen = self._rng.choice(candidates)
            return chosen[0], chosen[1], chosen[3]

        threshold = self._rng.random() * total_attract
        cumulative = 0.0
        for node, edge_id, attract, cost in candidates:
            cumulative += attract
            if cumulative >= threshold:
                return node, edge_id, cost

        # Fallback due to float precision
        last = candidates[-1]
        return last[0], last[1], last[3]

    # ------------------------------------------------------------------
    # Private: Backward Pass Mechanics
    # ------------------------------------------------------------------

    def _waggle_dance(
        self, valid_paths: list[_BeePath]
    ) -> tuple[list[_BeePath], int]:
        """Evaluates paths, computes loyalty probabilities, and recruits.
        
        Returns:
            Tuple (list of loyal recruiters, number of abandoning bees).
        """
        if not valid_paths:
            return [], self.config.colony_size

        c_best = min(p[2] for p in valid_paths)
        c_max = max(p[2] for p in valid_paths)
        
        recruiters: list[_BeePath] = []
        abandoning = 0

        # Phase 1: Determine Loyalty
        for path in valid_paths:
            cost = path[2]
            
            # Equation: p_b = RF * exp(-(C_b - C_best) / (C_max - C_best + 1e-6))
            exponent = -(cost - c_best) / (c_max - c_best + 1e-6)
            p_loyalty = self.config.recruitment_factor * math.exp(exponent)
            
            if p_loyalty < self.config.abandonment_threshold:
                p_loyalty = 0.0  # Force abandonment if below threshold
                
            if self._rng.random() <= p_loyalty:
                recruiters.append(path)
            else:
                abandoning += 1

        # Plus bees that failed to find a valid path are automatically abandoning
        abandoning += self.config.colony_size - len(valid_paths)

        # Note: Roulette wheel selection for the abandoning bees is handled
        # implicitly in the next iteration's forward pass by calling 
        # _rng.choice(recruiters) for recruited bees. This is mathematically
        # equivalent to selecting a recruiter uniformly if their waggle dance
        # duration (number of copies in the pool) is proportional to their quality.
        # Here we enhance the recruiter pool based on quality so choice() models
        # the roulette wheel correctly.
        
        weighted_recruiters: list[_BeePath] = []
        if recruiters:
            # Assign waggle duration proportional to 1/cost
            for r in recruiters:
                # weight = (C_max - C_r) / (C_max - C_best + epsilon) + 0.1
                # Normalise cost to 0-1 range inverted. Best gets 1.1, worst gets 0.1.
                w = ((c_max - r[2]) / (c_max - c_best + 1e-6)) + 0.1
                num_copies = max(1, int(w * 10))
                weighted_recruiters.extend([r] * num_copies)
                
        return weighted_recruiters, abandoning

    # ------------------------------------------------------------------
    # Private: Research Metrics
    # ------------------------------------------------------------------

    def _record_iteration_metrics(
        self,
        metrics: BCOSearchMetrics,
        iteration: int,
        valid_paths: list[_BeePath],
        best_cost: float,
        scouts_succ: int,
        num_scouts: int,
        recruits_succ: int,
        num_recruits: int,
        num_recruiters: int,
        abandoning: int,
    ) -> None:
        """Records diagnostics for a single BCO iteration."""
        avg_cost = best_cost
        diversity = 0.0
        
        if valid_paths:
            avg_cost = sum(p[2] for p in valid_paths) / len(valid_paths)
            unique_paths = len({tuple(p[1]) for p in valid_paths})
            diversity = unique_paths / self.config.colony_size

        scout_rate = scouts_succ / num_scouts if num_scouts > 0 else 0.0
        recruit_rate = recruits_succ / num_recruits if num_recruits > 0 else 0.0
        
        loyalty = num_recruiters / self.config.colony_size
        abandon_rate = abandoning / self.config.colony_size

        metrics.iteration_records.append(
            BCOIterationMetrics(
                iteration=iteration,
                best_cost_in_iteration=best_cost,
                avg_cost_in_iteration=avg_cost,
                scout_success_rate=scout_rate,
                recruitment_effectiveness=recruit_rate,
                colony_diversity=diversity,
                loyalty_distribution=loyalty,
                abandonment_rate=abandon_rate,
            )
        )
