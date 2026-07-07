from src.communication.channel import CommunicationChannel
from src.core.battery import BatteryModel
from src.core.network import ChargingStation, Network
from src.core.vehicle import Vehicle, VehicleState
from src.emergency.ambulance import Ambulance
from src.emergency.corridor import EmergencyCorridor
from src.emergency.failure import InfrastructureFailure
from src.emergency.incident import Incident
from src.emergency.scheduler import EventScheduler, SimulationEvent


class SimulationContext:
    """Encapsulates references to all mutable simulator components during steps."""

    def __init__(
        self,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
        vehicles: dict[str, Vehicle],
    ) -> None:
        """Initializes the simulation context wrapper.

        Args:
            network: Road network graph.
            channel: Signal propagation channel.
            charging_stations: Dictionary of charging station objects.
            vehicles: Dictionary of standard vehicles.
        """
        self.network = network
        self.channel = channel
        self.charging_stations = charging_stations
        self.vehicles = vehicles


class ScenarioManager:
    """Coordinates and executes all emergency system events and updates."""

    def __init__(self) -> None:
        self.scheduler = EventScheduler()
        self.active_incidents: dict[str, Incident] = {}
        self.active_failures: dict[str, InfrastructureFailure] = {}
        self.active_closures: dict[str, RoadClosure] = {}
        self.ambulances: dict[str, Ambulance] = {}

    def step(
        self,
        dt: float,
        current_time: float,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
        vehicles: dict[str, Vehicle],
    ) -> None:
        """Updates the state of all emergency components at the current time step.

        Steps scheduler events, grows hazards, caps edge speeds, runs ambulances,
        and manages lane-clearance corridors.

        Args:
            dt: Time step duration in seconds.
            current_time: Current simulation timestamp.
            network: Road network.
            channel: Communication channel.
            charging_stations: Dict of charging stations.
            vehicles: Dict of all active vehicles.
        """
        context = SimulationContext(network, channel, charging_stations, vehicles)

        # 1. Process scheduled event triggers
        self.scheduler.step(current_time, self, context)

        # 2. Reset dynamic speed limits for all edges before applying active hazards
        for edge in network.edges.values():
            edge.speed_reduction_factor = 1.0

        # 3. Apply active incidents (hazards)
        self._update_incidents(current_time, network)

        # 4. Update infrastructure failures and road closures
        self._update_failures_and_closures(
            current_time, network, channel, charging_stations
        )

        # 5. Move ambulances and broadcast emergency beacons
        self._update_ambulances(dt, current_time, network, channel)

        # 6. Apply yielding corridor pulling-over rules on affected edges
        EmergencyCorridor.update_yield_states(vehicles, self.ambulances)

    def _update_incidents(self, current_time: float, network: Network) -> None:
        """Helper to process incident propagation and speed reduction factors."""
        for incident in list(self.active_incidents.values()):
            if incident.is_active(current_time):
                # Ensure coordinates are initialized
                if incident.epicenter_x == 0.0 and incident.epicenter_y == 0.0:
                    incident.initialize_epicenter_position(network)

                affected_edges = incident.get_affected_edges(network, current_time)
                for edge_id in affected_edges:
                    edge = network.edges.get(edge_id)
                    if edge:
                        # Cap speed reduction factor (smaller value = slower speed)
                        factor = max(0.0, 1.0 - incident.intensity)
                        edge.speed_reduction_factor = min(
                            edge.speed_reduction_factor, factor
                        )
            # Remove expired incidents from the active set
            elif current_time > (incident.start_time + incident.duration):
                self.active_incidents.pop(incident.id, None)

    def _update_failures_and_closures(
        self,
        current_time: float,
        network: Network,
        channel: CommunicationChannel,
        charging_stations: dict[str, ChargingStation],
    ) -> None:
        """Helper to update infrastructure failures and road closures."""
        # Update infrastructure failures
        for failure in list(self.active_failures.values()):
            failure.update(current_time, network, channel, charging_stations)
            if not failure.is_within_timeframe(current_time) and current_time > (
                failure.start_time + failure.duration
            ):
                self.active_failures.pop(failure.id, None)

        # Update road closures
        for closure in list(self.active_closures.values()):
            closure.update(current_time, network)
            if not closure.is_within_timeframe(current_time) and current_time > (
                closure.start_time + closure.duration
            ):
                self.active_closures.pop(closure.id, None)

    def _update_ambulances(
        self,
        dt: float,
        current_time: float,
        network: Network,
        channel: CommunicationChannel,
    ) -> None:
        """Helper to advance ambulance positions and beacon broadcasts."""
        for ambulance in list(self.ambulances.values()):
            if ambulance.state == VehicleState.EN_ROUTE:
                ambulance.step_movement_ambulance(dt, network)
                ambulance.step_beacon(current_time, channel, network)
            elif ambulance.state == VehicleState.ARRIVED:
                # Deregister arrived ambulance from communication channel
                channel.deregister_transceiver(ambulance.transceiver.id)
                self.ambulances.pop(ambulance.id, None)


# Concrete Event Classes
class SpawnIncidentEvent(SimulationEvent):
    """Event that triggers a spatiotemporal hazard incident in the scenario."""

    def __init__(self, incident: Incident) -> None:
        super().__init__(
            event_id=f"spawn_incident_{incident.id}",
            execution_time=incident.start_time,
            priority=10,  # high priority
        )
        self.incident = incident

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        self.incident.initialize_epicenter_position(context.network)
        manager.active_incidents[self.incident.id] = self.incident


class ResolveIncidentEvent(SimulationEvent):
    """Event that manually resolves/terminates a running incident."""

    def __init__(self, incident_id: str, resolve_time: float) -> None:
        super().__init__(
            event_id=f"resolve_incident_{incident_id}",
            execution_time=resolve_time,
            priority=9,
        )
        self.incident_id = incident_id

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        incident = manager.active_incidents.get(self.incident_id)
        if incident:
            incident.resolved = True
            manager.active_incidents.pop(self.incident_id, None)


class ApplyFailureEvent(SimulationEvent):
    """Event that triggers an infrastructure failure."""

    def __init__(self, failure: InfrastructureFailure) -> None:
        super().__init__(
            event_id=f"apply_failure_{failure.id}",
            execution_time=failure.start_time,
            priority=8,
        )
        self.failure = failure

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        manager.active_failures[self.failure.id] = self.failure
        self.failure.apply(context.network, context.channel, context.charging_stations)


class ReverseFailureEvent(SimulationEvent):
    """Event that forces early resolution/reversal of an infrastructure failure."""

    def __init__(self, failure_id: str, reverse_time: float) -> None:
        super().__init__(
            event_id=f"reverse_failure_{failure_id}",
            execution_time=reverse_time,
            priority=7,
        )
        self.failure_id = failure_id

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        failure = manager.active_failures.get(self.failure_id)
        if failure:
            failure.reverse(context.network, context.channel, context.charging_stations)
            manager.active_failures.pop(self.failure_id, None)


class DispatchAmbulanceEvent(SimulationEvent):
    """Event that spawns and dispatches an ambulance."""

    def __init__(
        self,
        ambulance_id: str,
        execution_time: float,
        origin_node_id: str,
        destination_node_id: str,
        battery_model: BatteryModel,
        route: list[str],
        speed_m_s: float = 25.0,
        v2v_range_m: float = 300.0,
        v2i_range_m: float = 500.0,
        initial_soc: float = 1.0,
    ) -> None:
        super().__init__(
            event_id=f"dispatch_ambulance_{ambulance_id}",
            execution_time=execution_time,
            priority=5,
        )
        self.ambulance_id = ambulance_id
        self.origin_node_id = origin_node_id
        self.destination_node_id = destination_node_id
        self.battery_model = battery_model
        self.route = route
        self.speed_m_s = speed_m_s
        self.v2v_range_m = v2v_range_m
        self.v2i_range_m = v2i_range_m
        self.initial_soc = initial_soc

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        ambulance = Ambulance(
            vehicle_id=self.ambulance_id,
            origin_node_id=self.origin_node_id,
            destination_node_id=self.destination_node_id,
            initial_soc=self.initial_soc,
            battery=self.battery_model,
            speed_m_s=self.speed_m_s,
            v2v_range_m=self.v2v_range_m,
            v2i_range_m=self.v2i_range_m,
        )
        ambulance.assign_route(self.route)

        # Register ambulance in manager and context collections
        manager.ambulances[self.ambulance_id] = ambulance
        context.vehicles[self.ambulance_id] = ambulance
        context.channel.register_transceiver(ambulance.transceiver)


class RoadClosure:
    """Models a dynamic road closure."""

    def __init__(
        self, closure_id: str, edge_id: str, start_time: float, duration: float
    ) -> None:
        self.id = closure_id
        self.edge_id = edge_id
        self.start_time = start_time
        self.duration = duration
        self.active = False

    def is_within_timeframe(self, current_time: float) -> bool:
        """Checks if the closure should be active at the given timestamp."""
        return self.start_time <= current_time <= (self.start_time + self.duration)

    def apply(self, network: Network) -> None:
        """Applies the closure, disabling the edge."""
        if self.active:
            return
        edge = network.edges.get(self.edge_id)
        if edge:
            edge.is_closed = True
            self.active = True

    def reverse(self, network: Network) -> None:
        """Reverses the closure, re-enabling the edge."""
        if not self.active:
            return
        edge = network.edges.get(self.edge_id)
        if edge:
            edge.is_closed = False
            self.active = False

    def update(self, current_time: float, network: Network) -> None:
        """Updates closure state based on simulation time."""
        if self.is_within_timeframe(current_time):
            self.apply(network)
        else:
            self.reverse(network)


class ApplyRoadClosureEvent(SimulationEvent):
    """Event that triggers a road closure."""

    def __init__(self, closure: RoadClosure) -> None:
        super().__init__(
            event_id=f"apply_closure_{closure.id}",
            execution_time=closure.start_time,
            priority=6,
        )
        self.closure = closure

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        manager.active_closures[self.closure.id] = self.closure
        self.closure.apply(context.network)


class ReverseRoadClosureEvent(SimulationEvent):
    """Event that forces early resolution/reversal of a road closure."""

    def __init__(self, closure_id: str, reverse_time: float) -> None:
        super().__init__(
            event_id=f"reverse_closure_{closure_id}",
            execution_time=reverse_time,
            priority=5,
        )
        self.closure_id = closure_id

    def execute(self, manager: ScenarioManager, context: SimulationContext) -> None:
        closure = manager.active_closures.get(self.closure_id)
        if closure:
            closure.reverse(context.network)
            manager.active_closures.pop(self.closure_id, None)
