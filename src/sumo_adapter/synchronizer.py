"""SUMO TraCI State Synchronizer for bidirectional synchronization between
SUMO and Python.
"""

import traci  # type: ignore[import-untyped]
import traci.constants as tc  # type: ignore[import-untyped]

from src.core.network import Network
from src.core.vehicle import Vehicle, VehicleState
from src.utils.config import SimulationConfig
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SumoSynchronizer:
    """Manages the bidirectional synchronization of state between Python and SUMO."""

    MIN_ROUTE_LENGTH = 2

    def __init__(
        self,
        config: SimulationConfig,
        network: Network,
        vehicle_registry: dict[str, Vehicle],
    ) -> None:
        self.config = config
        self.network = network
        self.vehicle_registry = vehicle_registry

        # Track last synced route to avoid redundant TraCI setRoute calls
        self._last_synced_routes: dict[str, list[str]] = {}

        # List of edges that are already closed in SUMO
        self._synced_closed_edges: set[str] = set()

    def sync_from_sumo(self, dt: float) -> list[str]:  # noqa: PLR0912, PLR0915
        """Synchronizes vehicle physics and arrivals from SUMO to Python.

        Args:
            dt: Sim step size in seconds.

        Returns:
            list[str]: IDs of vehicles that arrived in this step.
        """
        arrived_ids: list[str] = []

        try:
            active_sumo_ids = traci.vehicle.getIDList()
        except traci.exceptions.TraCIException as e:
            logger.warning(f"Failed to fetch active vehicle list from TraCI: {e}")
            return arrived_ids

        # Detect arrivals: vehicle was en-route but is no longer active in SUMO
        for veh_id, vehicle in self.vehicle_registry.items():
            if vehicle.state == VehicleState.EN_ROUTE and veh_id not in active_sumo_ids:
                vehicle.state = VehicleState.ARRIVED
                arrived_ids.append(veh_id)
                logger.info(f"Vehicle '{veh_id}' arrived at destination.")

        # Update active vehicles
        for veh_id in active_sumo_ids:
            if veh_id not in self.vehicle_registry:
                continue

            vehicle = self.vehicle_registry[veh_id]
            if vehicle.state not in (VehicleState.EN_ROUTE, VehicleState.STRANDED):
                continue

            # Performance subscription: Subscribe on first sighting
            results = None
            if self.config.enable_subscriptions:
                try:
                    results = traci.vehicle.getSubscriptionResults(veh_id)
                    if not results:
                        traci.vehicle.subscribe(
                            veh_id,
                            [
                                tc.VAR_POSITION,
                                tc.VAR_SPEED,
                                tc.VAR_ROAD_ID,
                                tc.VAR_LANEPOSITION,
                                tc.VAR_ACCELERATION,
                            ],
                        )
                        results = traci.vehicle.getSubscriptionResults(veh_id)
                except traci.exceptions.TraCIException as e:
                    logger.warning(f"Error subscribing to vehicle '{veh_id}': {e}")
                    results = None

            # Pull metrics
            speed = 0.0
            road_id = ""
            lane_position = 0.0
            accel = 0.0

            if results:
                speed = results.get(tc.VAR_SPEED, 0.0)
                road_id = results.get(tc.VAR_ROAD_ID, "")
                lane_position = results.get(tc.VAR_LANEPOSITION, 0.0)
                accel = results.get(tc.VAR_ACCELERATION, 0.0)
            else:
                try:
                    speed = traci.vehicle.getSpeed(veh_id)
                    road_id = traci.vehicle.getRoadID(veh_id)
                    lane_position = traci.vehicle.getLanePosition(veh_id)
                    accel = traci.vehicle.getAcceleration(veh_id)
                except traci.exceptions.TraCIException as e:
                    logger.warning(f"Failed to query vehicle '{veh_id}': {e}")
                    continue

            # Sync speed and route location
            vehicle.speed = speed

            # Find the active edge
            edge = self.network.edges.get(road_id)
            if edge:
                distance_covered = speed * dt
                energy = vehicle.battery.calculate_consumption(
                    distance_m=distance_covered,
                    speed_m_s=speed,
                    acceleration_m_s2=accel,
                    gradient_rad=edge.gradient_rad,
                )
                vehicle._apply_energy_draw(energy)

                if road_id in vehicle.current_route:
                    vehicle.current_edge_idx = vehicle.current_route.index(road_id)
                vehicle.distance_on_current_edge = lane_position

            # Enforce stop if stranded
            if vehicle.state == VehicleState.STRANDED:
                try:
                    traci.vehicle.setSpeed(veh_id, 0.0)
                    logger.warning(
                        f"Vehicle '{veh_id}' is stranded (SoC=0.0). "
                        "Enforcing stop in SUMO."
                    )
                except traci.exceptions.TraCIException as e:
                    logger.error(
                        f"Failed to enforce stop on vehicle '{veh_id}': {e}"
                    )

        return arrived_ids

    def sync_to_sumo(self) -> None:
        """Synchronizes events and vehicle routes from Python to SUMO."""
        # 1. Sync road closures
        for edge_id, edge in self.network.edges.items():
            if edge.is_closed and edge_id not in self._synced_closed_edges:
                try:
                    traci.edge.setDisallowed(edge_id, ["passenger", "evehicle"])
                    self._synced_closed_edges.add(edge_id)
                    logger.info(f"Synchronized closure of edge '{edge_id}' to SUMO.")
                except traci.exceptions.TraCIException as e:
                    logger.warning(
                        f"Failed to synchronize closure for edge '{edge_id}': {e}"
                    )

        # 2. Sync vehicle routes
        for veh_id, vehicle in self.vehicle_registry.items():
            if vehicle.state != VehicleState.EN_ROUTE:
                continue

            # Sync route if changed
            last_route = self._last_synced_routes.get(veh_id)
            if last_route != vehicle.current_route:
                route_slice = vehicle.current_route[vehicle.current_edge_idx :]
                if len(route_slice) >= self.MIN_ROUTE_LENGTH:
                    try:
                        traci.vehicle.setRoute(veh_id, route_slice)
                        self._last_synced_routes[veh_id] = list(
                            vehicle.current_route
                        )
                        logger.info(
                            f"Pushed route update for vehicle '{veh_id}': {route_slice}"
                        )
                    except traci.exceptions.TraCIException as e:
                        logger.warning(
                            f"Failed to set route for vehicle '{veh_id}': {e}"
                        )
