"""Defines the pluggable A* heuristic strategies."""

import math
from collections.abc import Callable
from enum import StrEnum

from src.core.network import Network, Node

# Heuristic function signature
HeuristicFunction = Callable[[Node, Node, Network], float]


class HeuristicType(StrEnum):
    """Supported heuristics for A* search selectable via configuration."""

    ZERO = "ZERO"
    EUCLIDEAN = "EUCLIDEAN"
    MANHATTAN = "MANHATTAN"


class ZeroHeuristic:
    """A zero heuristic, making A* search equivalent to Dijkstra's algorithm."""

    def __call__(self, node: Node, dest: Node, network: Network) -> float:
        return 0.0


class EuclideanHeuristic:
    """Calculates the straight-line Euclidean distance between two nodes.

    Can be scaled by a speed factor to remain admissible under travel-time costs.
    """

    def __init__(self, speed_scale_m_s: float | None = None) -> None:
        """Initializes Euclidean heuristic.

        Args:
            speed_scale_m_s: Optional maximum speed in meters/second. If provided,
                returns estimated travel time in seconds instead of raw meters.
        """
        self.speed_scale = speed_scale_m_s

    def __call__(self, node: Node, dest: Node, network: Network) -> float:
        dx = node.x - dest.x
        dy = node.y - dest.y
        dist = math.sqrt(dx * dx + dy * dy)
        if self.speed_scale is not None and self.speed_scale > 0.0:
            return dist / self.speed_scale
        return dist


class ManhattanHeuristic:
    """Calculates the Manhattan L1 distance between two nodes.

    Can be scaled by a speed factor to remain admissible under travel-time costs.
    """

    def __init__(self, speed_scale_m_s: float | None = None) -> None:
        """Initializes Manhattan heuristic.

        Args:
            speed_scale_m_s: Optional maximum speed in meters/second. If provided,
                returns estimated travel time in seconds instead of raw meters.
        """
        self.speed_scale = speed_scale_m_s

    def __call__(self, node: Node, dest: Node, network: Network) -> float:
        dist = abs(node.x - dest.x) + abs(node.y - dest.y)
        if self.speed_scale is not None and self.speed_scale > 0.0:
            return dist / self.speed_scale
        return dist


def get_heuristic(
    heuristic_type: HeuristicType, speed_scale_m_s: float | None = None
) -> HeuristicFunction:
    """Factory function to build the requested heuristic strategy."""
    if heuristic_type == HeuristicType.ZERO:
        return ZeroHeuristic()
    elif heuristic_type == HeuristicType.EUCLIDEAN:
        return EuclideanHeuristic(speed_scale_m_s)
    elif heuristic_type == HeuristicType.MANHATTAN:
        return ManhattanHeuristic(speed_scale_m_s)
    else:
        raise ValueError(f"Unknown heuristic type: {heuristic_type}")
