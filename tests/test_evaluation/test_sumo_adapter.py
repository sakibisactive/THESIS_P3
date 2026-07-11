"""Unit tests for the SumoAdapter layer."""

import os
from unittest.mock import MagicMock, patch
import pytest

from src.core.network import Network, Node, Edge
from src.utils.config import BatteryConfig
from src.sumo_adapter.adapter import SumoAdapter


def test_sumo_adapter_parse_network() -> None:
    """Verifies that SUMO junction/road elements are correctly parsed and loaded."""
    # Create mock Nodes from sumolib
    mock_node1 = MagicMock()
    mock_node1.getID.return_value = "n1"
    mock_node1.getCoord.return_value = (10.0, 20.0)

    mock_node2 = MagicMock()
    mock_node2.getID.return_value = "n2"
    mock_node2.getCoord.return_value = (110.0, 20.0)

    # Create mock Edges from sumolib
    mock_edge1 = MagicMock()
    mock_edge1.getID.return_value = "e1"
    mock_edge1.getFromNode().getID.return_value = "n1"
    mock_edge1.getToNode().getID.return_value = "n2"
    mock_edge1.getLength.return_value = 100.0
    mock_edge1.getSpeed.return_value = 15.0

    # Mock Net object
    mock_net = MagicMock()
    mock_net.getNodes.return_value = [mock_node1, mock_node2]
    mock_net.getEdges.return_value = [mock_edge1]

    # Patch sumolib.net.readNet to return our mock net
    with patch("sumolib.net.readNet", return_value=mock_net) as mock_read:
        net = SumoAdapter.parse_network("mock_net.xml")
        
        mock_read.assert_called_once_with("mock_net.xml")
        assert "n1" in net.nodes
        assert "n2" in net.nodes
        assert net.nodes["n1"].x == 10.0
        assert net.nodes["n1"].y == 20.0
        
        assert "e1" in net.edges
        assert net.edges["e1"].from_node == "n1"
        assert net.edges["e1"].to_node == "n2"
        assert net.edges["e1"].length == 100.0
        assert net.edges["e1"].speed_limit == 15.0


def test_sumo_adapter_parse_trips(tmp_path) -> None:
    """Verifies parsing of standard trips.xml and routes.xml file formats."""
    # Create a dummy network
    network = Network()
    network.add_node(Node("n1", 0.0, 0.0))
    network.add_node(Node("n2", 100.0, 0.0))
    network.add_edge(Edge("e1", "n1", "n2", 100.0, 15.0))
    
    # Write a mock trips.xml file
    trips_file = tmp_path / "trips.xml"
    trips_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
    <routes>
        <trip id="veh_0" depart="0.0" from="e1" to="e1"/>
        <vehicle id="veh_1" depart="10.0">
            <route edges="e1"/>
        </vehicle>
    </routes>
    """, encoding="utf-8")

    bat_config = BatteryConfig(
        capacity_kwh=60.0,
        mass_kg=1800.0,
        efficiency=0.9,
        drag_coeff=0.3,
        frontal_area=2.2,
        rolling_res_coeff=0.015,
        regen_efficiency=0.7
    )

    vehs = SumoAdapter.parse_trips(str(trips_file), bat_config, network)

    assert len(vehs) == 2
    
    # veh_0
    assert vehs[0].id == "veh_0"
    assert vehs[0].origin_node_id == "n1"
    assert vehs[0].destination_node_id == "n2"
    assert vehs[0].soc == 0.8
    
    # veh_1
    assert vehs[1].id == "veh_1"
    assert vehs[1].origin_node_id == "n1"
    assert vehs[1].destination_node_id == "n2"
    assert vehs[1].current_route == ["e1"]
