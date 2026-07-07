from typing import TYPE_CHECKING

from src.communication.packet import (
    EmergencyPayload,
    Packet,
    PacketPriority,
    PacketType,
)
from src.communication.transceiver import Transceiver
from src.core.battery import BatteryModel
from src.core.network import Network
from src.core.vehicle import Vehicle, VehicleState

if TYPE_CHECKING:
    from src.communication.channel import CommunicationChannel


class Ambulance(Vehicle):
    """Represents an emergency ambulance vehicle capable of V2X beaconing."""

    def __init__(
        self,
        vehicle_id: str,
        origin_node_id: str,
        destination_node_id: str,
        initial_soc: float,
        battery: BatteryModel,
        speed_m_s: float = 25.0,
        v2v_range_m: float = 300.0,
        v2i_range_m: float = 500.0,
    ) -> None:
        """Initializes the Ambulance vehicle.

        Args:
            vehicle_id: Unique string identifier for the ambulance.
            origin_node_id: Start node identifier.
            destination_node_id: End node identifier.
            initial_soc: Starting battery State of Charge.
            battery: The vehicle battery model.
            speed_m_s: Operating speed target.
            v2v_range_m: Range for V2V communication.
            v2i_range_m: Range for V2I communication.
        """
        super().__init__(
            vehicle_id=vehicle_id,
            origin_node_id=origin_node_id,
            destination_node_id=destination_node_id,
            initial_soc=initial_soc,
            battery=battery,
        )
        self.speed_m_s = speed_m_s
        self.v2v_range_m = v2v_range_m
        self.v2i_range_m = v2i_range_m

        # Dynamic reference to network for transceiver coordinates callback
        self.network: Network | None = None

        self.transceiver = Transceiver(
            transceiver_id=f"tx_amb_{vehicle_id}",
            is_rsu=False,
            v2v_range=v2v_range_m,
            v2i_range=v2i_range_m,
            position_provider=self.get_transceiver_position,
        )

        self.beacon_interval: float = 1.0  # broadcast beacon every 1.0s
        self.last_beacon_time: float = -999.0
        self.is_emergency_beacon_active: bool = True

    def get_transceiver_position(self) -> tuple[float, float]:
        """Provides the current coordinates of the ambulance.

        Matches the Transceiver position provider signature.

        Returns:
            tuple[float, float]: current (x, y) coordinates.
        """
        if self.network is not None:
            return self.get_position(self.network)
        return 0.0, 0.0

    def step_beacon(
        self,
        current_time: float,
        channel: "CommunicationChannel",
        network: Network,
    ) -> None:
        """Generates and broadcasts periodic emergency signals to surrounding vehicles.

        Args:
            current_time: Current simulation timestamp.
            channel: Communication channel to transmit through.
            network: The road network structure.
        """
        self.network = network
        if not self.is_emergency_beacon_active or self.state != VehicleState.EN_ROUTE:
            return

        if current_time - self.last_beacon_time >= self.beacon_interval:
            x, y = self.get_position(network)
            if not self.current_route:
                return

            # Include current edge and next 2 upcoming edges in the route
            start_idx = self.current_edge_idx
            upcoming = self.current_route[start_idx : start_idx + 3]

            payload = EmergencyPayload(
                incident_id=f"amb_beacon_{self.id}",
                epicenter_x=x,
                epicenter_y=y,
                hazard_radius=self.v2v_range_m,
                hazard_intensity=1.0,
                affected_edges=upcoming,
                ambulance_speed_m_s=self.speed_m_s,
            )

            packet = Packet(
                packet_id=f"beacon_{self.id}_{int(current_time)}",
                sender_id=self.transceiver.id,
                packet_type=PacketType.EMERGENCY,
                priority=PacketPriority.HIGH,
                timestamp=current_time,
                ttl=3,
                payload=payload,
            )

            self.transceiver.broadcast(packet, channel, current_time)
            self.last_beacon_time = current_time

    def step_movement_ambulance(self, dt: float, network: Network) -> None:
        """Moves the ambulance under free-flow speeds.

        Args:
            dt: Simulation step time delta.
            network: Road network.
        """
        if self.state != VehicleState.EN_ROUTE:
            return

        if not self.current_route:
            self.state = VehicleState.ARRIVED
            return

        edge_id = self.current_route[self.current_edge_idx]
        edge = network.edges.get(edge_id)
        if edge:
            # Traveling at maximum free flow (ignoring traffic congestion)
            speed = min(self.speed_m_s, edge.current_speed_limit)
        else:
            speed = self.speed_m_s

        super().step_movement(
            dt_seconds=dt,
            current_speed_m_s=speed,
            current_acceleration_m_s2=0.0,
            network=network,
        )
