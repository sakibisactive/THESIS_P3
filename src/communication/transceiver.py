from collections.abc import Callable
from typing import TYPE_CHECKING

from src.communication.packet import Packet

if TYPE_CHECKING:
    from src.communication.channel import CommunicationChannel


class Transceiver:
    """Represents a V2X wireless transceiver for vehicles or RSU nodes."""

    def __init__(
        self,
        transceiver_id: str,
        is_rsu: bool,
        v2v_range: float,
        v2i_range: float,
        position_provider: Callable[[], tuple[float, float]],
    ) -> None:
        """Initializes the Transceiver.

        Args:
            transceiver_id: Unique string identifier for the transceiver.
            is_rsu: True if this is a Roadside Unit (RSU), False for vehicle OBU.
            v2v_range: Range for Vehicle-to-Vehicle communication (meters).
            v2i_range: Range for Vehicle-to-Infrastructure communication (meters).
            position_provider: Callback function returning current (x, y) coordinates.
        """
        self.id = transceiver_id
        self.is_rsu = is_rsu
        self.v2v_range = v2v_range
        self.v2i_range = v2i_range
        self.position_provider = position_provider

        # Duplicate suppression and message inbox
        self.received_packet_ids: set[str] = set()
        self.received_packets: list[Packet] = []

    def get_position(self) -> tuple[float, float]:
        """Retrieves the current spatial coordinates of the transceiver.

        Returns:
            tuple[float, float]: (x, y) coordinates in meters.
        """
        return self.position_provider()

    @property
    def range(self) -> float:
        """Gets the operational range of the transceiver depending on its type."""
        return self.v2i_range if self.is_rsu else self.v2v_range

    def broadcast(
        self, packet: Packet, channel: "CommunicationChannel", current_time: float
    ) -> None:
        """Initiates a broadcast of a packet through the communication channel.

        Args:
            packet: The Packet instance to broadcast.
            channel: The CommunicationChannel managing network propagation.
            current_time: The current simulation time in seconds.
        """
        self.received_packet_ids.add(packet.packet_id)
        channel.transmit(sender_id=self.id, packet=packet, current_time=current_time)

    def receive(
        self, packet: Packet, current_time: float, channel: "CommunicationChannel"
    ) -> bool:
        """Receives a packet from the channel, applying duplicate suppression.

        If the packet is valid and has remaining TTL, it schedules a
        rebroadcast (forwarding) through the channel.

        Args:
            packet: The Packet instance being received.
            current_time: The current simulation time in seconds.
            channel: The CommunicationChannel managing network propagation.

        Returns:
            bool: True if the packet was successfully received (new),
                  False if ignored (duplicate).
        """
        if packet.packet_id in self.received_packet_ids:
            return False

        self.received_packet_ids.add(packet.packet_id)
        self.received_packets.append(packet)

        # Forward the message (rebroadcast) if TTL is greater than 1
        if packet.ttl > 1:
            forwarded_packet = packet.model_copy(
                update={
                    "ttl": packet.ttl - 1,
                    "timestamp": current_time,
                }
            )
            # Forwarding is sent from this transceiver's perspective
            channel.transmit(
                sender_id=self.id,
                packet=forwarded_packet,
                current_time=current_time,
            )

        return True

    def clear_inbox(self) -> None:
        """Clears the inbox of received packets."""
        self.received_packets.clear()

    def __repr__(self) -> str:
        pos = self.get_position()
        return (
            f"Transceiver(id={self.id}, rsu={self.is_rsu}, "
            f"pos=({pos[0]:.1f}, {pos[1]:.1f}), inbox={len(self.received_packets)})"
        )
