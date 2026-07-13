"""SUMO scenario execution engine driving simulator runs and data collection."""

import os
import random
import time
from collections.abc import Callable

import traci  # type: ignore[import-untyped]

from src.communication.channel import CommunicationChannel
from src.communication.transceiver import Transceiver
from src.core.battery import BatteryModel
from src.core.network import ChargingStation, Network, Node
from src.core.vehicle import Vehicle, VehicleState
from src.emergency.scenario_loader import ScenarioLoader
from src.evaluation.metrics_collector import MetricsCollector
from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.sumo_adapter.adapter import SumoAdapter
from src.sumo_adapter.client import SumoClient
from src.sumo_adapter.synchronizer import SumoSynchronizer
from src.utils.config import ScenarioConfig
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

MIN_NODES_FOR_ROUTING = 2
MIN_PATH_EDGES = 2


class SumoScenarioExecutor:
    """Orchestrates a SUMO-based simulation scenario execution run."""

    def __init__(
        self,
        scenario_config: ScenarioConfig,
        router: Router,
        reroute_threshold_soc: float = 0.20,
        target_charge_soc: float = 1.00,
        traffic_seed: int = 42,
    ) -> None:
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
        """Helper to parse SUMO .net.xml and add charging stations."""
        sim_cfg = self.config.simulation
        net_file = sim_cfg.network_file_path or sim_cfg.network_file
        if not net_file or not os.path.exists(net_file):
            raise FileNotFoundError(f"SUMO network file not found at: {net_file}")

        net = SumoAdapter.parse_network(net_file)

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

        # Register RSUs on charging stations
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

        Ensures path connectivity using the router.
        """
        nodes = list(self.network.nodes.keys())
        if len(nodes) < MIN_NODES_FOR_ROUTING:
            return

        battery_model = BatteryModel(self.config.battery)
        routing_ctx = RoutingContext(network=self.network, current_time=0.0)

        vehicles_created = 0
        attempts = 0
        max_attempts = num_vehicles * 10

        while vehicles_created < num_vehicles and attempts < max_attempts:
            attempts += 1
            veh_id = f"v_{vehicles_created}"
            origin = self._traffic_rng.choice(nodes)
            dest = origin
            while dest == origin:
                dest = self._traffic_rng.choice(nodes)

            # Pre-validate connectivity
            try:
                res = self.router.find_route(origin, dest, routing_ctx)
                if len(res.path_edges) < MIN_PATH_EDGES:
                    continue
            except Exception:
                continue

            soc = self._traffic_rng.uniform(soc_min, soc_max)
            vehicle = Vehicle(veh_id, origin, dest, soc, battery_model)
            vehicle.assign_route(res.path_edges)
            self.add_vehicle(vehicle)
            vehicles_created += 1

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Adds a vehicle to the execution run and configures V2X communication."""
        self.vehicles[vehicle.id] = vehicle

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

    def _spawn_initial_vehicles(self, routing_ctx: RoutingContext) -> None:
        """Helper to spawn all loaded vehicles in SUMO."""
        for veh_id, vehicle in self.vehicles.items():
            self.metrics_collector.record_vehicle_spawn(veh_id, 0.0)
            traci.route.add(f"route_{veh_id}", vehicle.current_route)
            traci.vehicle.add(veh_id, f"route_{veh_id}")

    def _handle_departed_and_arrivals(
        self, arrived: list[str]
    ) -> int:
        """Processes arrived vehicles and transitions them to queues/charge/done."""
        step_arrivals = 0
        for arr_id in arrived:
            veh = self.vehicles[arr_id]
            is_at_station = any(
                cs.node_id == veh.destination_node_id
                for cs in self.network.stations.values()
            )
            if is_at_station:
                st_id = self._find_nearest_station_id(veh.destination_node_id)
                cs = self.network.stations.get(st_id)
                if cs:
                    cs.queue.append(arr_id)
                    veh.state = VehicleState.WAITING_IN_QUEUE
                    logger.info(f"Vehicle '{arr_id}' queued at station '{st_id}'.")
            else:
                step_arrivals += 1
                free_flow = self._calculate_free_flow_time(veh.current_route)
                distance_m = sum(
                    self.network.edges[eid].length
                    for eid in veh.current_route
                    if eid in self.network.edges
                )
                self.metrics_collector.record_vehicle_arrival(
                    vehicle_id=arr_id,
                    travel_time=veh.accumulated_travel_time,
                    energy_consumed=veh.accumulated_energy_consumed,
                    distance_m=distance_m,
                    free_flow_time=free_flow,
                )
                # Clean up transceiver
                self.channel.deregister_transceiver(f"obu_{arr_id}")
        return step_arrivals

    def _handle_low_battery_rerouting(self, routing_ctx: RoutingContext) -> None:
        """Checks SoC of all active en-route vehicles and schedules charging
        diversion.
        """
        for veh_id, vehicle in self.vehicles.items():
            if vehicle.state != VehicleState.EN_ROUTE:
                continue

            # EV Rerouting check
            is_heading_to_cs = any(
                cs.node_id == vehicle.destination_node_id
                for cs in self.network.stations.values()
            )
            if vehicle.soc < self.reroute_threshold_soc and not is_heading_to_cs:
                nearest_station = self._find_nearest_station(vehicle)
                if nearest_station:
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
                    except Exception as e:
                        logger.warning(
                            f"Low battery reroute search failed for '{veh_id}': {e}"
                        )

    def execute(self) -> MetricsCollector:
        """Runs the SUMO TraCI simulation step loop and records metrics."""
        dt = self.config.simulation.dt
        max_steps = self.config.simulation.max_steps
        sim_cfg = self.config.simulation
        net_file = sim_cfg.network_file_path or sim_cfg.network_file

        if not net_file or not os.path.exists(net_file):
            raise FileNotFoundError(f"SUMO network file not found at: {net_file}")

        client = SumoClient(sim_cfg)
        synchronizer = SumoSynchronizer(sim_cfg, self.network, self.vehicles)

        logger.info("Starting SUMO TraCI execution client...")
        client.start(net_file)

        try:
            routing_ctx = RoutingContext(network=self.network, current_time=0.0)
            self._spawn_initial_vehicles(routing_ctx)

            for step in range(max_steps):
                current_time = step * dt

                # Check termination conditions
                active_evs = [
                    v for v in self.vehicles.values()
                    if v.state in (
                        VehicleState.EN_ROUTE,
                        VehicleState.WAITING_IN_QUEUE,
                        VehicleState.CHARGING,
                    )
                ]
                if not active_evs and step > 0:
                    logger.info("All vehicles finished trips. Terminating.")
                    break

                # Step emergency managers and channel
                manager_vehs = {**self.vehicles}
                self.scenario_manager.step(
                    dt=dt,
                    current_time=current_time,
                    network=self.network,
                    channel=self.channel,
                    charging_stations=self.network.stations,
                    vehicles=manager_vehs,
                )
                self.channel.step(current_time)

                # Step SUMO and synchronizers
                client.step()
                arrived = synchronizer.sync_from_sumo(dt=dt)

                # Process vehicles
                for v in active_evs:
                    if v.state == VehicleState.EN_ROUTE:
                        v.accumulated_travel_time += dt

                step_arrivals = self._handle_departed_and_arrivals(arrived)
                self._handle_low_battery_rerouting(routing_ctx)
                self._step_charging_stations(dt, routing_ctx)

                synchronizer.sync_to_sumo()

                # Step metrics
                avg_queue_len = 0.0
                if self.network.stations:
                    avg_queue_len = sum(
                        len(cs.queue) for cs in self.network.stations.values()
                    ) / len(self.network.stations)

                self.metrics_collector.update_step_metrics(
                    active_yielding_vehicles=set(),
                    dt=dt,
                    average_queue_len=avg_queue_len,
                    throughput=step_arrivals,
                    average_speed_ratio=1.0,
                )

        finally:
            logger.info("Stopping SUMO TraCI execution client...")
            client.stop()

        self.metrics_collector.finalize(total_ambulances=0)
        return self.metrics_collector

    def _step_charging_stations(self, dt: float, routing_ctx: RoutingContext) -> None:
        """Advances charging queue timers and respawns charged vehicles in SUMO."""
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

                        # Restore original destination
                        original_dest = self.original_destinations.pop(
                            veh_id, veh.destination_node_id
                        )
                        veh.destination_node_id = original_dest

                        if cs.node_id == original_dest:
                            # Already at destination! Mark as arrived.
                            veh.state = VehicleState.ARRIVED
                            logger.info(f"Vehicle '{veh_id}' finished charging and is already at destination node '{original_dest}'. Marking as ARRIVED.")
                            distance_m = sum(
                                self.network.edges[eid].length
                                for eid in veh.current_route
                                if eid in self.network.edges
                            )
                            free_flow = self._calculate_free_flow_time(veh.current_route)
                            self.metrics_collector.record_vehicle_arrival(
                                vehicle_id=veh_id,
                                travel_time=veh.accumulated_travel_time,
                                energy_consumed=veh.accumulated_energy_consumed,
                                distance_m=distance_m,
                                free_flow_time=free_flow,
                            )
                            self.channel.deregister_transceiver(f"obu_{veh_id}")
                            continue

                        # Reroute to destination from charging node
                        try:
                            start_t = time.perf_counter()
                            res = self.router.find_route(
                                cs.node_id, veh.destination_node_id, routing_ctx
                            )
                            end_t = time.perf_counter()
                            self.metrics_collector.record_router_invocation(
                                end_t - start_t
                            )
                            
                            if not res.path_edges:
                                raise ValueError("Router returned an empty route path (network disconnected or unreachable).")
                                
                            veh.assign_route(res.path_edges)

                            # Re-spawn in SUMO
                            route_name = f"route_{veh_id}_postcharge"
                            traci.route.add(route_name, res.path_edges)
                            traci.vehicle.add(veh_id, route_name)
                            logger.info(f"Re-spawned vehicle '{veh_id}' in SUMO.")
                        except Exception as e:
                            logger.error(
                                f"Failed to route post-charge vehicle '{veh_id}': {e}"
                            )
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
