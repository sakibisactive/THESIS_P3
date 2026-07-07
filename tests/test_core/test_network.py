import pytest

from src.core.network import ChargingStation, Edge, Network, Node
from src.utils.exceptions import NetworkError


def test_node_creation() -> None:
    node = Node("n1", 10.5, 20.7)
    assert node.id == "n1"
    assert node.x == 10.5
    assert node.y == 20.7
    assert "n1" in repr(node)


def test_edge_creation_and_speed_limit() -> None:
    edge = Edge("e1", "n1", "n2", 150.0, 13.89, 0.02)
    assert edge.id == "e1"
    assert edge.from_node == "n1"
    assert edge.to_node == "n2"
    assert edge.length == 150.0
    assert edge.speed_limit == 13.89
    assert edge.gradient_rad == 0.02
    assert edge.current_speed_limit == 13.89

    # Apply speed reduction
    edge.speed_reduction_factor = 0.5
    assert edge.current_speed_limit == 13.89 * 0.5

    # Close edge
    edge.is_closed = True
    assert edge.current_speed_limit == 0.0


def test_edge_creation_invalid() -> None:
    with pytest.raises(ValueError, match="length must be positive"):
        Edge("e1", "n1", "n2", -10.0, 10.0)

    with pytest.raises(ValueError, match="speed limit must be positive"):
        Edge("e1", "n1", "n2", 10.0, -5.0)


def test_charging_station_queue_operations() -> None:
    station = ChargingStation(
        "cs1", "n1", capacity=2, power_kw=50.0, base_price_per_kwh=0.3
    )
    assert station.id == "cs1"
    assert station.node_id == "n1"
    assert station.capacity == 2
    assert station.power_kw == 50.0
    assert station.base_price_per_kwh == 0.3
    assert len(station.queue) == 0
    assert len(station.charging_vehicles) == 0

    # Wait time estimation (empty queue)
    assert station.get_estimated_wait_time() == 0.0

    # Add vehicles to queue
    station.add_to_queue("v1")
    station.add_to_queue("v2")
    station.add_to_queue("v3")
    assert len(station.queue) == 3
    # Wait time estimation: 3 vehicles, capacity 2, avg duration 1800s
    # (3 / 2) * 1800 = 2700 seconds
    assert station.get_estimated_wait_time(avg_charge_duration_s=1800.0) == 2700.0

    # Start charging v1
    assert station.start_charging("v1") is True
    assert "v1" not in station.queue
    assert "v1" in station.charging_vehicles

    # Start charging v2
    assert station.start_charging("v2") is True
    assert len(station.charging_vehicles) == 2

    # Attempt to charge v3 (should fail since capacity is 2)
    assert station.start_charging("v3") is False
    assert "v3" in station.queue
    assert len(station.charging_vehicles) == 2

    # Stop charging v1 and transfer v3
    station.stop_charging("v1")
    assert "v1" not in station.charging_vehicles
    assert station.start_charging("v3") is True
    assert "v3" in station.charging_vehicles
    assert len(station.queue) == 0

    # Remove from queue directly
    station.add_to_queue("v4")
    assert "v4" in station.queue
    station.remove_from_queue("v4")
    assert "v4" not in station.queue


def test_network_add_and_queries() -> None:
    network = Network()
    n1 = Node("n1", 0.0, 0.0)
    n2 = Node("n2", 100.0, 0.0)
    network.add_node(n1)
    network.add_node(n2)

    e1 = Edge("e1", "n1", "n2", 100.0, 15.0)
    network.add_edge(e1)

    assert network.nodes["n1"] == n1
    assert network.edges["e1"] == e1

    # Missing node error
    e_bad = Edge("e_bad", "n1", "n3", 50.0, 10.0)
    with pytest.raises(NetworkError, match="Target node 'n3' not in network"):
        network.add_edge(e_bad)

    # Outgoing / incoming edge checks
    assert network.get_outgoing_edges("n1")[0] == e1
    assert len(network.get_outgoing_edges("n2")) == 0
    assert network.get_incoming_edges("n2")[0] == e1
    assert len(network.get_incoming_edges("n1")) == 0


def test_network_load_from_dict() -> None:
    data = {
        "nodes": [
            {"id": "n1", "x": 0.0, "y": 0.0},
            {"id": "n2", "x": 100.0, "y": 100.0},
        ],
        "edges": [
            {
                "id": "e1",
                "from": "n1",
                "to": "n2",
                "length": 141.4,
                "speed_limit": 15.0,
                "gradient_rad": 0.05,
            }
        ],
        "stations": [
            {
                "id": "cs1",
                "node_id": "n2",
                "capacity": 3,
                "power_kw": 120.0,
                "base_price_per_kwh": 0.4,
            }
        ],
    }

    network = Network.load_from_dict(data)
    assert "n1" in network.nodes
    assert "n2" in network.nodes
    assert "e1" in network.edges
    assert "cs1" in network.stations

    assert network.edges["e1"].gradient_rad == 0.05
    assert network.stations["cs1"].power_kw == 120.0
