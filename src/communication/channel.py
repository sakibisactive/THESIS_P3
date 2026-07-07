import math
import random

from pydantic import BaseModel, Field

from src.communication.packet import Packet
from src.communication.transceiver import Transceiver
from src.utils.config import BoundingBox, CommunicationConfig


class PendingDelivery(BaseModel):
    """Represents a V2X packet scheduled for future delivery due to network latency."""

    packet: Packet = Field(..., description="The packet being transmitted")
    receiver_id: str = Field(..., description="Identifier of the target transceiver")
    delivery_time: float = Field(..., description="Simulation timestamp for delivery")


class CommunicationChannel:
    """Manages propagation, packet loss, and latency of V2X packets."""

    def __init__(self, config: CommunicationConfig, seed: int | None = None) -> None:
        """Initializes the CommunicationChannel.

        Args:
            config: The validated CommunicationConfig configuration parameters.
            seed: Optional seed for the channel's local random number generator.
        """
        self.config = config
        self.transceivers: dict[str, Transceiver] = {}
        self.pending_deliveries: list[PendingDelivery] = []
        self.active_blackout_zones: list[BoundingBox] = []
        self._rng = random.Random(seed)

    def register_transceiver(self, transceiver: Transceiver) -> None:
        """Registers a transceiver with the channel.

        Args:
            transceiver: The Transceiver instance.
        """
        self.transceivers[transceiver.id] = transceiver

    def deregister_transceiver(self, transceiver_id: str) -> None:
        """Removes a transceiver from the channel.

        Args:
            transceiver_id: Unique identifier of the transceiver to remove.
        """
        self.transceivers.pop(transceiver_id, None)

    def transmit(self, sender_id: str, packet: Packet, current_time: float) -> None:
        """Transmits a packet to all eligible transceivers in range.

        Applies regional blackouts, range limits, packet loss, and schedules
        delivery based on propagation speed and processing latency.

        Args:
            sender_id: ID of the transceiver initiating the transmission.
            packet: The Packet instance being transmitted.
            current_time: The current simulation time in seconds.
        """
        sender = self.transceivers.get(sender_id)
        if not sender:
            return

        sender_pos = sender.get_position()

        # Check if the sender is currently inside a communication blackout zone
        if self._is_in_blackout(sender_pos[0], sender_pos[1], current_time):
            return

        for receiver in self.transceivers.values():
            if receiver.id == sender_id:
                continue

            receiver_pos = receiver.get_position()

            # Check if the receiver is currently inside a communication blackout zone
            if self._is_in_blackout(receiver_pos[0], receiver_pos[1], current_time):
                continue

            # Calculate spatial Euclidean distance between transceivers
            dx = receiver_pos[0] - sender_pos[0]
            dy = receiver_pos[1] - sender_pos[1]
            distance = math.sqrt(dx * dx + dy * dy)

            # Determine transmission range based on V2V or V2I communication type
            is_v2i = sender.is_rsu or receiver.is_rsu
            max_range = sender.v2i_range if is_v2i else sender.v2v_range
            if distance > max_range:
                continue

            # Exponential distance-based packet loss probability calculation
            # P(loss) = 1 - exp(-gamma * distance)
            loss_prob = 1.0 - math.exp(-self.config.base_packet_loss_rate * distance)
            if self._rng.random() < loss_prob:
                continue

            # Calculate network latency: base_delay + propagation_delay + random_jitter
            jitter = self._rng.uniform(
                -self.config.latency_jitter_s, self.config.latency_jitter_s
            )
            propagation_delay = distance / self.config.propagation_speed_m_s
            latency = max(0.0, self.config.base_latency_s + propagation_delay + jitter)

            delivery_time = current_time + latency

            # Schedule the packet for delivery in the future
            self.pending_deliveries.append(
                PendingDelivery(
                    packet=packet,
                    receiver_id=receiver.id,
                    delivery_time=delivery_time,
                )
            )

    def step(self, current_time: float) -> None:
        """Processes pending deliveries scheduled at or before current_time.

        Args:
            current_time: The current simulation time in seconds.
        """
        # Partition deliveries: those to deliver now vs those to keep pending
        to_deliver: list[PendingDelivery] = []
        keep_pending: list[PendingDelivery] = []

        for delivery in self.pending_deliveries:
            if delivery.delivery_time <= current_time:
                to_deliver.append(delivery)
            else:
                keep_pending.append(delivery)

        self.pending_deliveries = keep_pending

        # Deliver packets to target transceivers
        for delivery in to_deliver:
            receiver = self.transceivers.get(delivery.receiver_id)
            if receiver:
                receiver.receive(delivery.packet, current_time, self)

    def _is_in_blackout(self, x: float, y: float, t: float) -> bool:
        """Determines if a location is under a regional blackout at the given time."""
        # Check dynamic blackout zones (e.g. from Infrastructure Failures)
        for area in self.active_blackout_zones:
            if area.min_x <= x <= area.max_x and area.min_y <= y <= area.max_y:
                return True

        cfg = self.config
        if cfg.blackout_start_time is None or cfg.blackout_end_time is None:
            return False
        if not (cfg.blackout_start_time <= t <= cfg.blackout_end_time):
            return False
        if cfg.blackout_area is None:
            return False

        area = cfg.blackout_area
        return area.min_x <= x <= area.max_x and area.min_y <= y <= area.max_y
