from enum import Enum

from src.core.battery import BatteryModel
from src.core.network import Network


class VehicleState(Enum):
    """Enumeration representing the operational state of an EV agent."""

    EN_ROUTE = "EN_ROUTE"
    WAITING_IN_QUEUE = "WAITING_IN_QUEUE"
    CHARGING = "CHARGING"
    STRANDED = "STRANDED"
    ARRIVED = "ARRIVED"


class Vehicle:
    """Represents an Electric Vehicle (EV) agent in the simulator."""

    # Threshold representing full charge (99%)
    FULL_CHARGE_THRESHOLD: float = 0.99

    def __init__(
        self,
        vehicle_id: str,
        origin_node_id: str,
        destination_node_id: str,
        initial_soc: float,
        battery: BatteryModel,
    ) -> None:
        """Initializes an EV agent.

        Args:
            vehicle_id: Unique string identifier for the vehicle.
            origin_node_id: Node ID where the trip begins.
            destination_node_id: Node ID where the trip ends.
            initial_soc: Starting State of Charge (value between 0.0 and 1.0).
            battery: The initialized BatteryModel for energy calculations.

        Raises:
            ValueError: If initial_soc is not in range [0.0, 1.0].
        """
        if not (0.0 <= initial_soc <= 1.0):
            raise ValueError(f"Initial SoC must be between 0.0 and 1.0: {initial_soc}")

        self.id = vehicle_id
        self.origin_node_id = origin_node_id
        self.destination_node_id = destination_node_id
        self.soc = initial_soc
        self.battery = battery

        # Route-tracking attributes
        self.current_route: list[str] = []  # List of edge IDs representing path
        self.current_edge_idx: int = 0
        self.distance_on_current_edge: float = 0.0
        self.speed: float = 0.0

        # Operational state
        self.state: VehicleState = VehicleState.EN_ROUTE

        # Yielding state for emergency corridors
        self.is_yielding: bool = False
        self.yield_speed_limit: float | None = None

        # Cumulative performance statistics
        self.accumulated_travel_time: float = 0.0  # seconds
        self.accumulated_energy_consumed: float = 0.0  # kWh
        self.accumulated_queue_time: float = 0.0  # seconds
        self.accumulated_charge_time: float = 0.0  # seconds
        self.recalculation_count: int = 0

    def assign_route(self, route: list[str]) -> None:
        """Assigns a planned route to the vehicle.

        Args:
            route: List of edge IDs forming a contiguous path.
        """
        self.current_route = list(route)
        self.current_edge_idx = 0
        self.distance_on_current_edge = 0.0
        self.state = VehicleState.EN_ROUTE

    def step_movement(
        self,
        dt_seconds: float,
        current_speed_m_s: float,
        current_acceleration_m_s2: float,
        network: Network,
    ) -> None:
        """Updates the vehicle's position and battery SoC during active movement.

        Executes fractional movements across edge boundaries within a single time step.

        Args:
            dt_seconds: Time step duration in seconds.
            current_speed_m_s: Traversal velocity in meters/second.
            current_acceleration_m_s2: Traversal acceleration in meters/second^2.
            network: The road network graph.
        """
        if self.state != VehicleState.EN_ROUTE:
            return

        if not self.current_route:
            # Arrived if no route remains
            self.state = VehicleState.ARRIVED
            return

        time_remaining = dt_seconds

        while time_remaining > 0.0 and self.state == VehicleState.EN_ROUTE:
            # Retrieve the current edge instance
            edge_id = self.current_route[self.current_edge_idx]
            edge = network.edges.get(edge_id)
            if not edge:
                self.state = VehicleState.STRANDED
                return

            # Max speed is capped by the edge's current speed limit
            speed = min(current_speed_m_s, edge.current_speed_limit)
            if self.is_yielding and self.yield_speed_limit is not None:
                speed = min(speed, self.yield_speed_limit)
            if speed <= 0.0:
                # If traffic is completely blocked, time passes but no
                # distance is covered
                self.accumulated_travel_time += time_remaining
                break

            # Distance we can cover in the remaining time
            distance_to_cover = speed * time_remaining
            distance_left_on_edge = edge.length - self.distance_on_current_edge

            if distance_to_cover < distance_left_on_edge:
                # We stay on the current edge
                self.distance_on_current_edge += distance_to_cover
                energy = self.battery.calculate_consumption(
                    distance_m=distance_to_cover,
                    speed_m_s=speed,
                    acceleration_m_s2=current_acceleration_m_s2,
                    gradient_rad=edge.gradient_rad,
                )
                self._apply_energy_draw(energy)
                self.accumulated_travel_time += time_remaining
                time_remaining = 0.0
            else:
                # We reach the end of the current edge
                self.distance_on_current_edge = edge.length
                energy = self.battery.calculate_consumption(
                    distance_m=distance_left_on_edge,
                    speed_m_s=speed,
                    acceleration_m_s2=current_acceleration_m_s2,
                    gradient_rad=edge.gradient_rad,
                )
                self._apply_energy_draw(energy)

                time_spent_on_edge = distance_left_on_edge / speed
                self.accumulated_travel_time += time_spent_on_edge
                time_remaining -= time_spent_on_edge

                if self.soc <= 0.0:
                    time_remaining = 0.0
                    break

                # Transition to next edge in route
                if self.current_edge_idx + 1 < len(self.current_route):
                    self.current_edge_idx += 1
                    self.distance_on_current_edge = 0.0
                else:
                    # End of route reached
                    self.state = VehicleState.ARRIVED
                    time_remaining = 0.0

    def step_charging(self, dt_seconds: float, charger_power_kw: float) -> None:
        """Performs a battery charging update step.

        Args:
            dt_seconds: Time step duration in seconds.
            charger_power_kw: Output power of the charging station slot in kW.
        """
        if self.state != VehicleState.CHARGING:
            return

        # Energy added in kWh: E = P * t (hours)
        energy_added = charger_power_kw * (dt_seconds / 3600.0)
        soc_increase = energy_added / self.battery.capacity_kwh

        self.soc = min(1.0, self.soc + soc_increase)
        self.accumulated_charge_time += dt_seconds

        # Automatically transition back to route prep if fully charged
        if self.soc >= self.FULL_CHARGE_THRESHOLD:
            self.soc = 1.0
            # Note: Transition to EN_ROUTE will be handled by the simulator once
            # it detaches from the charging station.

    def step_waiting(self, dt_seconds: float) -> None:
        """Updates the waiting stats for vehicles in charging station queues.

        Args:
            dt_seconds: Time step duration in seconds.
        """
        if self.state == VehicleState.WAITING_IN_QUEUE:
            self.accumulated_queue_time += dt_seconds

    def _apply_energy_draw(self, energy_kwh: float) -> None:
        """Internal helper to apply energy consumption and handle depletion.

        Args:
            energy_kwh: Energy consumed (positive) or regenerated (negative).
        """
        self.accumulated_energy_consumed += energy_kwh
        soc_draw = energy_kwh / self.battery.capacity_kwh
        self.soc = max(0.0, self.soc - soc_draw)

        if self.soc <= 0.0:
            self.soc = 0.0
            self.state = VehicleState.STRANDED

    def get_position(self, network: Network) -> tuple[float, float]:
        """Calculates the current (x, y) coordinates of the vehicle in the network.

        Interpolates along the current edge segment.

        Args:
            network: The network graph representation.

        Returns:
            tuple[float, float]: (x, y) coordinates in meters.
        """
        if self.state == VehicleState.ARRIVED or not self.current_route:
            # Use destination node position if arrived or no route, fallback to origin
            node_id = (
                self.destination_node_id
                if self.state == VehicleState.ARRIVED
                else self.origin_node_id
            )
            node = network.nodes.get(node_id)
            if node:
                return node.x, node.y
            return 0.0, 0.0

        edge_id = self.current_route[self.current_edge_idx]
        edge = network.edges.get(edge_id)
        if not edge:
            return 0.0, 0.0

        from_node = network.nodes.get(edge.from_node)
        to_node = network.nodes.get(edge.to_node)
        if not from_node or not to_node:
            return 0.0, 0.0

        # Linear interpolation based on distance_on_current_edge
        ratio = (
            self.distance_on_current_edge / edge.length if edge.length > 0.0 else 0.0
        )
        x = from_node.x + ratio * (to_node.x - from_node.x)
        y = from_node.y + ratio * (to_node.y - from_node.y)
        return x, y

    def yield_for_emergency(self, yield_speed: float) -> None:
        """Casts the vehicle into yielding state, capping its speed.

        Args:
            yield_speed: The maximum speed target (in m/s) when yielding.
        """
        self.is_yielding = True
        self.yield_speed_limit = yield_speed

    def reset_yield(self) -> None:
        """Resets the vehicle's yielding state to default operation."""
        self.is_yielding = False
        self.yield_speed_limit = None

    def __repr__(self) -> str:
        return (
            f"Vehicle(id={self.id}, state={self.state.value}, "
            f"soc={self.soc * 100:.1f}%, route_idx={self.current_edge_idx}/"
            f"{len(self.current_route)})"
        )
