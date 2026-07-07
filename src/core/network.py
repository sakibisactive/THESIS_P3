from typing import Any, Self

from src.utils.exceptions import NetworkError


class Node:
    """Represents a spatial point in the road network graph."""

    def __init__(self, node_id: str, x: float, y: float) -> None:
        """Initializes a network Node.

        Args:
            node_id: Unique string identifier for the node.
            x: X-coordinate in the Cartesian space (meters).
            y: Y-coordinate in the Cartesian space (meters).
        """
        self.id = node_id
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Node(id={self.id}, x={self.x}, y={self.y})"


class Edge:
    """Represents a directed link between two Nodes in the graph."""

    def __init__(
        self,
        edge_id: str,
        from_node: str,
        to_node: str,
        length: float,
        speed_limit: float,
        gradient_rad: float = 0.0,
    ) -> None:
        """Initializes a directed road segment.

        Args:
            edge_id: Unique string identifier for the edge.
            from_node: ID of the starting node.
            to_node: ID of the ending node.
            length: Length of the segment in meters.
            speed_limit: Speed limit in meters/second.
            gradient_rad: Slope angle of the road in radians.

        Raises:
            ValueError: If length or speed limit are negative or zero.
        """
        if length <= 0.0:
            raise ValueError(f"Edge length must be positive: {length}")
        if speed_limit <= 0.0:
            raise ValueError(f"Edge speed limit must be positive: {speed_limit}")

        self.id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        self.length = length
        self.speed_limit = speed_limit
        self.gradient_rad = gradient_rad

        # Dynamic state updated by simulation events
        self.speed_reduction_factor: float = 1.0  # 1.0 = normal, 0.0 = fully blocked
        self.is_closed: bool = False

    @property
    def current_speed_limit(self) -> float:
        """Gets the speed limit adjusted for dynamic congestion or hazard reductions."""
        if self.is_closed:
            return 0.0
        return self.speed_limit * self.speed_reduction_factor

    def __repr__(self) -> str:
        return (
            f"Edge(id={self.id}, from={self.from_node}, to={self.to_node}, "
            f"length={self.length:.1f}m, speed={self.speed_limit:.1f}m/s)"
        )


class ChargingStation:
    """Represents an EV charging facility situated at a network Node."""

    def __init__(
        self,
        station_id: str,
        node_id: str,
        capacity: int,
        power_kw: float,
        base_price_per_kwh: float,
    ) -> None:
        """Initializes a charging station.

        Args:
            station_id: Unique string identifier.
            node_id: The ID of the node where this station is located.
            capacity: Number of concurrent charging spaces.
            power_kw: Power supply rating of chargers in kW.
            base_price_per_kwh: Charging fee per kWh.
        """
        self.id = station_id
        self.node_id = node_id
        self.capacity = capacity
        self.power_kw = power_kw
        self.base_price_per_kwh = base_price_per_kwh

        # Queuing and charging status tracking (uses vehicle IDs)
        self.queue: list[str] = []
        self.charging_vehicles: set[str] = set()
        self.is_operational: bool = True

    def get_estimated_wait_time(self, avg_charge_duration_s: float = 1800.0) -> float:
        """Calculates estimated wait time in seconds based on current queues.

        Formula: (Number in queue / Number of chargers) * Average charge duration.

        Args:
            avg_charge_duration_s: Expected charging session duration in seconds.

        Returns:
            float: Estimated queue wait time in seconds.
        """
        if not self.is_operational:
            return float("inf")
        if self.capacity <= 0:
            return float("inf")
        # Estimate queue delay based on server capacity
        active_queue_len = len(self.queue)
        return (active_queue_len / self.capacity) * avg_charge_duration_s

    def add_to_queue(self, vehicle_id: str) -> None:
        """Enqueues a vehicle at the charging station.

        Args:
            vehicle_id: Unique identifier of the vehicle.
        """
        if not self.is_operational:
            return
        if vehicle_id not in self.queue and vehicle_id not in self.charging_vehicles:
            self.queue.append(vehicle_id)

    def start_charging(self, vehicle_id: str) -> bool:
        """Attempts to transition a vehicle from queue to an active charging bay.

        Args:
            vehicle_id: Unique identifier of the vehicle.

        Returns:
            bool: True if charging started successfully, False if bays are full
                  or vehicle is not in queue.
        """
        if not self.is_operational:
            return False
        if len(self.charging_vehicles) >= self.capacity:
            return False

        if vehicle_id in self.queue:
            self.queue.remove(vehicle_id)
            self.charging_vehicles.add(vehicle_id)
            return True
        elif vehicle_id not in self.charging_vehicles:
            # Direct charge if queue is empty and bays are free
            self.charging_vehicles.add(vehicle_id)
            return True

        return False

    def stop_charging(self, vehicle_id: str) -> None:
        """Releases a vehicle from the charging bay.

        Args:
            vehicle_id: Unique identifier of the vehicle.
        """
        self.charging_vehicles.discard(vehicle_id)

    def remove_from_queue(self, vehicle_id: str) -> None:
        """Removes a vehicle from the queue (e.g. if it decides to leave).

        Args:
            vehicle_id: Unique identifier of the vehicle.
        """
        if vehicle_id in self.queue:
            self.queue.remove(vehicle_id)

    def __repr__(self) -> str:
        return (
            f"ChargingStation(id={self.id}, node={self.node_id}, "
            f"charging={len(self.charging_vehicles)}/{self.capacity}, "
            f"queue={len(self.queue)})"
        )


class Network:
    """Simulator-agnostic directed graph representing the road topology."""

    def __init__(self) -> None:
        """Initializes an empty road network."""
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.stations: dict[str, ChargingStation] = {}

        # Fast lookup mapping node ID -> list of outgoing edges
        self._adjacency_map: dict[str, list[Edge]] = {}
        # Fast lookup mapping node ID -> list of incoming edges
        self._incoming_map: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Adds a Node to the network graph.

        Args:
            node: The Node instance.
        """
        self.nodes[node.id] = node
        self._adjacency_map.setdefault(node.id, [])
        self._incoming_map.setdefault(node.id, [])

    def add_edge(self, edge: Edge) -> None:
        """Adds a directed Edge to the network graph.

        Args:
            edge: The Edge instance.

        Raises:
            NetworkError: If source or destination node does not exist in graph.
        """
        if edge.from_node not in self.nodes:
            raise NetworkError(f"Source node '{edge.from_node}' not in network.")
        if edge.to_node not in self.nodes:
            raise NetworkError(f"Target node '{edge.to_node}' not in network.")

        self.edges[edge.id] = edge
        self._adjacency_map[edge.from_node].append(edge)
        self._incoming_map[edge.to_node].append(edge)

    def add_station(self, station: ChargingStation) -> None:
        """Registers a ChargingStation at its specified node.

        Args:
            station: The ChargingStation instance.

        Raises:
            NetworkError: If node location does not exist in graph.
        """
        if station.node_id not in self.nodes:
            raise NetworkError(f"Charging node '{station.node_id}' not in network.")
        self.stations[station.id] = station

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        """Gets all outgoing edges starting from the specified node.

        Args:
            node_id: Unique identifier of the node.

        Returns:
            list[Edge]: List of outgoing Edge instances.
        """
        return self._adjacency_map.get(node_id, [])

    def get_incoming_edges(self, node_id: str) -> list[Edge]:
        """Gets all incoming edges ending at the specified node.

        Args:
            node_id: Unique identifier of the node.

        Returns:
            list[Edge]: List of incoming Edge instances.
        """
        return self._incoming_map.get(node_id, [])

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> Self:
        """Factory method to construct a Network from a dictionary configuration.

        Format:
        {
            "nodes": [{"id": "n1", "x": 0.0, "y": 0.0}, ...],
            "edges": [{"id": "e1", "from": "n1", "to": "n2", "length": 100.0,
                       "speed_limit": 13.89, "gradient_rad": 0.0}, ...],
            "stations": [{"id": "cs1", "node_id": "n1", "capacity": 2,
                          "power_kw": 50.0, "base_price_per_kwh": 0.35}, ...]
        }

        Args:
            data: Parsed configuration dictionary.

        Returns:
            Network: The populated Network instance.

        Raises:
            NetworkError: If schema keys are missing or malformed.
        """
        network = cls()
        try:
            for n in data.get("nodes", []):
                network.add_node(Node(node_id=n["id"], x=n["x"], y=n["y"]))

            for e in data.get("edges", []):
                network.add_edge(
                    Edge(
                        edge_id=e["id"],
                        from_node=e["from"],
                        to_node=e["to"],
                        length=e["length"],
                        speed_limit=e["speed_limit"],
                        gradient_rad=e.get("gradient_rad", 0.0),
                    )
                )

            for s in data.get("stations", []):
                network.add_station(
                    ChargingStation(
                        station_id=s["id"],
                        node_id=s["node_id"],
                        capacity=s["capacity"],
                        power_kw=s["power_kw"],
                        base_price_per_kwh=s.get("base_price_per_kwh", 0.35),
                    )
                )
        except KeyError as err:
            msg = f"Missing required field in network config: {err}"
            raise NetworkError(msg) from err
        except Exception as err:
            msg = f"Failed to parse network configuration: {err}"
            raise NetworkError(msg) from err

        return network
