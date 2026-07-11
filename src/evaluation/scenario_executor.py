"""Scenario execution engine driving simulator runs and data collection."""

import random
import time
from collections.abc import Callable

from src.communication.channel import CommunicationChannel
from src.communication.packet import (
    EmergencyPayload,
    Packet,
    PacketPriority,
    PacketType,
    TrafficUpdatePayload,
)
from src.communication.transceiver import Transceiver
from src.core.battery import BatteryModel
from src.core.network import ChargingStation, Network, Node
from src.core.vehicle import Vehicle, VehicleState
from src.emergency.scenario_loader import ScenarioLoader
from src.evaluation.metrics_collector import MetricsCollector
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.utils.config import ScenarioConfig


class ScenarioExecutor:
    """Orchestrates a standalone simulation scenario execution run."""

    def __init__(
        self,
        scenario_config: ScenarioConfig,
        router: Router,
        reroute_threshold_soc: float = 0.20,
        target_charge_soc: float = 1.00,
        traffic_seed: int = 42,
    ) -> None:
        """Initializes the execution engine.

        Args:
            scenario_config: Full ScenarioConfig containing environment rules.
            router: Pre-configured Router instance.
            reroute_threshold_soc: Battery SoC below which vehicle diverts to charge.
            target_charge_soc: Target battery SoC to reach before resuming trip.
            traffic_seed: Seed for random traffic generation.
        """
        self.config = scenario_config
        self.router = router
        self.reroute_threshold_soc = reroute_threshold_soc
        self.target_charge_soc = target_charge_soc
        self.traffic_seed = traffic_seed
        self._traffic_rng = random.Random(traffic_seed)

        # Initialize network & state
        self.network = self._initialize_network()
        self.channel = self._initialize_communication()

        # Load emergency manager
        self.scenario_manager = ScenarioLoader.load_scenario(scenario_config)
        self.vehicles: dict[str, Vehicle] = {}

        # Setup metrics
        ablation = {}
        if hasattr(router, "config") and hasattr(router.config, "e3_hybrid"):
            hyb_cfg = router.config.e3_hybrid
            ablation = {
                "share_aco_to_pso": getattr(hyb_cfg, "share_aco_to_pso", False),
                "share_gbest_to_pso": getattr(hyb_cfg, "share_gbest_to_pso", False),
                "share_gbest_to_bco": getattr(hyb_cfg, "share_gbest_to_bco", False),
                "share_bco_pso_to_aco": getattr(hyb_cfg, "share_bco_pso_to_aco", False),
            }

        self.metrics_collector = MetricsCollector(
            algorithm_name=router.__class__.__name__,
            scenario_name=scenario_config.name,
            seed=traffic_seed,
            config_details=scenario_config.model_dump(mode="json"),
            ablation_settings=ablation,
        )

        # Map vehicles -> Transceivers to manage range-based V2X
        self.vehicle_transceivers: dict[str, Transceiver] = {}
        self.original_destinations: dict[str, str] = {}

    def _initialize_network(self) -> Network:
        """Helper to create and populate the Network domain model."""
        net = Network()

        # Standalone scenario loading usually requires a network file.
        # Since we want to be decoupled, we check if the network_file_path is loaded.
        # For mock/unit-test purposes, we allow injecting or creating a dummy if it fails.
        import json
        import os

        net_path = self.config.simulation.network_file_path
        if os.path.exists(net_path):
            with open(net_path, encoding="utf-8") as f:
                data = json.load(f)
            net = Network.load_from_dict(data)
        else:
            # Fallback to empty network - callers should populate this in unit tests
            pass

        # Add Charging Stations from ScenarioConfig
        for cs_cfg in self.config.charging_stations:
            cs = ChargingStation(
                station_id=cs_cfg.id,
                node_id=cs_cfg.node_id,
                capacity=cs_cfg.capacity,
                power_kw=cs_cfg.power_kw,
                base_price_per_kwh=cs_cfg.base_price_per_kwh,
            )
            net.stations[cs.id] = cs

        return net

    def _initialize_communication(self) -> CommunicationChannel:
        """Helper to create and register V2I units on the channel."""
        channel = CommunicationChannel(
            self.config.communication, seed=self.traffic_seed
        )

        # Register Roadside Units (RSUs) on charging stations
        for cs in self.network.stations.values():
            node = self.network.nodes.get(cs.node_id)
            if node:

                def make_rsu_pos(n: Node) -> Callable[[], tuple[float, float]]:
                    return lambda: (n.x, n.y)

                rsu_transceiver = Transceiver(
                    transceiver_id=f"rsu_{cs.id}",
                    is_rsu=True,
                    v2v_range=self.config.communication.v2v_range_m,
                    v2i_range=self.config.communication.v2i_range_m,
                    position_provider=make_rsu_pos(node),
                )
                channel.register_transceiver(rsu_transceiver)

        return channel

    def generate_random_traffic(
        self, num_vehicles: int, soc_min: float = 0.5, soc_max: float = 0.95
    ) -> None:
        """Generates random EV vehicle trips in the network.

        Args:
            num_vehicles: Number of vehicles to generate.
            soc_min: Lower bound for initial SoC.
            soc_max: Upper bound for initial SoC.
        """
        nodes = list(self.network.nodes.keys())
        if len(nodes) < 2:
            return

        battery_model = BatteryModel(self.config.battery)

        for i in range(num_vehicles):
            veh_id = f"v_{i}"
            origin = self._traffic_rng.choice(nodes)
            dest = origin
            while dest == origin:
                dest = self._traffic_rng.choice(nodes)

            soc = self._traffic_rng.uniform(soc_min, soc_max)
            vehicle = Vehicle(veh_id, origin, dest, soc, battery_model)
            self.add_vehicle(vehicle)

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Adds a vehicle to the execution run and configures V2X communication.

        Args:
            vehicle: Vehicle instance.
        """
        self.vehicles[vehicle.id] = vehicle

        # Configure Transceiver callback for vehicle's dynamic coordinates
        def make_veh_pos(v: Vehicle) -> Callable[[], tuple[float, float]]:
            return lambda: v.get_position(self.network)

        trans = Transceiver(
            transceiver_id=f"obu_{vehicle.id}",
            is_rsu=False,
            v2v_range=self.config.communication.v2v_range_m,
            v2i_range=self.config.communication.v2i_range_m,
            position_provider=make_veh_pos(vehicle),
        )
        self.vehicle_transceivers[vehicle.id] = trans
        self.channel.register_transceiver(trans)

    def execute(self) -> MetricsCollector:
        """Runs the entire step-by-step simulation loop.

        Returns:
            MetricsCollector: Fully populated metrics collector.
        """
        dt = self.config.simulation.dt
        max_steps = self.config.simulation.max_steps
        current_time = 0.0

        # Initial Routing for all vehicles
        routing_ctx = RoutingContext(network=self.network, current_time=current_time)
        for vehicle in self.vehicles.values():
            self.metrics_collector.record_vehicle_spawn(vehicle.id, current_time)
            try:
                start_t = time.perf_counter()
                res = self.router.find_route(
                    vehicle.origin_node_id, vehicle.destination_node_id, routing_ctx
                )
                end_t = time.perf_counter()

                # Fetch statistics from swarm routers if available
                conv_iter = None
                exploration = None
                if hasattr(self.router, "get_statistics"):
                    stats = self.router.get_statistics()
                    conv_iter = stats.get("convergence_iteration")
                    exploration = stats.get("exploration_ratio")

                self.metrics_collector.record_router_invocation(
                    end_t - start_t, conv_iter, exploration
                )
                vehicle.assign_route(res.path_edges)
            except Exception:
                self.metrics_collector.record_stranded_vehicle()
                vehicle.state = VehicleState.STRANDED

        # Main Loop
        for step in range(max_steps):
            current_time = step * dt

            # 1. Update emergencies, closures, and ambulance dispatches
            # Temporarily register ambulances into vehicle set so scenario manager can see them
            manager_vehs = {**self.vehicles}

            # Step the emergency scenario manager
            self.scenario_manager.step(
                dt=dt,
                current_time=current_time,
                network=self.network,
                channel=self.channel,
                charging_stations=self.network.stations,
                vehicles=manager_vehs,
            )

            # Synchronize any ambulances spawned by manager into our OBU transceivers
            for amb_id, ambulance in self.scenario_manager.ambulances.items():
                if amb_id not in self.vehicles:
                    self.vehicles[amb_id] = ambulance
                    self.metrics_collector.record_ambulance_dispatch(
                        amb_id, current_time
                    )

                    def make_amb_pos(a: Vehicle) -> Callable[[], tuple[float, float]]:
                        return lambda: a.get_position(self.network)

                    trans = Transceiver(
                        transceiver_id=f"obu_{amb_id}",
                        is_rsu=False,
                        v2v_range=self.config.communication.v2v_range_m,
                        v2i_range=self.config.communication.v2i_range_m,
                        position_provider=make_amb_pos(ambulance),
                    )
                    self.vehicle_transceivers[amb_id] = trans
                    self.channel.register_transceiver(trans)

            # 2. V2X Broadcast generation for incidents & closures
            self._generate_v2x_broadcasts(current_time)

            # 3. Step the communication channel to deliver pending packets
            self.channel.step(current_time)

            # 4. Handle routing and movement updates
            step_arrivals = 0
            yielding_vehicles = set()

            routing_ctx = RoutingContext(
                network=self.network, current_time=current_time
            )

            # Read E3-Hybrid specific contribution logs if active
            if hasattr(self.router, "get_statistics"):
                s_stats = self.router.get_statistics()
                if "aco_contribution" in s_stats:
                    self.metrics_collector.record_subsystem_contribution(
                        s_stats.get("aco_contribution", 0.0),
                        s_stats.get("bco_contribution", 0.0),
                        s_stats.get("pso_contribution", 0.0),
                    )
                if "route_stability" in s_stats:
                    self.metrics_collector.record_route_stability(
                        s_stats["route_stability"]
                    )
                if "adaptation_time" in s_stats:
                    self.metrics_collector.record_adaptation_time(
                        s_stats["adaptation_time"]
                    )

            for veh_id, vehicle in list(self.vehicles.items()):
                # Ambulance movement is driven by scenario_manager, but check arrival here
                is_ambulance = veh_id in self.scenario_manager.ambulances
                if is_ambulance:
                    if vehicle.state == VehicleState.ARRIVED:
                        amb_disp = (
                            self.metrics_collector._temp_ambulance_dispatch_times.get(
                                veh_id, 0.0
                            )
                        )
                        self.metrics_collector.record_ambulance_arrival(
                            veh_id,
                            travel_time=vehicle.accumulated_travel_time,
                            response_time=current_time - amb_disp,
                        )
                        # Deregister ambulance to free space
                        self.vehicles.pop(veh_id, None)
                        self.channel.deregister_transceiver(f"obu_{veh_id}")
                    continue

                if vehicle.is_yielding:
                    yielding_vehicles.add(veh_id)

                if vehicle.state == VehicleState.EN_ROUTE:
                    # Check V2X updates to detect blocked/closed roads in current path
                    transceiver = self.vehicle_transceivers.get(veh_id)
                    needs_reroute = False

                    if transceiver:
                        # Scan incoming packets for road blocks or delays
                        for packet in list(transceiver.received_packets):
                            self.metrics_collector.record_packet_deliver(
                                current_time - packet.timestamp
                            )

                            # Parse payload details
                            if (
                                packet.packet_type == PacketType.TRAFFIC_UPDATE
                                and isinstance(packet.payload, TrafficUpdatePayload)
                            ):
                                if packet.payload.is_closed and (
                                    packet.payload.edge_id
                                    in vehicle.current_route[vehicle.current_edge_idx :]
                                ):
                                    needs_reroute = True
                            elif (
                                packet.packet_type == PacketType.EMERGENCY
                                and isinstance(packet.payload, EmergencyPayload)
                            ):
                                closed_edges = set(packet.payload.affected_edges)
                                remaining_route = set(
                                    vehicle.current_route[vehicle.current_edge_idx :]
                                )
                                if closed_edges.intersection(remaining_route):
                                    needs_reroute = True
                        transceiver.clear_inbox()

                    # Fallback check: if next edge is physically closed in the network
                    if not needs_reroute and vehicle.current_route:
                        next_edge_id = vehicle.current_route[vehicle.current_edge_idx]
                        next_edge = self.network.edges.get(next_edge_id)
                        if next_edge and next_edge.is_closed:
                            needs_reroute = True

                    # Run route recalculation
                    if needs_reroute or not vehicle.current_route:
                        vehicle.recalculation_count += 1
                        self.metrics_collector.record_reroute(veh_id)

                        # Find current node
                        current_node = vehicle.origin_node_id
                        if vehicle.current_route and vehicle.current_edge_idx < len(
                            vehicle.current_route
                        ):
                            curr_edge = self.network.edges[
                                vehicle.current_route[vehicle.current_edge_idx]
                            ]
                            current_node = curr_edge.from_node

                        try:
                            start_t = time.perf_counter()
                            res = self.router.find_route(
                                current_node, vehicle.destination_node_id, routing_ctx
                            )
                            end_t = time.perf_counter()
                            self.metrics_collector.record_router_invocation(
                                end_t - start_t
                            )
                            vehicle.assign_route(res.path_edges)
                        except Exception:
                            self.metrics_collector.record_stranded_vehicle()
                            vehicle.state = VehicleState.STRANDED
                            continue

                    # Move vehicle
                    edge_id = vehicle.current_route[vehicle.current_edge_idx]
                    edge = self.network.edges[edge_id]
                    speed = edge.speed_limit * edge.speed_reduction_factor
                    if vehicle.is_yielding and vehicle.yield_speed_limit is not None:
                        speed = min(speed, vehicle.yield_speed_limit)

                    vehicle.step_movement(dt, speed, 0.0, self.network)

                    # Check SoC for Low Battery Rerouting
                    is_heading_to_cs = any(
                        cs.node_id == vehicle.destination_node_id
                        for cs in self.network.stations.values()
                    )
                    if (
                        vehicle.soc < self.reroute_threshold_soc
                        and vehicle.state == VehicleState.EN_ROUTE
                        and not is_heading_to_cs
                    ):
                        nearest_station = self._find_nearest_station(vehicle)
                        if nearest_station:
                            # Replan path to Charging Node
                            current_node = edge.from_node
                            try:
                                start_t = time.perf_counter()
                                res_cs = self.router.find_route(
                                    current_node, nearest_station.node_id, routing_ctx
                                )
                                end_t = time.perf_counter()
                                self.metrics_collector.record_router_invocation(
                                    end_t - start_t
                                )

                                vehicle.assign_route(res_cs.path_edges)
                                if veh_id not in self.original_destinations:
                                    self.original_destinations[veh_id] = (
                                        vehicle.destination_node_id
                                    )
                                vehicle.destination_node_id = nearest_station.node_id
                                self.metrics_collector.record_charging_event(veh_id)
                            except Exception:
                                pass  # keep going if routing fails

                    # Check Arrival
                    if vehicle.state == VehicleState.ARRIVED:
                        is_at_station = any(
                            cs.node_id == vehicle.destination_node_id
                            for cs in self.network.stations.values()
                        )
                        if is_at_station:
                            vehicle.state = VehicleState.WAITING_IN_QUEUE
                        else:
                            step_arrivals += 1
                            free_flow = self._calculate_free_flow_time(
                                vehicle.current_route
                            )
                            self.metrics_collector.record_vehicle_arrival(
                                vehicle_id=veh_id,
                                travel_time=vehicle.accumulated_travel_time,
                                energy_consumed=vehicle.accumulated_energy_consumed,
                                distance_m=sum(
                                    self.network.edges[eid].length
                                    for eid in vehicle.current_route
                                ),
                                free_flow_time=free_flow,
                            )
                            # Clean up transceiver
                            self.channel.deregister_transceiver(f"obu_{veh_id}")

                elif vehicle.state == VehicleState.WAITING_IN_QUEUE:
                    # Find nearest station
                    station = self.network.stations.get(
                        self._find_nearest_station_id(vehicle.origin_node_id)
                    )
                    if station:
                        station.add_to_queue(veh_id)
                        vehicle.step_waiting(dt)

                elif vehicle.state == VehicleState.CHARGING:
                    # Charging is handled in global station step below
                    pass

            # 5. Charging Station bay management
            self._step_charging_stations(dt, routing_ctx)

            # 6. Global Step Metrics
            avg_queue_len = 0.0
            if self.network.stations:
                avg_queue_len = sum(
                    len(cs.queue) for cs in self.network.stations.values()
                ) / len(self.network.stations)

            total_edges = len(self.network.edges)
            avg_speed_ratio = 1.0
            if total_edges > 0:
                avg_speed_ratio = (
                    sum(e.speed_reduction_factor for e in self.network.edges.values())
                    / total_edges
                )

            self.metrics_collector.update_step_metrics(
                active_yielding_vehicles=yielding_vehicles,
                dt=dt,
                average_queue_len=avg_queue_len,
                throughput=step_arrivals,
                average_speed_ratio=avg_speed_ratio,
            )

        # Finalize runs
        total_amb = len(self.scenario_manager.ambulances) + len(
            self.metrics_collector._temp_ambulance_dispatch_times
        )
        self.metrics_collector.finalize(total_ambulances=total_amb)
        return self.metrics_collector

    def _generate_v2x_broadcasts(self, current_time: float) -> None:
        """Helper to scan active incidents/failures and broadcast V2X warnings."""
        for edge_id, edge in self.network.edges.items():
            if edge.is_closed:
                # Close alert
                payload = TrafficUpdatePayload(
                    edge_id=edge_id, speed_reduction_factor=0.0, is_closed=True
                )
                packet = Packet(
                    packet_id=f"pkt_close_{edge_id}_{current_time}",
                    sender_id="rsu_cs_dummy",  # System fallback
                    packet_type=PacketType.TRAFFIC_UPDATE,
                    priority=PacketPriority.MEDIUM,
                    timestamp=current_time,
                    ttl=2,
                    payload=payload,
                )
                self.metrics_collector.record_packet_transmit("system")

                # Deliver to transceivers in range by triggering broadcast on any registered RSU
                rsus = [r for r in self.channel.transceivers.values() if r.is_rsu]
                if rsus:
                    rsus[0].broadcast(packet, self.channel, current_time)
                else:
                    self.metrics_collector.record_packet_loss()

    def _step_charging_stations(self, dt: float, routing_ctx: RoutingContext) -> None:
        """Advances charging queue timers and transitions vehicles."""
        for cs in self.network.stations.values():
            if not cs.is_operational:
                continue

            # Process vehicles in queue
            for veh_id in list(cs.queue):
                if len(cs.charging_vehicles) < cs.capacity:
                    if cs.start_charging(veh_id):
                        veh = self.vehicles.get(veh_id)
                        if veh:
                            veh.state = VehicleState.CHARGING

            # Step charging vehicles
            for veh_id in list(cs.charging_vehicles):
                veh = self.vehicles.get(veh_id)
                if veh:
                    veh.step_charging(dt, cs.power_kw)
                    if veh.soc >= self.target_charge_soc:
                        cs.stop_charging(veh_id)
                        veh.state = VehicleState.EN_ROUTE

                        # Restore original destination node ID
                        original_dest = self.original_destinations.pop(
                            veh_id, veh.destination_node_id
                        )
                        veh.destination_node_id = original_dest

                        # Find destination path
                        try:
                            start_t = time.perf_counter()
                            res = self.router.find_route(
                                cs.node_id, veh.destination_node_id, routing_ctx
                            )
                            end_t = time.perf_counter()
                            self.metrics_collector.record_router_invocation(
                                end_t - start_t
                            )
                            veh.assign_route(res.path_edges)
                        except Exception:
                            veh.state = VehicleState.STRANDED
                            self.metrics_collector.record_stranded_vehicle()

    def _find_nearest_station(self, vehicle: Vehicle) -> ChargingStation | None:
        """Finds the spatial closest Charging Station based on Cartesian distance."""
        current_pos = vehicle.get_position(self.network)
        best_cs = None
        min_dist = float("inf")

        for cs in self.network.stations.values():
            node = self.network.nodes.get(cs.node_id)
            if node:
                dx = node.x - current_pos[0]
                dy = node.y - current_pos[1]
                dist = dx * dx + dy * dy
                if dist < min_dist:
                    min_dist = dist
                    best_cs = cs
        return best_cs

    def _find_nearest_station_id(self, node_id: str) -> str:
        """Returns station ID at or nearest to the node."""
        for cs in self.network.stations.values():
            if cs.node_id == node_id:
                return cs.id
        return list(self.network.stations.keys())[0] if self.network.stations else ""

    def _calculate_free_flow_time(self, route_edges: list[str]) -> float:
        """Calculates expected traversal duration at speed limits."""
        total_time = 0.0
        for edge_id in route_edges:
            edge = self.network.edges.get(edge_id)
            if edge:
                total_time += edge.length / edge.speed_limit
        return total_time
