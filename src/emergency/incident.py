import math

from src.core.network import Edge, Network
from src.utils.config import EmergencyEventConfig


class Incident:
    """Models a dynamic, expanding spatiotemporal emergency event (hazard zone)."""

    def __init__(self, config: EmergencyEventConfig) -> None:
        """Initializes the Incident based on config settings.

        Args:
            config: Configuration defining the event location and propagation traits.
        """
        self.id = config.id
        self.epicenter_x = 0.0
        self.epicenter_y = 0.0
        self.epicenter_node_id = config.epicenter_node_id
        self.start_time = config.start_time
        self.duration = config.duration
        self.initial_radius = config.initial_radius_m
        self.propagation_rate = config.propagation_rate
        self.intensity = config.intensity

        # Ephemeral states
        self.resolved = False

    def initialize_epicenter_position(self, network: Network) -> None:
        """Resolves the epicenter's node ID to (x, y) coordinates from the
        network topology.

        Args:
            network: The network graph representation containing the node coordinates.
        """
        if self.epicenter_node_id in network.nodes:
            node = network.nodes[self.epicenter_node_id]
            self.epicenter_x = node.x
            self.epicenter_y = node.y
        else:
            # Fallback coordinates if node ID is not found (default center 0.0, 0.0)
            self.epicenter_x = 0.0
            self.epicenter_y = 0.0

    def is_active(self, current_time: float) -> bool:
        """Determines if the incident is active at the given simulation time.

        Args:
            current_time: The current simulation time in seconds.

        Returns:
            bool: True if active, False otherwise.
        """
        if self.resolved:
            return False
        return self.start_time <= current_time <= (self.start_time + self.duration)

    def get_radius(self, current_time: float) -> float:
        """Calculates the current propagation radius of the hazard at a given time.

        Args:
            current_time: The current simulation time in seconds.

        Returns:
            float: Radius in meters.
        """
        if not self.is_active(current_time):
            if current_time < self.start_time:
                return 0.0
            return self.initial_radius + self.propagation_rate * self.duration

        elapsed = current_time - self.start_time
        return self.initial_radius + self.propagation_rate * elapsed

    def is_point_inside(self, x: float, y: float, current_time: float) -> bool:
        """Checks if a given 2D coordinate is within the hazard zone radius.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            current_time: The current simulation time in seconds.

        Returns:
            bool: True if inside the hazard radius, False otherwise.
        """
        if not self.is_active(current_time) and current_time < self.start_time:
            return False

        dx = x - self.epicenter_x
        dy = y - self.epicenter_y
        dist = math.sqrt(dx * dx + dy * dy)
        return dist <= self.get_radius(current_time)

    def distance_to_edge(self, edge: Edge, network: Network) -> float:
        """Calculates the shortest Euclidean distance from the epicenter
        to an edge segment.

        Uses point-to-segment projection math.

        Args:
            edge: The Edge to compute distance to.
            network: The network graph containing node coordinates.

        Returns:
            float: Distance in meters.
        """
        from_node = network.nodes.get(edge.from_node)
        to_node = network.nodes.get(edge.to_node)

        if not from_node or not to_node:
            return float("inf")

        # Segment endpoints
        ax, ay = from_node.x, from_node.y
        bx, by = to_node.x, to_node.y

        # Epicenter coordinates
        px, py = self.epicenter_x, self.epicenter_y

        # Segment vector AB
        abx = bx - ax
        aby = by - ay

        # Point vector AP
        apx = px - ax
        apy = py - ay

        ab_lensq = abx * abx + aby * aby
        if ab_lensq == 0.0:
            # Endpoints coincide, return point distance
            return math.sqrt(apx * apx + apy * apy)

        # Projection ratio t, clamped to [0.0, 1.0] representing the segment bounds
        t = (apx * abx + apy * aby) / ab_lensq
        t = max(0.0, min(1.0, t))

        # Closest point C on segment AB
        cx = ax + t * abx
        cy = ay + t * aby

        # Distance PC
        dx = px - cx
        dy = py - cy
        return math.sqrt(dx * dx + dy * dy)

    def get_affected_edges(self, network: Network, current_time: float) -> list[str]:
        """Identifies all network edges within the active hazard radius.

        Args:
            network: The network graph representation.
            current_time: The current simulation time in seconds.

        Returns:
            list[str]: List of affected edge IDs.
        """
        if not self.is_active(current_time) and current_time < self.start_time:
            return []

        radius = self.get_radius(current_time)
        affected = []
        for edge_id, edge in network.edges.items():
            if self.distance_to_edge(edge, network) <= radius:
                affected.append(edge_id)
        return affected

    def __repr__(self) -> str:
        return (
            f"Incident(id={self.id}, active_at_node={self.epicenter_node_id}, "
            f"pos=({self.epicenter_x:.1f}, {self.epicenter_y:.1f}))"
        )
