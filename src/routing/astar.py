"""A* heuristic search routing algorithm implementation."""

import heapq
import time
from typing import Any

from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.graph_utils import reconstruct_path
from src.routing.heuristic import HeuristicFunction, ZeroHeuristic
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult


class AStarRouter(Router):
    """Implementation of A* heuristic search algorithm.

    Prunes the search space using heuristic estimates of remaining cost.
    Requires an admissible heuristic to guarantee optimality.
    """

    def __init__(self, heuristic: HeuristicFunction | None = None) -> None:
        """Initializes A* router with a pluggable heuristic strategy.

        Args:
            heuristic: The heuristic function. Defaults to ZeroHeuristic.
        """
        self.heuristic = heuristic or ZeroHeuristic()
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds the shortest path using A* search.

        Args:
            origin_node_id: ID of the starting node.
            destination_node_id: ID of the target destination node.
            context: RoutingContext with network and cost parameters.

        Returns:
            RoutingResult: The found route path and execution statistics.

        Raises:
            InvalidNodeError: If node IDs are missing in the network.
            NoPathFoundError: If no path connects origin and destination.
            ValueError: If an edge returns a negative cost weight.
        """
        self.search_count += 1
        start_time = time.perf_counter()

        network = context.network
        if origin_node_id not in network.nodes:
            raise InvalidNodeError(
                f"Origin node '{origin_node_id}' not found in network."
            )
        if destination_node_id not in network.nodes:
            raise InvalidNodeError(
                f"Destination node '{destination_node_id}' not found."
            )

        # Handle trivial case where origin matches destination
        if origin_node_id == destination_node_id:
            elapsed = time.perf_counter() - start_time
            self.total_search_time += elapsed
            return RoutingResult(
                path_nodes=[origin_node_id],
                path_edges=[],
                total_cost=0.0,
                expanded_nodes=0,
                search_time_s=elapsed,
            )

        dest_node = network.nodes[destination_node_id]
        h_start = self.heuristic(network.nodes[origin_node_id], dest_node, network)

        # Priority queue holds tuples: (f_score, g_score, node_id)
        pq: list[tuple[float, float, str]] = [(h_start, 0.0, origin_node_id)]
        g_score: dict[str, float] = {origin_node_id: 0.0}
        # Parent mapping: node_id -> (parent_node_id, edge_id)
        parent: dict[str, tuple[str, str]] = {}
        visited: set[str] = set()
        expanded_count = 0

        while pq:
            _, cost, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            expanded_count += 1

            if u == destination_node_id:
                break

            from_edge = None
            if u != origin_node_id and u in parent:
                from_edge = parent[u][1]

            for edge in network.get_outgoing_edges(u, from_edge):
                if edge.is_closed or edge.current_speed_limit <= 0.0:
                    continue

                v = edge.to_node
                edge_cost = context.cost_function(
                    edge, context.vehicle, network, context
                )

                if edge_cost < 0.0:
                    raise ValueError(
                        f"A* encountered illegal negative edge cost: {edge_cost} "
                        f"on edge '{edge.id}'"
                    )

                new_g = cost + edge_cost
                if v not in g_score or new_g < g_score[v]:
                    g_score[v] = new_g
                    parent[v] = (u, edge.id)
                    h_val = self.heuristic(network.nodes[v], dest_node, network)
                    new_f = new_g + h_val
                    heapq.heappush(pq, (new_f, new_g, v))

        if destination_node_id not in g_score:
            raise NoPathFoundError(
                f"No path connects origin '{origin_node_id}' to "
                f"destination '{destination_node_id}'."
            )

        # Reconstruct path by backtracking parent pointers
        path_nodes, path_edges = reconstruct_path(
            origin_node_id, destination_node_id, parent
        )

        elapsed_time = time.perf_counter() - start_time
        self.total_search_time += elapsed_time
        self.total_expanded_nodes += expanded_count

        return RoutingResult(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_cost=g_score[destination_node_id],
            expanded_nodes=expanded_count,
            search_time_s=elapsed_time,
        )

    def update_network(self, network_update: Any) -> None:
        """A* is memoryless and does not cache internal graphs."""
        pass

    def reset(self) -> None:
        """Resets execution metrics tracking."""
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0

    def get_statistics(self) -> dict[str, Any]:
        """Returns cumulative execution telemetry."""
        return {
            "search_count": self.search_count,
            "total_search_time_s": self.total_search_time,
            "total_expanded_nodes": self.total_expanded_nodes,
            "avg_search_time_s": (
                (self.total_search_time / self.search_count)
                if self.search_count > 0
                else 0.0
            ),
        }
