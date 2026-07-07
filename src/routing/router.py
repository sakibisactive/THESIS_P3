"""Defines the abstract base Router class."""

from abc import ABC, abstractmethod
from typing import Any

from src.routing.routing_context import RoutingContext
from src.routing.routing_result import RoutingResult


class Router(ABC):
    """Abstract base class for all routing algorithms."""

    @abstractmethod
    def find_route(
        self,
        origin_node_id: str,
        destination_node_id: str,
        context: RoutingContext,
    ) -> RoutingResult:
        """Finds an optimal route between origin and destination nodes.

        Args:
            origin_node_id: ID of the starting node.
            destination_node_id: ID of the target destination node.
            context: RoutingContext containing network snapshot and objectives.

        Returns:
            RoutingResult: The search results including paths and metrics.

        Raises:
            NoPathFoundError: If no path can connect origin and destination.
            InvalidNodeError: If node IDs are not present in the network.
        """
        pass

    @abstractmethod
    def update_network(self, network_update: Any) -> None:
        """Updates the router's internal network state representation if cached."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets any internal caches or learning parameters."""
        pass

    @abstractmethod
    def get_statistics(self) -> dict[str, Any]:
        """Returns internal execution statistics (e.g., search counts)."""
        pass
