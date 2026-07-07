"""Defines the RoutingContext and standard edge cost functions."""

import math
from collections.abc import Callable
from typing import Any

from src.core.network import Edge, Network
from src.core.vehicle import Vehicle

# Type alias for edge cost functions
EdgeCostFunction = Callable[[Edge, Vehicle | None, Network, Any], float]


def shortest_distance_cost(
    edge: Edge,
    vehicle: Vehicle | None,
    network: Network,
    context: Any,
) -> float:
    """Calculates cost based on the physical length of the edge in meters."""
    return edge.length


def fastest_time_cost(
    edge: Edge,
    vehicle: Vehicle | None,
    network: Network,
    context: Any,
) -> float:
    """Calculates cost based on traversal time in seconds under current speed limits."""
    speed = edge.current_speed_limit
    if speed <= 0.0:
        return float("inf")
    return edge.length / speed


def energy_optimal_cost(
    edge: Edge,
    vehicle: Vehicle | None,
    network: Network,
    context: Any,
) -> float:
    """Calculates cost based on energy consumption in kWh using potential reweighting.

    Uses Johnson's potential reweighting to eliminate negative costs from
    regenerative braking while preserving relative path quality guarantees.
    """
    if vehicle is None or vehicle.battery is None:
        # Fallback to travel time/distance cost if no vehicle physical model is provided
        return fastest_time_cost(edge, vehicle, network, context)

    speed = edge.current_speed_limit
    if speed <= 0.0:
        return float("inf")

    # 1. Compute raw energy consumption on the edge (can be negative due to regen)
    raw_energy_kwh = vehicle.battery.calculate_consumption(
        distance_m=edge.length,
        speed_m_s=speed,
        acceleration_m_s2=0.0,
        gradient_rad=edge.gradient_rad,
    )

    # 2. Apply Johnson's potential reweighting
    # h(u) = (mass * g * elevation) / (3.6e6) to convert Joules to kWh
    # E'(u, v) = E(u, v) + h(u) - h(v)
    mass_kg = vehicle.battery.mass_kg
    g = 9.81  # gravity m/s^2

    # Get node elevations from context
    elevation_from = context.get_node_elevation(edge.from_node)
    elevation_to = context.get_node_elevation(edge.to_node)

    h_from = (mass_kg * g * elevation_from) / 3.6e6
    h_to = (mass_kg * g * elevation_to) / 3.6e6

    reweighted_energy_kwh = raw_energy_kwh + h_from - h_to

    # 3. Clamp to a small positive epsilon to prevent negative/zero weights
    # ensuring mathematical correctness of Dijkstra/A* priority queues.
    return float(max(1e-6, reweighted_energy_kwh))


def compute_node_elevations(network: Network) -> dict[str, float]:
    """Computes Cartesian elevation for each node based on edge gradients.

    Constructs an undirected representation of the network topology to propagate
    elevations consistently across each connected component.
    """
    adj: dict[str, list[tuple[str, float]]] = {nid: [] for nid in network.nodes}
    for edge in network.edges.values():
        dh = edge.length * math.sin(edge.gradient_rad)
        adj[edge.from_node].append((edge.to_node, dh))
        adj[edge.to_node].append((edge.from_node, -dh))

    elevations: dict[str, float] = {}
    for start_node in network.nodes:
        if start_node in elevations:
            continue

        elevations[start_node] = 0.0
        queue = [start_node]
        while queue:
            u = queue.pop(0)
            u_el = elevations[u]
            for v, dh in adj[u]:
                if v not in elevations:
                    elevations[v] = u_el + dh
                    queue.append(v)
    return elevations


class RoutingContext:
    """Contains constraints and objectives for a single routing query."""

    def __init__(
        self,
        network: Network,
        vehicle: Vehicle | None = None,
        current_time: float = 0.0,
        cost_function: EdgeCostFunction | None = None,
        active_incidents: list[Any] | None = None,
    ) -> None:
        """Initializes the routing query context.

        Args:
            network: The road network graph snapshot.
            vehicle: The optional vehicle instance requesting the path.
            current_time: The current simulation timestamp.
            cost_function: Strategy function to evaluate edge costs.
            active_incidents: Optional list of active Incident objects for
                emergency-aware scoring. Incidents must expose
                ``distance_to_edge(edge, network) -> float`` and
                ``intensity: float``.
        """
        self.network = network
        self.vehicle = vehicle
        self.current_time = current_time
        self.cost_function = cost_function or shortest_distance_cost
        self.active_incidents: list[Any] = active_incidents or []

        # Lazy elevation calculation
        self._node_elevations: dict[str, float] | None = None

    def get_node_elevation(self, node_id: str) -> float:
        """Retrieves or calculates the elevation of the node based on edge gradients."""
        if self._node_elevations is None:
            self._node_elevations = compute_node_elevations(self.network)
        return self._node_elevations.get(node_id, 0.0)
