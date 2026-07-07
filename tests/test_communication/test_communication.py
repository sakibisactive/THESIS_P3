import pytest

from src.communication.channel import CommunicationChannel
from src.communication.packet import (
    ChargingUpdatePayload,
    EmergencyPayload,
    Packet,
    PacketPriority,
    PacketType,
    RoutineTelemetryPayload,
    TrafficUpdatePayload,
)
from src.communication.transceiver import Transceiver
from src.utils.config import BoundingBox, CommunicationConfig


@pytest.fixture
def comm_config() -> CommunicationConfig:
    return CommunicationConfig(
        v2v_range_m=300.0,
        v2i_range_m=500.0,
        base_packet_loss_rate=0.0,  # 0.0 loss rate for deterministic range tests
        base_latency_s=0.005,
        latency_jitter_s=0.002,
        propagation_speed_m_s=3.0e8,
        blackout_start_time=10.0,
        blackout_end_time=20.0,
        blackout_area=BoundingBox(min_x=10.0, min_y=10.0, max_x=50.0, max_y=50.0),
    )


@pytest.fixture
def channel(comm_config: CommunicationConfig) -> CommunicationChannel:
    return CommunicationChannel(comm_config, seed=42)


def test_packet_payload_validation() -> None:
    # 1. Telemetry
    telemetry = RoutineTelemetryPayload(speed_m_s=15.5, soc=0.75)
    packet_tel = Packet(
        packet_id="p1",
        sender_id="v1",
        packet_type=PacketType.ROUTINE,
        priority=PacketPriority.LOW,
        timestamp=0.0,
        ttl=3,
        payload=telemetry,
    )
    assert packet_tel.packet_id == "p1"
    assert isinstance(packet_tel.payload, RoutineTelemetryPayload)
    assert packet_tel.payload.speed_m_s == 15.5

    # 2. Traffic
    traffic = TrafficUpdatePayload(
        edge_id="e1", speed_reduction_factor=0.5, is_closed=False
    )
    packet_traf = Packet(
        packet_id="p2",
        sender_id="v1",
        packet_type=PacketType.TRAFFIC_UPDATE,
        priority=PacketPriority.MEDIUM,
        timestamp=1.0,
        payload=traffic,
    )
    assert isinstance(packet_traf.payload, TrafficUpdatePayload)
    assert packet_traf.payload.edge_id == "e1"

    # 3. Charging
    charging = ChargingUpdatePayload(
        station_id="cs1", queue_length=3, estimated_wait_time=900.0
    )
    packet_chg = Packet(
        packet_id="p3",
        sender_id="v1",
        packet_type=PacketType.CHARGING_UPDATE,
        priority=PacketPriority.MEDIUM,
        timestamp=2.0,
        payload=charging,
    )
    assert isinstance(packet_chg.payload, ChargingUpdatePayload)
    assert packet_chg.payload.estimated_wait_time == 900.0

    # 4. Emergency (universal cross-brand emergency protocol)
    emergency = EmergencyPayload(
        incident_id="inc_1",
        epicenter_x=25.0,
        epicenter_y=30.0,
        hazard_radius=150.0,
        hazard_intensity=0.9,
        affected_edges=["e1", "e2"],
        ambulance_speed_m_s=25.0,
    )
    packet_em = Packet(
        packet_id="p4",
        sender_id="v1",
        packet_type=PacketType.EMERGENCY,
        priority=PacketPriority.HIGH,
        timestamp=3.0,
        payload=emergency,
    )
    assert isinstance(packet_em.payload, EmergencyPayload)
    assert packet_em.payload.incident_id == "inc_1"
    assert packet_em.payload.affected_edges == ["e1", "e2"]


def test_packet_invalid_ttl() -> None:
    with pytest.raises(ValueError, match="TTL must be greater than zero"):
        Packet(
            packet_id="p_bad",
            sender_id="v1",
            packet_type=PacketType.ROUTINE,
            priority=PacketPriority.LOW,
            timestamp=0.0,
            ttl=0,
            payload=RoutineTelemetryPayload(speed_m_s=10.0, soc=0.5),
        )


def test_transceiver_properties() -> None:
    tx_veh = Transceiver(
        transceiver_id="v1",
        is_rsu=False,
        v2v_range=300.0,
        v2i_range=500.0,
        position_provider=lambda: (100.0, 200.0),
    )
    assert tx_veh.id == "v1"
    assert tx_veh.is_rsu is False
    assert tx_veh.get_position() == (100.0, 200.0)
    assert tx_veh.range == 300.0

    tx_rsu = Transceiver(
        transceiver_id="r1",
        is_rsu=True,
        v2v_range=300.0,
        v2i_range=500.0,
        position_provider=lambda: (0.0, 0.0),
    )
    assert tx_rsu.range == 500.0


def test_channel_registration(channel: CommunicationChannel) -> None:
    tx = Transceiver(
        transceiver_id="v1",
        is_rsu=False,
        v2v_range=100.0,
        v2i_range=200.0,
        position_provider=lambda: (0.0, 0.0),
    )
    channel.register_transceiver(tx)
    assert "v1" in channel.transceivers

    channel.deregister_transceiver("v1")
    assert "v1" not in channel.transceivers


def test_channel_transmission_range_and_delivery(
    channel: CommunicationChannel,
) -> None:
    # A (0,0) Vehicle, B (250, 0) Vehicle, C (400, 0) Vehicle
    # D (450, 0) RSU
    tx_a = Transceiver("A", False, 300.0, 500.0, lambda: (0.0, 0.0))
    tx_b = Transceiver("B", False, 300.0, 500.0, lambda: (250.0, 0.0))
    tx_c = Transceiver("C", False, 300.0, 500.0, lambda: (400.0, 0.0))
    tx_d = Transceiver("D", True, 300.0, 500.0, lambda: (450.0, 0.0))

    for tx in [tx_a, tx_b, tx_c, tx_d]:
        channel.register_transceiver(tx)

    packet = Packet(
        packet_id="p1",
        sender_id="A",
        packet_type=PacketType.ROUTINE,
        priority=PacketPriority.LOW,
        timestamp=0.0,
        ttl=1,  # TTL=1 to prevent forwarding in this test
        payload=RoutineTelemetryPayload(speed_m_s=10.0, soc=0.9),
    )

    # A broadcasts at time=0.0
    tx_a.broadcast(packet, channel, 0.0)

    # Let's check pending deliveries
    # Range of A (V2V) is 300m.
    # B is 250m away -> In range (V2V). Should be scheduled.
    # C is 400m away -> Out of range (V2V). Should not be scheduled.
    # D is 450m away -> In range (V2I range of A is 500m). Should be scheduled.
    receivers = {d.receiver_id for d in channel.pending_deliveries}
    assert "B" in receivers
    assert "D" in receivers
    assert "C" not in receivers

    # Check latencies are scheduled
    for delivery in channel.pending_deliveries:
        assert delivery.delivery_time > 0.0
        # Latency bounds: base (0.005s) + propagation + jitter (-0.002 to +0.002)
        # Minimum possible latency = 0.005 + 0.0 - 0.002 = 0.003
        assert delivery.delivery_time >= 0.003

    # Fast forward time to 1.0s to deliver all scheduled packets
    channel.step(1.0)
    assert len(channel.pending_deliveries) == 0
    assert len(tx_b.received_packets) == 1
    assert len(tx_d.received_packets) == 1
    assert len(tx_c.received_packets) == 0


def test_channel_blackout(channel: CommunicationChannel) -> None:
    # A (0,0) outside, B (25, 25) inside blackout area: [10, 50] x [10, 50]
    tx_a = Transceiver("A", False, 300.0, 500.0, lambda: (0.0, 0.0))
    tx_b = Transceiver("B", False, 300.0, 500.0, lambda: (25.0, 25.0))

    channel.register_transceiver(tx_a)
    channel.register_transceiver(tx_b)

    packet = Packet(
        packet_id="p1",
        sender_id="A",
        packet_type=PacketType.ROUTINE,
        priority=PacketPriority.LOW,
        timestamp=15.0,
        ttl=1,
        payload=RoutineTelemetryPayload(speed_m_s=10.0, soc=0.9),
    )

    # 1. Transmit at t=5.0 (outside blackout time window [10.0, 20.0])
    tx_a.broadcast(packet, channel, 5.0)
    assert len(channel.pending_deliveries) == 1
    channel.pending_deliveries.clear()

    # 2. Transmit at t=15.0 (inside blackout time window)
    # B is inside the blackout area, so transmission to B must fail
    tx_a.broadcast(packet, channel, 15.0)
    assert len(channel.pending_deliveries) == 0


def test_transceiver_duplicate_suppression_and_forwarding(
    channel: CommunicationChannel,
) -> None:
    # A (0,0), B (100,0), C (200,0)
    # A sends a packet with TTL=2.
    # B receives it, decrements TTL to 1, and rebroadcasts.
    # C receives B's rebroadcast.
    # A receives B's rebroadcast but suppresses it (duplicate).
    tx_a = Transceiver("A", False, 150.0, 150.0, lambda: (0.0, 0.0))
    tx_b = Transceiver("B", False, 150.0, 150.0, lambda: (100.0, 0.0))
    tx_c = Transceiver("C", False, 150.0, 150.0, lambda: (200.0, 0.0))

    for tx in [tx_a, tx_b, tx_c]:
        channel.register_transceiver(tx)

    packet = Packet(
        packet_id="p_multi",
        sender_id="A",
        packet_type=PacketType.ROUTINE,
        priority=PacketPriority.LOW,
        timestamp=0.0,
        ttl=2,
        payload=RoutineTelemetryPayload(speed_m_s=12.0, soc=0.8),
    )

    # Step 0: A broadcasts
    tx_a.broadcast(packet, channel, 0.0)
    # Scheduled for B (C is out of A's range)
    assert len(channel.pending_deliveries) == 1
    assert channel.pending_deliveries[0].receiver_id == "B"

    # Step 1: Deliver to B (time passes to 0.1s)
    channel.step(0.1)

    # B received and rebroadcast it since ttl=2 > 1.
    # Rebroadcast from B should be scheduled for A and C (both 100m from B)
    assert len(tx_b.received_packets) == 1
    assert tx_b.received_packets[0].ttl == 2
    receivers = [d.receiver_id for d in channel.pending_deliveries]
    assert "A" in receivers
    assert "C" in receivers

    # Step 2: Deliver to A and C (time passes to 0.2s)
    channel.step(0.2)

    # C should have received B's broadcast
    assert len(tx_c.received_packets) == 1
    # A should NOT add a duplicate packet because of duplicate suppression
    assert len(tx_a.received_packets) == 0
    # No more pending broadcasts since forwarded packet TTL decremented to 1
    assert len(channel.pending_deliveries) == 0


def test_channel_packet_loss() -> None:
    # Set high loss rate: 0.5. At 100m, P(loss) = 1 - e^-50 = 1.0 (virtually 100% loss)
    config = CommunicationConfig(
        v2v_range_m=300.0,
        v2i_range_m=500.0,
        base_packet_loss_rate=0.5,
        base_latency_s=0.005,
        latency_jitter_s=0.002,
        propagation_speed_m_s=3.0e8,
    )
    chan = CommunicationChannel(config, seed=42)
    tx_a = Transceiver("A", False, 300.0, 500.0, lambda: (0.0, 0.0))
    tx_b = Transceiver("B", False, 300.0, 500.0, lambda: (100.0, 0.0))
    chan.register_transceiver(tx_a)
    chan.register_transceiver(tx_b)

    packet = Packet(
        packet_id="p1",
        sender_id="A",
        packet_type=PacketType.ROUTINE,
        priority=PacketPriority.LOW,
        timestamp=0.0,
        ttl=1,
        payload=RoutineTelemetryPayload(speed_m_s=10.0, soc=0.9),
    )
    tx_a.broadcast(packet, chan, 0.0)
    # Packet should be lost, so no pending deliveries are scheduled
    assert len(chan.pending_deliveries) == 0
