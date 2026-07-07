from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class PacketPriority(StrEnum):
    """Priority level for V2X packet processing and routing."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PacketType(StrEnum):
    """Functional categorization of V2X communication packets."""

    ROUTINE = "ROUTINE"
    TRAFFIC_UPDATE = "TRAFFIC_UPDATE"
    CHARGING_UPDATE = "CHARGING_UPDATE"
    EMERGENCY = "EMERGENCY"


class RoutineTelemetryPayload(BaseModel):
    """Telemetry information shared routinely between vehicles."""

    speed_m_s: float = Field(..., ge=0.0)
    soc: float = Field(..., ge=0.0, le=1.0)


class TrafficUpdatePayload(BaseModel):
    """Local traffic conditions and speed changes detected by nodes or vehicles."""

    edge_id: str
    speed_reduction_factor: float = Field(..., ge=0.0, le=1.0)
    is_closed: bool


class ChargingUpdatePayload(BaseModel):
    """Real-time charging queue status and estimated delay times."""

    station_id: str
    queue_length: int = Field(..., ge=0)
    estimated_wait_time: float = Field(..., ge=0.0)


class EmergencyPayload(BaseModel):
    """Universal cross-brand emergency protocol payload."""

    incident_id: str
    epicenter_x: float
    epicenter_y: float
    hazard_radius: float = Field(..., ge=0.0)
    hazard_intensity: float = Field(..., ge=0.0, le=1.0)
    affected_edges: list[str]
    ambulance_speed_m_s: float | None = Field(default=None, ge=0.0)


# Union type for strongly typed payload field validation
PacketPayload = (
    RoutineTelemetryPayload
    | TrafficUpdatePayload
    | ChargingUpdatePayload
    | EmergencyPayload
)


class Packet(BaseModel):
    """A strongly typed V2X network message."""

    packet_id: str = Field(..., description="Unique packet identifier")
    sender_id: str = Field(
        ..., description="Identifier of the transmitting transceiver"
    )
    packet_type: PacketType = Field(..., description="Type of packet payload")
    priority: PacketPriority = Field(..., description="Transmission priority")
    timestamp: float = Field(..., description="Simulation time of packet transmission")
    ttl: int = Field(default=3, description="Time to Live (max hops remaining)")
    payload: PacketPayload = Field(..., description="Strongly-typed payload data")

    @field_validator("ttl")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Validates that Time-to-Live is positive."""
        if v <= 0:
            raise ValueError(f"TTL must be greater than zero: {v}")
        return v
