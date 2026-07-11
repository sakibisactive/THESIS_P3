"""Dijkstra's shortest path routing algorithm implementation."""

import heapq
import time
from typing import Any

from src.routing.exceptions import InvalidNodeError, NoPathFoundError
from src.routing.graph_utils import reconstruct_path
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult


class DijkstraRouter(Router):
    """Implementation of Dijkstra's single-source shortest path algorithm.

    Guarantees mathematically optimal path findings for networks containing
    strictly non-negative edge costs (satisfying Dijkstra's non-negativity constraint).
    """

    def __init__(self) -> None:
        """Initializes the Dijkstra router with tracking counters."""
        self.search_count = 0
        self.total_search_time = 0.0
        self.total_expanded_nodes = 0

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds the shortest path using Dijkstra's algorithm.

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

        # Priority queue holds tuples: (cumulative_cost, node_id)
        pq: list[tuple[float, str]] = [(0.0, origin_node_id)]
        dist: dict[str, float] = {origin_node_id: 0.0}
        # Parent mapping: node_id -> (parent_node_id, edge_id)
        parent: dict[str, tuple[str, str]] = {}
        visited: set[str] = set()
        expanded_count = 0

        while pq:
            cost, u = heapq.heappop(pq)
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
                        f"Dijkstra encountered illegal negative edge cost: "
                        f"{edge_cost} on edge '{edge.id}'"
                    )

                new_cost = cost + edge_cost
                if v not in dist or new_cost < dist[v]:
                    dist[v] = new_cost
                    parent[v] = (u, edge.id)
                    heapq.heappush(pq, (new_cost, v))

        if destination_node_id not in dist:
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
            total_cost=dist[destination_node_id],
            expanded_nodes=expanded_count,
            search_time_s=elapsed_time,
        )

    def update_network(self, network_update: Any) -> None:
        """Dijkstra is memoryless and does not cache internal graphs."""
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
