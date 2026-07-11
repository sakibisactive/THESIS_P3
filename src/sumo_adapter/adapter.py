"""SUMO adapter layer for parsing XML networks and trip definitions."""

import xml.etree.ElementTree as ET

import sumolib  # type: ignore[import-untyped]

from src.core.battery import BatteryModel
from src.core.network import Edge, Network, Node
from src.core.vehicle import Vehicle
from src.utils.config import BatteryConfig


class SumoAdapter:
    """Translates SUMO network XML and demand definitions into simulator models."""

    @staticmethod
    def parse_network(net_xml_path: str) -> Network:
        """Parses a SUMO .net.xml file and constructs a Network instance.

        Args:
            net_xml_path: Path to the SUMO network file.

        Returns:
            Network: The populated Network instance.
        """
        # Read SUMO network using sumolib
        net = sumolib.net.readNet(net_xml_path)
        network = Network()

        # Parse Junctions (Nodes)
        for junction in net.getNodes():
            node_id = junction.getID()
            x, y = junction.getCoord()
            network.add_node(Node(node_id=node_id, x=x, y=y))

        # Parse Roads (Edges)
        for edge in net.getEdges():
            edge_id = edge.getID()
            from_node = edge.getFromNode().getID()
            to_node = edge.getToNode().getID()
            length = edge.getLength()
            speed_limit = edge.getSpeed()

            # Add to network
            edge_obj = Edge(
                edge_id=edge_id,
                from_node=from_node,
                to_node=to_node,
                length=length,
                speed_limit=speed_limit,
                gradient_rad=0.0,  # SUMO network paths are flat by default
            )
            # Retrieve connected outgoing edge IDs
            edge_obj.allowed_transitions = {
                out_edge.getID() for out_edge in edge.getOutgoing()
            }
            network.add_edge(edge_obj)

        return network

    @staticmethod
    def parse_trips(
        trips_xml_path: str, battery_config: BatteryConfig, network: Network
    ) -> list[Vehicle]:
        """Parses a SUMO trips.xml or routes.xml file to generate Vehicle objects.

        Handles both <trip> and <vehicle> XML elements.

        Args:
            trips_xml_path: Path to the SUMO routes/trips file.
            battery_config: Config for EV battery consumption logic.
            network: Network graph instance to resolve edge coordinates.

        Returns:
            list[Vehicle]: List of configured electric vehicle instances.
        """
        vehicles = []
        tree = ET.parse(trips_xml_path)
        root = tree.getroot()

        battery = BatteryModel(battery_config)

        # Handle both <trip> and <vehicle> tags
        for element in root.findall(".//trip") + root.findall(".//vehicle"):
            veh_id = element.attrib.get("id")
            if not veh_id:
                continue

            from_edge_id = element.attrib.get("from")
            to_edge_id = element.attrib.get("to")

            # If nested <route> is used:
            route_elem = element.find("route")
            if route_elem is not None:
                edges_str = route_elem.attrib.get("edges", "")
                edges = edges_str.split()
                if edges:
                    from_edge_id = edges[0]
                    to_edge_id = edges[-1]

            if not from_edge_id or not to_edge_id:
                continue

            # Resolve origin and destination nodes from edges
            from_edge = network.edges.get(from_edge_id)
            to_edge = network.edges.get(to_edge_id)

            if from_edge and to_edge:
                # Spawn at from_node of origin edge, dest is to_node of destination edge
                origin_node = from_edge.from_node
                dest_node = to_edge.to_node

                # Standard initial SoC of 0.8
                veh = Vehicle(
                    vehicle_id=veh_id,
                    origin_node_id=origin_node,
                    destination_node_id=dest_node,
                    initial_soc=0.8,
                    battery=battery,
                )

                # If routes are predefined in the XML, assign them
                if route_elem is not None:
                    veh.assign_route(edges)

                vehicles.append(veh)

        return vehicles
