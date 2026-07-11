"""Particle Swarm Optimization (PSO) routing algorithm for EV routing.

Algorithm Reference
-------------------
Adapted from Continuous PSO (Kennedy & Eberhart, 1995) to discrete graphs using
Edge Priority-Based Encoding, inspired by:
Ahn, C. W., et al. (2004). "Modified particle swarm optimization for shortest
path routing problem."

PSO Routing Adaptation
----------------------
Standard PSO uses continuous vectors for position and velocity. Applying this
directly to combinatorial graphs is difficult. We use **Edge Priority-Based
Encoding**:
- Position `X_i` is a sparse continuous vector (mapping edge ID -> priority weight).
- Velocity `V_i` is a sparse continuous vector (mapping edge ID -> velocity).
- **Decoding**: To evaluate a particle's fitness, we decode `X_i` into a valid
  route using a priority-ordered Depth-First Search (DFS). At each node, the
  particle chooses the unvisited neighbor connected by the edge with the highest
  priority in `X_i`. If a dead-end is reached, it backtracks. This guarantees a
  valid, loop-free path is always found if one exists, governed entirely by the
  continuous priorities.
- **Initialization**: Missing edges in `X_i` default to the heuristic desirability
  from the `MultiObjectiveEdgeScorer`.

Dynamic Environment
-------------------
When the environment changes (e.g., road closures), the swarm is NOT reset.
Instead, the fitness of `G_best` and `P_best` paths are re-evaluated. If a path
now contains a closed edge, its fitness becomes infinity. The standard velocity
updates will naturally pull the swarm away from the now-invalid routes towards
better alternatives.
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
from src.utils.config import PSOConfig, RoutingObjectivesConfig

# ---------------------------------------------------------------------------
# Research metrics data structures
# ---------------------------------------------------------------------------


@dataclass
class PSOIterationMetrics:
    """Stores per-iteration diagnostics for one PSO search call."""

    iteration: int
    global_best_cost: float
    avg_particle_cost: float
    # Number of particles that improved their personal best this iteration
    personal_best_improvements: int
    # Fraction of particles whose path differs from the global best
    exploration_ratio: float
    # Variance or average absolute velocity indicating swarm activity
    avg_velocity_magnitude: float
    # Number of unique routes found by the swarm this iteration
    swarm_diversity: float


@dataclass
class PSOSearchMetrics:
    """Aggregate research metrics for a single find_route() call."""

    query_origin: str
    query_destination: str
    num_iterations_run: int
    convergence_iteration: int
    best_cost_found: float
    route_stability: float
    iteration_records: list[PSOIterationMetrics] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Particle Definition
# ---------------------------------------------------------------------------


class Particle:
    """Represents a single swarm agent searching for routes."""

    def __init__(self, id: int) -> None:
        self.id = id

        # Position and Velocity (Sparse vectors of Edge ID -> float)
        self.X: dict[str, float] = {}
        self.V: dict[str, float] = {}

        # Personal Best
        self.p_best_X: dict[str, float] = {}
        self.p_best_path_nodes: list[str] = []
        self.p_best_path_edges: list[str] = []
        self.p_best_cost: float = float("inf")

        # Current state
        self.current_path_nodes: list[str] = []
        self.current_path_edges: list[str] = []
        self.current_cost: float = float("inf")


# ---------------------------------------------------------------------------
# PSO Router
# ---------------------------------------------------------------------------


class PSORouter(Router):
    """Particle Swarm Optimization (PSO) router for dynamic urban networks."""

    def __init__(
        self,
        config: PSOConfig,
        scorer: MultiObjectiveEdgeScorer | None = None,
        seed: int | None = None,
    ) -> None:
        self.config = config
        self.scorer = scorer or MultiObjectiveEdgeScorer(RoutingObjectivesConfig())
        self._rng = random.Random(seed)

        # Persistent Swarm State (Cross-Query Memory)
        self.particles: list[Particle] = [
            Particle(i) for i in range(self.config.swarm_size)
        ]

        self.g_best_X: dict[str, float] = {}
        self.g_best_path_nodes: list[str] = []
        self.g_best_path_edges: list[str] = []
        self.g_best_cost: float = float("inf")

        # If true, forces re-evaluation of g_best and p_best costs before next query
        self._environment_dirty: bool = False
        self._injected_pheromones: dict[str, float] = {}

        # Execution statistics
        self.search_count: int = 0
        self.total_search_time: float = 0.0
        self.total_expanded_nodes: int = 0
        self.metrics_history: list[PSOSearchMetrics] = []

    # ------------------------------------------------------------------
    # Router interface
    # ------------------------------------------------------------------

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds a high-quality route using the PSO algorithm."""
        self.search_count += 1
        start_wall = time.perf_counter()

        self._validate_nodes(origin_node_id, destination_node_id, context)

        if origin_node_id == destination_node_id:
            return self._trivial_result(origin_node_id, start_wall)

        # Re-evaluate cached bests if the environment changed (e.g. closures)
        if self._environment_dirty:
            self._re_evaluate_bests(context)
            self._environment_dirty = False

        best_nodes, best_edges, best_cost, conv_iter, total_expanded = (
            self._run_pso_iterations(origin_node_id, destination_node_id, context)
        )

        if not best_nodes or best_cost == float("inf"):
            raise NoPathFoundError(
                f"PSO could not find a path from '{origin_node_id}' to "
                f"'{destination_node_id}'."
            )

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
        """Flags the environment as dirty.

        PSO handles dynamic changes by re-evaluating the fitness of previously
        discovered personal and global best paths. If they are now invalid or
        expensive, the swarm naturally adapts via velocity updates.
        """
        self._environment_dirty = True

    def reset(self) -> None:
        """Resets the entire swarm state and statistics."""
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0
        self.metrics_history.clear()

        self.particles = [Particle(i) for i in range(self.config.swarm_size)]
        self.g_best_X = {}
        self.g_best_path_nodes = []
        self.g_best_path_edges = []
        self.g_best_cost = float("inf")
        self._environment_dirty = False

    def get_statistics(self) -> dict[str, Any]:
        """Returns cumulative execution statistics."""
        return {
            "algorithm": "PSO",
            "search_count": self.search_count,
            "total_search_time_s": self.total_search_time,
            "avg_search_time_s": (
                self.total_search_time / self.search_count
                if self.search_count > 0
                else 0.0
            ),
            "total_expanded_nodes": self.total_expanded_nodes,
            "global_best_cost": self.g_best_cost,
            "metrics_records": len(self.metrics_history),
        }

    def get_pheromone_matrix(self) -> dict[str, float] | None:
        return None

    def inject_pheromone_matrix(self, matrix: dict[str, float]) -> None:
        self._injected_pheromones = matrix

    def inject_global_best(
        self, path_nodes: list[str], path_edges: list[str], cost: float
    ) -> None:
        if path_edges and cost < self.g_best_cost:
            self.g_best_cost = cost
            self.g_best_path_nodes = list(path_nodes)
            self.g_best_path_edges = list(path_edges)
            # Create synthetic priorities for the injected path
            max_p = max(self.g_best_X.values()) if self.g_best_X else 1.0
            for edge in path_edges:
                self.g_best_X[edge] = max_p + 1.0

    def initialize_search(
        self, origin: str, dest: str, context: RoutingContext
    ) -> None:
        self._injected_pheromones = {}
        if self._environment_dirty:
            self._re_evaluate_bests(context)
            self._environment_dirty = False

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

    def _re_evaluate_bests(self, context: RoutingContext) -> None:
        """Re-evaluates the cost of G_best and all P_bests."""
        # Re-evaluate G_best
        if self.g_best_path_edges:
            self.g_best_cost = self._calculate_path_cost(
                self.g_best_path_edges, context
            )

        # Re-evaluate P_bests
        for p in self.particles:
            if p.p_best_path_edges:
                p.p_best_cost = self._calculate_path_cost(p.p_best_path_edges, context)

    def _calculate_path_cost(
        self, path_edges: list[str], context: RoutingContext
    ) -> float:
        """Calculates total cost of a path, returning infinity if invalid."""
        cost = 0.0
        net = context.network
        veh = context.vehicle
        for eid in path_edges:
            if eid not in net.edges:
                return float("inf")
            edge = net.edges[eid]
            if edge.is_closed or edge.current_speed_limit <= 0.0:
                return float("inf")
            cost += context.cost_function(edge, veh, net, context)
        return cost

    def _run_pso_iterations(
        self, origin: str, dest: str, context: RoutingContext
    ) -> tuple[list[str], list[str], float, int, int]:
        """Main PSO loop running particle evaluations and continuous updates."""
        metrics: PSOSearchMetrics | None = None
        if self.config.collect_metrics:
            metrics = PSOSearchMetrics(
                query_origin=origin,
                query_destination=dest,
                num_iterations_run=0,
                convergence_iteration=0,
                best_cost_found=float("inf"),
                route_stability=0.0,
            )

        conv_iter = 0
        total_expanded = 0
        identical_best_count = 0
        query_best_cost = float("inf")

        self.initialize_search(origin, dest, context)

        for iteration in range(self.config.max_iterations):
            iter_result = self.execute_iteration(origin, dest, context)

            total_expanded += iter_result.nodes_expanded
            pbest_improvements = int(
                iter_result.custom_metrics.get("pbest_improvements", 0.0)
            )

            if self.g_best_cost < query_best_cost:
                query_best_cost = self.g_best_cost
                conv_iter = iteration
            elif self.g_best_cost == query_best_cost and self.g_best_cost < float(
                "inf"
            ):
                identical_best_count += 1

            if metrics:
                self._record_iteration_metrics(metrics, iteration, pbest_improvements)

        if metrics:
            metrics.num_iterations_run = self.config.max_iterations
            metrics.convergence_iteration = conv_iter
            metrics.best_cost_found = self.g_best_cost
            if self.config.max_iterations > 1:
                metrics.route_stability = identical_best_count / (
                    self.config.max_iterations - 1
                )
            self.metrics_history.append(metrics)

        return (
            list(self.g_best_path_nodes),
            list(self.g_best_path_edges),
            self.g_best_cost,
            conv_iter,
            total_expanded,
        )

    def execute_iteration(
        self, origin: str, dest: str, context: RoutingContext
    ) -> SwarmIterationResult:
        result = SwarmIterationResult()
        pbest_improvements = 0
        iter_expanded = 0

        for p in self.particles:
            nodes, edges, cost, exp = self._decode_path(origin, dest, p.X, context)
            iter_expanded += exp

            p.current_path_nodes = nodes
            p.current_path_edges = edges
            p.current_cost = cost

            if cost < p.p_best_cost:
                p.p_best_cost = cost
                p.p_best_path_nodes = list(nodes)
                p.p_best_path_edges = list(edges)
                p.p_best_X = p.X.copy()
                pbest_improvements += 1

            if cost < self.g_best_cost:
                self.g_best_cost = cost
                self.g_best_path_nodes = list(nodes)
                self.g_best_path_edges = list(edges)
                self.g_best_X = p.X.copy()

            if nodes:
                result.path_nodes.append(nodes)
                result.path_edges.append(edges)
                result.costs.append(cost)

        result.nodes_expanded = iter_expanded
        result.custom_metrics["pbest_improvements"] = float(pbest_improvements)

        self._update_particles(context)

        return result

    # ------------------------------------------------------------------
    # Private: Edge Priority-Based Encoding / Decoding
    # ------------------------------------------------------------------

    def _decode_path(
        self, origin: str, dest: str, X_i: dict[str, float], context: RoutingContext
    ) -> tuple[list[str], list[str], float, int]:
        """Decodes the continuous priority vector X_i into a combinatorial path.

        Uses a priority-ordered Depth-First Search with backtracking to guarantee
        a valid path is found if one exists.

        Returns:
            Tuple containing (path_nodes, path_edges, total_cost, nodes_expanded).
        """
        net = context.network
        veh = context.vehicle
        incidents = context.active_incidents

        # Stack elements: (current_node, list_of_untried_edges)
        stack: list[tuple[str, list[Any]]] = []
        path_nodes: list[str] = [origin]
        path_edges: list[str] = []
        path_costs: list[float] = []
        path_nodes_set: set[str] = {origin}
        total_cost: float = 0.0
        nodes_expanded: int = 0
        max_expansions: int = 2000

        def get_sorted_edges(node: str) -> list[Any]:
            edges = []
            from_edge = path_edges[-1] if path_edges else None
            for e in net.get_outgoing_edges(node, from_edge):
                if e.is_closed or e.current_speed_limit <= 0.0:
                    continue
                if e.to_node in path_nodes_set:
                    continue
                edges.append(e)

            # Sort descending by priority. If edge not in X_i, initialize with heuristic + noise.
            def get_priority(e: Any) -> float:
                if e.id not in X_i:
                    base = self.scorer.heuristic(e, veh, net, incidents)
                    if dest:
                        to_node_obj = net.nodes.get(e.to_node)
                        dest_node_obj = net.nodes.get(dest)
                        if to_node_obj and dest_node_obj:
                            dx = to_node_obj.x - dest_node_obj.x
                            dy = to_node_obj.y - dest_node_obj.y
                            dist_to_dest = (dx * dx + dy * dy) ** 0.5
                            base = base * math.exp(-dist_to_dest / 80.0)
                    # Pheromone biasing
                    if getattr(self, "_injected_pheromones", None):
                        tau = self._injected_pheromones.get(e.id, 0.0)
                        base += tau * 10.0  # Scale pheromone influence

                    # Add +/- 10% noise for initial swarm diversity
                    X_i[e.id] = base * (1.0 + self._rng.uniform(-0.1, 0.1))
                return X_i[e.id]

            edges.sort(key=get_priority, reverse=True)
            return edges

        stack.append((origin, get_sorted_edges(origin)))

        while stack:
            if nodes_expanded > max_expansions:
                break  # Safety cutoff to prevent infinite backtracking loops in DFS

            current_node, untried_edges = stack[-1]

            if current_node == dest:
                return path_nodes, path_edges, total_cost, nodes_expanded

            if not untried_edges:
                # Dead end reached. Backtrack.
                stack.pop()
                if not stack:
                    break  # Completely exhausted search space

                popped_node = path_nodes.pop()
                popped_edge = path_edges.pop()
                path_nodes_set.remove(popped_node)
                total_cost -= path_costs.pop()
                continue

            # Try the highest priority untried edge
            next_edge = untried_edges.pop(0)
            next_node = next_edge.to_node

            edge_cost = context.cost_function(next_edge, veh, net, context)

            path_nodes.append(next_node)
            path_edges.append(next_edge.id)
            path_costs.append(edge_cost)
            path_nodes_set.add(next_node)
            total_cost += edge_cost
            nodes_expanded += 1

            # Push new state to stack
            stack.append((next_node, get_sorted_edges(next_node)))

        # No path found
        return [], [], float("inf"), nodes_expanded

    def _update_particles(self, context: RoutingContext) -> None:
        """Applies PSO continuous velocity and position updates.

        V_{t+1} = w*V_t + c1*r1*(Pbest - X) + c2*r2*(Gbest - X)
        X_{t+1} = X_t + V_{t+1}
        """
        w = self.config.inertia_weight
        c1 = self.config.cognitive_weight
        c2 = self.config.social_weight
        v_max = self.config.v_max
        net = context.network
        veh = context.vehicle
        incidents = context.active_incidents

        for p in self.particles:
            r1 = self._rng.random()
            r2 = self._rng.random()

            # We only need to update dimensions (edges) that are actively
            # represented in X, P_best, or G_best to maintain sparsity.
            active_edges = (
                set(p.X.keys()).union(p.p_best_X.keys()).union(self.g_best_X.keys())
            )

            for edge in active_edges:
                v_current = p.V.get(edge, 0.0)

                # Assume heuristic desirability if uninitialized
                if edge in p.X:
                    x_current = p.X[edge]
                elif edge in net.edges:
                    x_current = self.scorer.heuristic(
                        net.edges[edge], veh, net, incidents
                    )
                else:
                    x_current = 0.0

                # If an edge is missing from p_best or g_best, we assume its
                # default heuristic value, rather than 0.0, to prevent artificial drag
                if edge in p.p_best_X:
                    p_best_val = p.p_best_X[edge]
                else:
                    p_best_val = (
                        self.scorer.heuristic(net.edges[edge], veh, net, incidents)
                        if edge in net.edges
                        else 0.0
                    )

                if edge in self.g_best_X:
                    g_best_val = self.g_best_X[edge]
                else:
                    g_best_val = (
                        self.scorer.heuristic(net.edges[edge], veh, net, incidents)
                        if edge in net.edges
                        else 0.0
                    )

                # Velocity Update
                v_new = (
                    w * v_current
                    + c1 * r1 * (p_best_val - x_current)
                    + c2 * r2 * (g_best_val - x_current)
                )

                # Clamping
                if v_new > v_max:
                    v_new = v_max
                elif v_new < -v_max:
                    v_new = -v_max

                p.V[edge] = v_new
                p.X[edge] = x_current + v_new

    # ------------------------------------------------------------------
    # Private: Research Metrics
    # ------------------------------------------------------------------

    def _record_iteration_metrics(
        self,
        metrics: PSOSearchMetrics,
        iteration: int,
        pbest_improvements: int,
    ) -> None:
        """Records diagnostics for a single PSO iteration."""
        valid_paths = [p for p in self.particles if p.current_cost < float("inf")]

        avg_cost = float("inf")
        diversity = 0.0
        avg_vel = 0.0
        exploration = 0.0

        if valid_paths:
            avg_cost = sum(p.current_cost for p in valid_paths) / len(valid_paths)
            unique_paths = len({tuple(p.current_path_edges) for p in valid_paths})
            diversity = unique_paths / self.config.swarm_size

            # Calculate exploration ratio: fraction of particles not following G_best exactly
            if self.g_best_path_edges:
                g_best_tuple = tuple(self.g_best_path_edges)
                exploring = sum(
                    1
                    for p in valid_paths
                    if tuple(p.current_path_edges) != g_best_tuple
                )
                exploration = exploring / len(valid_paths)

        # Average velocity magnitude across all particles and their active dimensions
        total_vel = 0.0
        total_dims = 0
        for p in self.particles:
            for v in p.V.values():
                total_vel += abs(v)
                total_dims += 1

        if total_dims > 0:
            avg_vel = total_vel / total_dims

        metrics.iteration_records.append(
            PSOIterationMetrics(
                iteration=iteration,
                global_best_cost=self.g_best_cost,
                avg_particle_cost=avg_cost,
                personal_best_improvements=pbest_improvements,
                exploration_ratio=exploration,
                avg_velocity_magnitude=avg_vel,
                swarm_diversity=diversity,
            )
        )
