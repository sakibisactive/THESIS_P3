"""Ant Colony System (ACS) routing algorithm for dynamic EV urban routing.

Algorithm Reference
-------------------
Dorigo, M. & Gambardella, L.M. (1997).
Ant Colony System: A Cooperative Learning Approach to the Travelling
Salesman Problem.
IEEE Transactions on Evolutionary Computation, 1(1), 53–66.
https://doi.org/10.1109/4235.585892

ACS Variant Description
-----------------------
We implement the **Ant Colony System (ACS)** variant rather than the
simpler Ant System (AS) for three reasons:

1.  *Pseudo-random Proportional Rule* (§III-A in the paper):
    The state transition rule uses an exploitation threshold q0::

        if q <= q0:   # Exploitation
            s* = argmax_{u in N_k(r)} [ tau(r,u)^alpha * eta(r,u)^beta ]
        else:          # Probabilistic exploration
            s ~ p_k(r, s)

    This balances convergence speed with solution diversity.

2.  *Local Pheromone Update* (§III-C):
    After each ant k traverses edge (r, s), it immediately applies::

        tau(r, s) <- (1 - xi) * tau(r, s) + xi * tau_0

    This reduces pheromone on recently visited edges, encouraging
    subsequent ants in the same iteration to explore alternatives.

3.  *Global Pheromone Update* (§III-B):
    Only the global-best ant deposits pheromones at the end of each
    iteration::

        tau(r, s) <- (1 - rho) * tau(r, s) + rho * Delta_tau_best
        where Delta_tau_best = Q / C_best  (C_best = best path cost)

Probabilistic Transition Formula
---------------------------------
For the exploration branch::

    p_k(r, s) = [tau(r,s)^alpha * eta(r,s)^beta] /
                sum_{u in N_k(r)} [tau(r,u)^alpha * eta(r,u)^beta]

where N_k(r) is the set of unvisited (not-tabu) neighbours of r.

Key Deviations from the Original Paper
---------------------------------------
1.  **Dynamic environment**: The original ACS targets the static TSP.
    We extend it to a dynamic directed routing graph where edge costs and
    closures change over time.  The pheromone matrix is kept persistent
    across routing queries so that learned knowledge accumulates.

2.  **Lazy Temporal Evaporation**: Global evaporation is applied lazily
    when context.current_time advances by >= evaporation_dt, instead of
    running it every ACS iteration.  This ensures pheromones decay at a
    realistic simulation rate even when queries are infrequent.

3.  **Closed Edge Handling**: Ants skip edges marked is_closed or with
    zero speed limit.  No explicit pheromone reset is performed; instead,
    natural evaporation reduces pheromone on inaccessible edges over time.

4.  **Configurable Pheromone Bounds** (tau_min, tau_max): Borrowed from the
    MAX-MIN Ant System (Stützle & Hoos, 2000) to prevent premature
    stagnation and maintain exploration.

5.  **Multi-Objective Heuristic**: eta(e) is computed by the injected
    MultiObjectiveEdgeScorer rather than the single 1/distance used in
    the original TSP context.  This allows EV-aware routing without
    modifying the core algorithm.

Computational Complexity
------------------------
Per call to find_route():
    * Pheromone evaporation: O(|E|) where |E| = number of network edges.
    * Ant construction: O(I * K * |V|) where I = max_iterations,
      K = num_ants, |V| = reachable nodes (tabu list lookups O(1) with set).
    * Global update: O(|E_best|) where |E_best| = edges in best path.
    * Total: O(I * K * |V| + |E|) per query.

Convergence Assumption
----------------------
ACS is guaranteed to converge to the global optimum in probability
for static graphs with sufficient iterations (Stützle & Dorigo, 1999).
For dynamic graphs, convergence is not formally guaranteed but empirical
studies show high-quality solutions within tens of iterations.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.graph_utils import reconstruct_path
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult
from src.routing.scorer import MultiObjectiveEdgeScorer
from src.utils.config import ACOConfig, RoutingObjectivesConfig

# ---------------------------------------------------------------------------
# Research metrics data structures
# ---------------------------------------------------------------------------


@dataclass
class ACOIterationMetrics:
    """Stores per-iteration diagnostics for one ACS search call.

    Only populated when ACOConfig.collect_metrics is True.
    """

    iteration: int
    best_cost_in_iteration: float
    avg_cost_in_iteration: float
    # Fraction of ants that exploited (q <= q0) in this iteration
    exploitation_ratio: float
    # Mean pheromone on edges traversed by best ant in this iteration
    mean_pheromone_on_best_path: float


@dataclass
class ACOSearchMetrics:
    """Aggregate research metrics for a single find_route() call."""

    query_origin: str
    query_destination: str
    num_iterations_run: int
    # Iteration index at which the globally best solution was last improved
    convergence_iteration: int
    best_cost_found: float
    # Per-iteration diagnostic records
    iteration_records: list[ACOIterationMetrics] = field(default_factory=list)
    # Summary pheromone statistics after the search
    pheromone_min: float = 0.0
    pheromone_max: float = 0.0
    pheromone_mean: float = 0.0
    pheromone_std: float = 0.0


# Internal tuple type for candidate edges during ant construction
# (to_node_id, edge_id, attractiveness, edge_cost)
_Candidate = tuple[str, str, float, float]

# Internal return type for _construct_solution
# (path_nodes, path_edges, total_cost, exploit_count, nodes_visited)
_AntResult = tuple[list[str], list[str], float, int, int]


# ---------------------------------------------------------------------------
# ACO Router
# ---------------------------------------------------------------------------


class ACORouter(Router):
    """Ant Colony System (ACS) router for dynamic EV urban traffic networks.

    State
    -----
    pheromones : dict[str, float]
        Persistent pheromone matrix keyed by edge ID.  Values are
        initialised to tau_0 on first access and persist across queries.
    last_evaporation_time : float
        Simulation timestamp of the most recent global evaporation step.

    The router is intentionally stateful; persistent pheromones allow
    the algorithm to accumulate learned routing knowledge over time and
    respond naturally to environmental changes without catastrophic
    forgetting.
    """

    def __init__(
        self,
        config: ACOConfig,
        scorer: MultiObjectiveEdgeScorer | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialises the ACS router.

        Args:
            config: Full ACS hyperparameter configuration.
            scorer: Optional pre-built MultiObjectiveEdgeScorer. If None,
                a default scorer (equal-weight objectives) is constructed
                internally.  Inject a shared scorer instance so that BCO,
                PSO, and E3-Hybrid can reuse the same scoring function.
            seed: Optional random seed for fully reproducible execution.
                Using the same seed and config guarantees identical output.
        """
        self.config = config
        self.scorer = scorer or MultiObjectiveEdgeScorer(
            RoutingObjectivesConfig()
        )
        self._rng = random.Random(seed)

        # Persistent pheromone state – keyed by edge.id
        self.pheromones: dict[str, float] = {}
        self.last_evaporation_time: float = 0.0

        # Execution statistics
        self.search_count: int = 0
        self.total_search_time: float = 0.0
        self.total_expanded_nodes: int = 0

        # Best route ever found (across all queries)
        self._global_best_cost: float = float("inf")
        self._global_best_edges: list[str] = []

        # Research metrics history (populated when collect_metrics=True)
        self.metrics_history: list[ACOSearchMetrics] = []

    # ------------------------------------------------------------------
    # Router interface
    # ------------------------------------------------------------------

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds a high-quality route using the ACS algorithm.

        Executes up to config.max_iterations iterations, each deploying
        config.num_ants ants from origin to destination.  The global best
        path found across all iterations is returned.

        Args:
            origin_node_id: ID of the starting node.
            destination_node_id: ID of the target node.
            context: RoutingContext containing network, vehicle, time, and
                cost function. context.current_time drives lazy evaporation.

        Returns:
            RoutingResult: Best path found across all iterations.

        Raises:
            InvalidNodeError: If node IDs are absent from the network.
            NoPathFoundError: If no ant can reach the destination.
        """
        self.search_count += 1
        start_wall = time.perf_counter()

        self._validate_nodes(origin_node_id, destination_node_id, context)

        if origin_node_id == destination_node_id:
            return self._trivial_result(origin_node_id, start_wall)

        self._apply_lazy_evaporation(context.current_time)
        self._initialise_pheromones(context.network)

        best_nodes, best_edges, best_cost, conv_iter, total_expanded = (
            self._run_acs_iterations(
                origin_node_id, destination_node_id, context
            )
        )

        if not best_nodes:
            raise NoPathFoundError(
                f"No ant path found from '{origin_node_id}' to "
                f"'{destination_node_id}'."
            )

        if best_cost < self._global_best_cost:
            self._global_best_cost = best_cost
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
        """Handles dynamic network changes without resetting pheromones.

        If network_update is a single edge ID (str) or list of edge IDs,
        the pheromone on those edges is reduced by one local evaporation
        step to accelerate adaptation to the change.

        Args:
            network_update: Single edge ID string, list of edge IDs, or
                any arbitrary network state object (ignored if not str/list).
        """
        edge_ids: list[str] = []
        if isinstance(network_update, str):
            edge_ids = [network_update]
        elif isinstance(network_update, list):
            edge_ids = [e for e in network_update if isinstance(e, str)]

        xi = self.config.local_evaporation_rate
        tau_0 = self.config.initial_pheromone
        for eid in edge_ids:
            if eid in self.pheromones:
                self.pheromones[eid] = self._clamp(
                    (1.0 - xi) * self.pheromones[eid] + xi * tau_0
                )

    def reset(self) -> None:
        """Resets all pheromones and execution statistics.

        Should only be called when beginning a new independent experiment.
        """
        self.pheromones.clear()
        self.last_evaporation_time = 0.0
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0
        self._global_best_cost = float("inf")
        self._global_best_edges = []
        self.metrics_history.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Returns cumulative execution and pheromone distribution statistics.

        Returns:
            dict: Telemetry including search counts, timing, pheromone
                distribution, and number of research metric records.
        """
        ph_vals = list(self.pheromones.values())
        ph_mean = sum(ph_vals) / len(ph_vals) if ph_vals else 0.0
        ph_min = min(ph_vals) if ph_vals else 0.0
        ph_max = max(ph_vals) if ph_vals else 0.0

        return {
            "algorithm": "ACS",
            "search_count": self.search_count,
            "total_search_time_s": self.total_search_time,
            "avg_search_time_s": (
                self.total_search_time / self.search_count
                if self.search_count > 0 else 0.0
            ),
            "total_expanded_nodes": self.total_expanded_nodes,
            "num_pheromone_edges": len(self.pheromones),
            "pheromone_min": ph_min,
            "pheromone_max": ph_max,
            "pheromone_mean": ph_mean,
            "global_best_cost": self._global_best_cost,
            "metrics_records": len(self.metrics_history),
        }

    def get_pheromone(self, edge_id: str) -> float:
        """Returns the current pheromone concentration on an edge.

        Args:
            edge_id: The edge identifier.

        Returns:
            float: Current pheromone, or tau_0 if the edge has not yet
                been visited.
        """
        return self.pheromones.get(edge_id, self.config.initial_pheromone)

    # ------------------------------------------------------------------
    # Private: search orchestration
    # ------------------------------------------------------------------

    def _validate_nodes(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> None:
        """Raises InvalidNodeError if either node is missing from the network."""
        if origin_node_id not in context.network.nodes:
            raise InvalidNodeError(
                f"Origin node '{origin_node_id}' not found in network."
            )
        if destination_node_id not in context.network.nodes:
            raise InvalidNodeError(
                f"Destination node '{destination_node_id}' not found."
            )

    def _trivial_result(
        self, node_id: str, start_wall: float
    ) -> RoutingResult:
        """Returns a zero-cost RoutingResult for origin == destination."""
        elapsed = time.perf_counter() - start_wall
        self.total_search_time += elapsed
        return RoutingResult(
            path_nodes=[node_id],
            path_edges=[],
            total_cost=0.0,
            expanded_nodes=0,
            search_time_s=elapsed,
        )

    def _run_acs_iterations(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> tuple[list[str], list[str], float, int, int]:
        """Executes the full ACS iteration loop.

        Returns:
            Tuple of (best_nodes, best_edges, best_cost,
            convergence_iteration, total_nodes_expanded).
        """
        search_metrics: ACOSearchMetrics | None = None
        if self.config.collect_metrics:
            search_metrics = ACOSearchMetrics(
                query_origin=origin_node_id,
                query_destination=destination_node_id,
                num_iterations_run=0,
                convergence_iteration=0,
                best_cost_found=float("inf"),
            )

        best_cost = float("inf")
        best_nodes: list[str] = []
        best_edges: list[str] = []
        convergence_iter = 0
        total_expanded = 0

        for iteration in range(self.config.max_iterations):
            iter_result = self._run_single_iteration(
                origin_node_id, destination_node_id, context
            )
            iter_nodes, iter_edges, iter_cost, exploits, expanded = iter_result
            total_expanded += expanded

            if iter_cost < best_cost:
                best_cost = iter_cost
                best_nodes = iter_nodes
                best_edges = iter_edges
                convergence_iter = iteration

            if best_edges:
                self._global_pheromone_update(best_edges, best_cost)

            if search_metrics is not None and best_edges:
                self._record_iteration_metrics(
                    search_metrics, iteration, iter_cost, exploits, best_edges
                )

        if search_metrics is not None:
            self._finalise_search_metrics(
                search_metrics, convergence_iter, best_cost
            )

        return best_nodes, best_edges, best_cost, convergence_iter, total_expanded

    def _run_single_iteration(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> tuple[list[str], list[str], float, int, int]:
        """Deploys all ants for one iteration and returns the best result.

        Returns:
            Tuple of (best_nodes, best_edges, best_cost,
            total_exploits, total_nodes_expanded).
        """
        best_cost = float("inf")
        best_nodes: list[str] = []
        best_edges: list[str] = []
        total_exploits = 0
        total_expanded = 0

        for _ in range(self.config.num_ants):
            ant = self._construct_solution(
                origin_node_id, destination_node_id, context
            )
            if ant is None:
                continue
            a_nodes, a_edges, a_cost, exploits, expanded = ant
            total_exploits += exploits
            total_expanded += expanded
            if a_cost < best_cost:
                best_cost = a_cost
                best_nodes = a_nodes
                best_edges = a_edges

        return best_nodes, best_edges, best_cost, total_exploits, total_expanded

    # ------------------------------------------------------------------
    # Private: ACS mechanics
    # ------------------------------------------------------------------

    def _construct_solution(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> _AntResult | None:
        """Constructs one ant's solution using the ACS transition rule.

        Returns:
            Tuple (path_nodes, path_edges, total_cost, exploit_count,
            nodes_visited) or None if the ant cannot reach the destination.
        """
        network = context.network
        vehicle = context.vehicle
        active_incidents = context.active_incidents

        current = origin_node_id
        tabu: set[str] = {current}
        parent: dict[str, tuple[str, str]] = {}
        total_cost = 0.0
        exploit_count = 0
        nodes_visited = 0

        while current != destination_node_id:
            candidates = self._build_candidates(
                current, context, vehicle, network, active_incidents, tabu
            )
            if not candidates:
                return None

            chosen_node, chosen_edge_id, chosen_cost, exploited = (
                self._apply_transition_rule(candidates)
            )
            exploit_count += exploited

            self._local_pheromone_update(chosen_edge_id)
            parent[chosen_node] = (current, chosen_edge_id)
            total_cost += chosen_cost
            tabu.add(chosen_node)
            current = chosen_node
            nodes_visited += 1

            if nodes_visited > len(network.nodes) + 1:
                return None  # Safety guard against infinite loops

        path_nodes, path_edges = reconstruct_path(
            origin_node_id, destination_node_id, parent
        )
        return path_nodes, path_edges, total_cost, exploit_count, nodes_visited

    def _build_candidates(
        self,
        current: str,
        context: RoutingContext,
        vehicle: Any,
        network: Any,
        active_incidents: list[object],
        tabu: set[str],
    ) -> list[_Candidate]:
        """Builds the list of feasible candidate edges from the current node."""
        candidates: list[_Candidate] = []
        for edge in network.get_outgoing_edges(current):
            if edge.is_closed or edge.current_speed_limit <= 0.0:
                continue
            if edge.to_node in tabu:
                continue
            tau = self.pheromones.get(edge.id, self.config.initial_pheromone)
            eta = self.scorer.heuristic(
                edge, vehicle, network, active_incidents
            )
            attract = MultiObjectiveEdgeScorer.pheromone_heuristic(
                tau, eta, self.config.alpha, self.config.beta
            )
            edge_cost = context.cost_function(
                edge, vehicle, network, context
            )
            candidates.append((edge.to_node, edge.id, attract, edge_cost))
        return candidates

    def _apply_transition_rule(
        self, candidates: list[_Candidate]
    ) -> tuple[str, str, float, int]:
        """Applies the ACS pseudo-random proportional transition rule.

        Returns:
            Tuple (chosen_node, chosen_edge_id, edge_cost, exploited)
            where exploited is 1 if the exploitation branch was taken, 0 otherwise.
        """
        q = self._rng.random()
        if q <= self.config.q_zero:
            # Exploitation: argmax attractiveness
            best = max(candidates, key=lambda c: c[2])
            return best[0], best[1], best[3], 1
        # Probabilistic exploration via roulette wheel
        node, edge_id, cost = self._weighted_random_choice(candidates)
        return node, edge_id, cost, 0

    def _weighted_random_choice(
        self, candidates: list[_Candidate]
    ) -> tuple[str, str, float]:
        """Roulette-wheel selection proportional to attractiveness.

        Args:
            candidates: List of (to_node, edge_id, attractiveness, cost).

        Returns:
            Tuple of (chosen_node_id, chosen_edge_id, edge_cost).
        """
        total_attract = sum(c[2] for c in candidates)
        if total_attract <= 0.0:
            chosen = self._rng.choice(candidates)
            return chosen[0], chosen[1], chosen[3]

        threshold = self._rng.random() * total_attract
        cumulative = 0.0
        for node_id, edge_id, attract, cost in candidates:
            cumulative += attract
            if cumulative >= threshold:
                return node_id, edge_id, cost

        last = candidates[-1]
        return last[0], last[1], last[3]

    def _local_pheromone_update(self, edge_id: str) -> None:
        """Applies the ACS local pheromone update (Eq. 4 in Dorigo 1997).

        Local update rule::

            tau(r, s) <- (1 - xi) * tau(r, s) + xi * tau_0

        Reduces pheromone on recently traversed edges, encouraging
        subsequent ants in the same iteration to explore alternatives.
        """
        xi = self.config.local_evaporation_rate
        tau_0 = self.config.initial_pheromone
        tau_old = self.pheromones.get(edge_id, tau_0)
        self.pheromones[edge_id] = self._clamp(
            (1.0 - xi) * tau_old + xi * tau_0
        )

    def _global_pheromone_update(
        self, best_edges: list[str], best_cost: float
    ) -> None:
        """Applies the ACS global pheromone update (Eq. 3 in Dorigo 1997).

        Global update rule applied to edges on the best path::

            tau(r, s) <- (1 - rho) * tau(r, s) + rho * Delta_tau_best
            Delta_tau_best = Q / C_best

        Only edges on the best path receive positive reinforcement.
        """
        if best_cost <= 0.0 or not best_edges:
            return
        rho = self.config.evaporation_rate
        delta = self.config.q / best_cost
        for eid in best_edges:
            tau_old = self.pheromones.get(eid, self.config.initial_pheromone)
            self.pheromones[eid] = self._clamp(
                (1.0 - rho) * tau_old + rho * delta
            )

    def _apply_lazy_evaporation(self, current_time: float) -> None:
        """Decays all pheromones when simulation time has advanced.

        Compounded evaporation for n elapsed steps::

            tau <- tau * (1 - rho)^n

        Only applied when current_time - last_evaporation_time >= evaporation_dt.
        """
        dt = self.config.evaporation_dt
        elapsed = current_time - self.last_evaporation_time
        n_steps = int(elapsed / dt)
        if n_steps == 0:
            return
        decay = (1.0 - self.config.evaporation_rate) ** n_steps
        for eid in list(self.pheromones):
            self.pheromones[eid] = self._clamp(self.pheromones[eid] * decay)
        self.last_evaporation_time += n_steps * dt

    def _initialise_pheromones(self, network: Any) -> None:
        """Ensures every network edge has a pheromone entry (tau_0 default)."""
        tau_0 = self.config.initial_pheromone
        for edge_id in network.edges:
            if edge_id not in self.pheromones:
                self.pheromones[edge_id] = tau_0

    def _clamp(self, value: float) -> float:
        """Clamps value to [tau_min, tau_max]."""
        return max(
            self.config.min_pheromone,
            min(self.config.max_pheromone, value),
        )

    def _mean_pheromone(self, edge_ids: list[str]) -> float:
        """Returns mean pheromone concentration over the given edges."""
        if not edge_ids:
            return 0.0
        total = sum(
            self.pheromones.get(eid, self.config.initial_pheromone)
            for eid in edge_ids
        )
        return total / len(edge_ids)

    # ------------------------------------------------------------------
    # Private: research metrics helpers
    # ------------------------------------------------------------------

    def _record_iteration_metrics(
        self,
        search_metrics: ACOSearchMetrics,
        iteration: int,
        iter_best_cost: float,
        exploits: int,
        best_edges: list[str],
    ) -> None:
        """Appends one iteration diagnostic record to search_metrics."""
        records = search_metrics.iteration_records
        # avg cost from the previous iteration record, or use current best
        avg_cost = (
            records[-1].avg_cost_in_iteration if records else iter_best_cost
        )
        exploitation_ratio = exploits / max(1, self.config.num_ants)
        mean_ph = self._mean_pheromone(best_edges)
        search_metrics.iteration_records.append(
            ACOIterationMetrics(
                iteration=iteration,
                best_cost_in_iteration=iter_best_cost,
                avg_cost_in_iteration=avg_cost,
                exploitation_ratio=exploitation_ratio,
                mean_pheromone_on_best_path=mean_ph,
            )
        )

    def _finalise_search_metrics(
        self,
        search_metrics: ACOSearchMetrics,
        convergence_iter: int,
        best_cost: float,
    ) -> None:
        """Populates aggregate statistics and appends to metrics_history."""
        search_metrics.num_iterations_run = self.config.max_iterations
        search_metrics.convergence_iteration = convergence_iter
        search_metrics.best_cost_found = best_cost

        ph_vals = list(self.pheromones.values())
        if ph_vals:
            search_metrics.pheromone_min = min(ph_vals)
            search_metrics.pheromone_max = max(ph_vals)
            mean = sum(ph_vals) / len(ph_vals)
            search_metrics.pheromone_mean = mean
            variance = sum((v - mean) ** 2 for v in ph_vals) / len(ph_vals)
            search_metrics.pheromone_std = math.sqrt(variance)

        self.metrics_history.append(search_metrics)
