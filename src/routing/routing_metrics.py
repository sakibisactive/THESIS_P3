"""Calculates analytical routing performance metrics."""

from src.core.network import Network
from src.core.vehicle import Vehicle


class RoutingMetrics:
    """Calculates various comparative performance metrics for computed paths."""

    @staticmethod
    def calculate_path_distance(network: Network, path_edges: list[str]) -> float:
        """Calculates the total physical length of the path in meters."""
        total = 0.0
        for edge_id in path_edges:
            edge = network.edges.get(edge_id)
            if edge:
                total += edge.length
        return total

    @staticmethod
    def calculate_travel_time(network: Network, path_edges: list[str]) -> float:
        """Calculates path traversal time in seconds under current speed limits."""
        total = 0.0
        for edge_id in path_edges:
            edge = network.edges.get(edge_id)
            if edge:
                speed = edge.current_speed_limit
                if speed > 0.0:
                    total += edge.length / speed
                else:
                    return float("inf")
        return total

    @staticmethod
    def calculate_energy_consumption(
        network: Network, path_edges: list[str], vehicle: Vehicle | None
    ) -> float:
        """Calculates the estimated energy consumption in kWh across the path.

        Estimates consumption using constant speed traversal at the edge's current
        speed limit without accounting for regenerative potential reweighting offsets.
        """
        if vehicle is None or vehicle.battery is None:
            return 0.0

        total = 0.0
        for edge_id in path_edges:
            edge = network.edges.get(edge_id)
            if edge:
                speed = edge.current_speed_limit
                if speed <= 0.0:
                    return float("inf")
                total += vehicle.battery.calculate_consumption(
                    distance_m=edge.length,
                    speed_m_s=speed,
                    acceleration_m_s2=0.0,
                    gradient_rad=edge.gradient_rad,
                )
        return total

    @staticmethod
    def calculate_optimality_ratio(
        actual_cost: float, optimal_cost: float
    ) -> float:
        """Calculates optimality ratio comparing actual cost to baseline optimal cost.

        A ratio of 1.0 represents perfect optimality. Ratios > 1.0 indicate
        sub-optimal paths.
        """
        if optimal_cost <= 0.0:
            return 1.0
        return actual_cost / optimal_cost
