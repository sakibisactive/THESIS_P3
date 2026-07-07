"""V2X Communication Layer for the E³-Hybrid Swarm Routing Simulator.

Provides classes and models for V2V/V2I message exchange, channel propagation
physics, and regional communication blackout simulation.
"""

from src.communication.channel import CommunicationChannel
from src.communication.packet import (
    ChargingUpdatePayload,
    EmergencyPayload,
    Packet,
    PacketPayload,
    PacketPriority,
    PacketType,
    RoutineTelemetryPayload,
    TrafficUpdatePayload,
)
from src.communication.transceiver import Transceiver

__all__ = [
    "CommunicationChannel",
    "Transceiver",
    "Packet",
    "PacketType",
    "PacketPriority",
    "PacketPayload",
    "RoutineTelemetryPayload",
    "TrafficUpdatePayload",
    "ChargingUpdatePayload",
    "EmergencyPayload",
]
