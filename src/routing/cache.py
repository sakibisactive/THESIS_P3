"""Implements the optional, invalidatable route cache and its decorator."""

from typing import Any

from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult


def get_cost_fn_identifier(cost_fn: Any) -> str:
    """Helper to extract a consistent string identifier for a cost function."""
    return getattr(cost_fn, "__name__", str(cost_fn))


class RouteCache:
    """Stores previously computed paths to avoid redundant search execution.

    Supports edge-specific cache invalidation to handle dynamic road closures
    and edge modifications without returning stale routes.
    """

    def __init__(self) -> None:
        """Initializes the RouteCache with stats tracking."""
        # Key: (origin, destination, cost_fn_id) -> RoutingResult
        self._cache: dict[tuple[str, str, str], RoutingResult] = {}
        self.hits = 0
        self.misses = 0

    def get(
        self, origin_node_id: str, destination_node_id: str, cost_fn_id: str
    ) -> RoutingResult | None:
        """Retrieves a route from the cache if available.

        Args:
            origin_node_id: Starting node.
            destination_node_id: Ending node.
            cost_fn_id: Cost function identifier.

        Returns:
            RoutingResult | None: The cached result, or None if a cache miss occurs.
        """
        key = (origin_node_id, destination_node_id, cost_fn_id)
        if key in self._cache:
            self.hits += 1
            return self._cache[key]
        self.misses += 1
        return None

    def set(
        self,
        origin_node_id: str,
        destination_node_id: str,
        cost_fn_id: str,
        result: RoutingResult,
    ) -> None:
        """Saves a route result in the cache.

        Args:
            origin_node_id: Starting node.
            destination_node_id: Ending node.
            cost_fn_id: Cost function identifier.
            result: RoutingResult to cache.
        """
        key = (origin_node_id, destination_node_id, cost_fn_id)
        self._cache[key] = result

    def invalidate_edges(self, edge_ids: list[str]) -> None:
        """Invalidates all cached routes that traverse any of the specified edges.

        Args:
            edge_ids: List of edge IDs that have changed or been closed.
        """
        edge_set = set(edge_ids)
        keys_to_remove = [
            key
            for key, result in self._cache.items()
            if any(e_id in edge_set for e_id in result.path_edges)
        ]
        for key in keys_to_remove:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clears all entries and resets stats."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0

    def get_statistics(self) -> dict[str, Any]:
        """Returns statistics of cache efficiency."""
        total = self.hits + self.misses
        hit_ratio = (self.hits / total) if total > 0 else 0.0
        return {
            "cache_size": len(self._cache),
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_hit_ratio": hit_ratio,
        }


class CachedRouter(Router):
    """Wrapper router that intercepts queries with a cache before searching."""

    def __init__(self, delegate: Router, cache: RouteCache) -> None:
        """Initializes the CachedRouter wrapper.

        Args:
            delegate: The underlying Router instance (e.g., DijkstraRouter).
            cache: The RouteCache instance to use.
        """
        self.delegate = delegate
        self.cache = cache

    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds route by checking the cache, falling back on miss."""
        cost_fn_id = get_cost_fn_identifier(context.cost_function)
        cached = self.cache.get(origin_node_id, destination_node_id, cost_fn_id)
        if cached is not None:
            return cached

        result = self.delegate.find_route(origin_node_id, destination_node_id, context)
        self.cache.set(origin_node_id, destination_node_id, cost_fn_id, result)
        return result

    def update_network(self, network_update: Any) -> None:
        """Passes updates to the delegate and invalidates changed edges in cache."""
        self.delegate.update_network(network_update)
        if isinstance(network_update, list):
            # List of edge IDs that were modified or closed
            self.cache.invalidate_edges(network_update)
        elif isinstance(network_update, str):
            # Single edge ID
            self.cache.invalidate_edges([network_update])

    def reset(self) -> None:
        """Resets the delegate stats and cache counters."""
        self.delegate.reset()
        self.cache.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Combines stats from the delegate router and the route cache."""
        stats = self.delegate.get_statistics()
        stats.update(self.cache.get_statistics())
        return stats
