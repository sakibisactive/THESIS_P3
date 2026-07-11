#!/usr/bin/env python3
"""Smoke test script for verifying Manhattan network compilation and TraCI sync."""

import os
import pathlib
import random
import sys

# Add project root to path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import traci  # type: ignore[import-untyped]

from src.core.battery import BatteryModel
from src.core.network import Network
from src.core.vehicle import Vehicle, VehicleState
from src.routing.dijkstra import DijkstraRouter
from src.routing.routing_context import RoutingContext
from src.sumo_adapter.adapter import SumoAdapter
from src.sumo_adapter.client import SumoClient
from src.sumo_adapter.osm_pipeline import OSMPipeline
from src.sumo_adapter.synchronizer import SumoSynchronizer
from src.utils.config import load_scenario_config

MIN_PATH_EDGES = 2
INITIAL_VEHICLE_SOC = 0.9
NUM_TICK_STEPS = 5
MAX_ROUTE_ATTEMPTS = 200


def resolve_network_file(config_path: str) -> str:
    """Resolves or compiles the network file according to config and file presence.

    Args:
        config_path: Scenario configuration path.

    Returns:
        str: Resolved net.xml file path.
    """
    scenario_cfg = load_scenario_config(config_path)
    sim_cfg = scenario_cfg.simulation
    net_file = sim_cfg.network_file_path or sim_cfg.network_file
    osm_file = sim_cfg.osm_file

    if net_file and os.path.exists(net_file):
        print(f"-> Found existing compiled network: '{net_file}'. Skipping.")
        return net_file

    if osm_file and os.path.exists(osm_file):
        if not net_file:
            net_file = "data/networks/manhattan.net.xml"
        print(f"-> Compiling raw OSM map from '{osm_file}' to '{net_file}'...")
        os.makedirs(os.path.dirname(net_file), exist_ok=True)
        OSMPipeline.compile_osm(
            osm_path=osm_file,
            output_net_path=net_file,
            remove_geometry=True,
            join_junctions=True,
        )
        print("-> OSM map compiled successfully.")
        return net_file

    raise FileNotFoundError(
        f"Could not load network. Neither network_file ('{net_file}') "
        f"nor osm_file ('{osm_file}') exists."
    )


def find_connected_route(
    network: Network, seed: int
) -> tuple[str, str, list[str]]:
    """Finds a valid origin-destination node pair and route using DijkstraRouter.

    Args:
        network: Python Network representation.
        seed: Random seed for node selection.

    Returns:
        tuple[str, str, list[str]]: Origin node, destination node, and route edges.
    """
    router = DijkstraRouter()
    ctx = RoutingContext(network=network)
    nodes_list = list(network.nodes.keys())

    random.seed(seed)

    for attempt in range(1, MAX_ROUTE_ATTEMPTS + 1):
        start = random.choice(nodes_list)
        end = random.choice(nodes_list)
        if start == end:
            continue
        try:
            res = router.find_route(start, end, ctx)
            if len(res.path_edges) >= MIN_PATH_EDGES:
                print(
                    f"   [Attempt {attempt}] Found route from '{start}' to "
                    f"'{end}' ({len(res.path_edges)} edges)."
                )
                return start, end, res.path_edges
        except Exception:
            continue

    raise RuntimeError(
        f"Failed to find any connected OD pairs after {MAX_ROUTE_ATTEMPTS} attempts."
    )


def run_smoke_test(config_path: str) -> None:
    """Executes the Manhattan map loading and TraCI synchronization smoke test.

    Args:
        config_path: Path to the YAML scenario configuration file.
    """
    print(f"[{config_path}] Loading scenario configuration...")
    net_file = resolve_network_file(config_path)

    # Load scenario configuration
    scenario_cfg = load_scenario_config(config_path)
    sim_cfg = scenario_cfg.simulation
    bat_cfg = scenario_cfg.battery

    print(f"-> Loading network '{net_file}' into Python Network model...")
    network = SumoAdapter.parse_network(net_file)
    print(
        f"-> Network loaded: {len(network.nodes)} nodes, "
        f"{len(network.edges)} edges."
    )

    if not network.nodes or not network.edges:
        raise ValueError("Loaded network is empty. Cannot run routing tests.")

    # Find valid connected route
    origin, dest, path_edges = find_connected_route(network, sim_cfg.seed)

    # Initialize Vehicle Registry and SUMO Client
    veh_id = "veh_smoke_0"
    battery = BatteryModel(bat_cfg)
    vehicle = Vehicle(
        vehicle_id=veh_id,
        origin_node_id=origin,
        destination_node_id=dest,
        initial_soc=INITIAL_VEHICLE_SOC,
        battery=battery,
    )
    vehicle.assign_route(path_edges)

    registry: dict[str, Vehicle] = {veh_id: vehicle}

    client = SumoClient(sim_cfg)
    synchronizer = SumoSynchronizer(sim_cfg, network, registry)

    print("-> Launching SUMO simulator...")
    try:
        client.start(net_file)
        print("-> SUMO server started and TraCI connection established.")

        # Define route and vehicle in SUMO
        traci.route.add("smoke_route", path_edges)
        traci.vehicle.add(veh_id, "smoke_route")
        print(f"-> Spawned vehicle '{veh_id}'")

        # Step the simulation a few times to verify synchronization
        print("-> Running step synchronization...")
        for tick in range(1, NUM_TICK_STEPS + 1):
            client.step()
            arrived = synchronizer.sync_from_sumo(dt=sim_cfg.dt)

            print(
                f"   [Step {tick}] Speed: {vehicle.speed:.2f} m/s | "
                f"SoC: {vehicle.soc * 100:.2f}% | "
                f"Edge: {vehicle.current_edge_idx}/{len(vehicle.current_route)}"
            )

            if veh_id in arrived:
                print(f"   [Step {tick}] Vehicle arrived early.")
                break

            # Verify telemetry updates
            assert vehicle.state == VehicleState.EN_ROUTE
            assert vehicle.soc <= INITIAL_VEHICLE_SOC

        print("-> Dynamic route update (Python -> SUMO) test...")
        synchronizer.sync_to_sumo()
        print("-> Route synchronization successful.")

    finally:
        print("-> Stopping SUMO simulator...")
        client.stop()
        print("-> SUMO server stopped successfully.")

    print("\n=======================================================")
    print("MANHATTAN SMOKE TEST PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    default_config = "configs/manhattan_sample.yaml"
    if len(sys.argv) > 1:
        default_config = sys.argv[1]

    try:
        run_smoke_test(default_config)
    except Exception as exc:
        print(f"\n[ERROR] Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)
