"""Integration tests for SUMO TraCI client and state synchronizer."""

import subprocess
from pathlib import Path

import traci  # type: ignore[import-untyped]

from src.core.battery import BatteryModel
from src.core.vehicle import Vehicle, VehicleState
from src.evaluation.sumo_runner import SumoExperimentRunner
from src.routing.dijkstra import DijkstraRouter
from src.sumo_adapter.adapter import SumoAdapter
from src.sumo_adapter.client import SumoClient
from src.sumo_adapter.synchronizer import SumoSynchronizer
from src.utils.config import BatteryConfig, ScenarioConfig, SimulationConfig


def compile_test_network(tmp_path: Path) -> str:
    """Helper to compile a minimal 2-node, 1-edge network for SUMO testing."""
    nodes_file = tmp_path / "nodes.nod.xml"
    edges_file = tmp_path / "edges.edg.xml"
    net_file = tmp_path / "test.net.xml"

    nodes_file.write_text(
        """<nodes>
        <node id="n1" x="0.0" y="0.0"/>
        <node id="n2" x="100.0" y="0.0"/>
    </nodes>""",
        encoding="utf-8",
    )

    edges_file.write_text(
        """<edges>
        <edge id="e1" from="n1" to="n2" numLanes="1" speed="15.0" length="100.0"/>
    </edges>""",
        encoding="utf-8",
    )

    # Run netconvert
    subprocess.run(
        [
            "netconvert",
            "--node-files",
            str(nodes_file),
            "--edge-files",
            str(edges_file),
            "--output-file",
            str(net_file),
        ],
        check=True,
        capture_output=True,
    )

    return str(net_file)


def test_sumo_client_and_sync_lifecycle(tmp_path: Path) -> None:
    """End-to-end integration test verifying SUMO lifecycle and state
    synchronization.
    """
    # 1. Compile minimal network
    net_file = compile_test_network(tmp_path)

    # 2. Build configuration
    config = SimulationConfig(
        dt=1.0,
        max_steps=10,
        mode="sumo",
        network_file_path=net_file,
        sumo_binary="sumo",
        use_gui=False,
        step_length=1.0,
        seed=42,
        traci_port=9999,  # Use distinct port for test isolation
        enable_subscriptions=True,
    )

    bat_config = BatteryConfig(
        capacity_kwh=60.0,
        mass_kg=1500.0,
        efficiency=0.9,
        drag_coeff=0.3,
        frontal_area=2.2,
        rolling_res_coeff=0.01,
        regen_efficiency=0.7,
    )

    # 3. Create Python Network and Vehicle Registry
    # Parse network using adapter to ensure exact mapping
    network = SumoAdapter.parse_network(net_file)

    # Register one vehicle agent
    battery = BatteryModel(bat_config)
    vehicle = Vehicle(
        vehicle_id="veh0",
        origin_node_id="n1",
        destination_node_id="n2",
        initial_soc=0.8,
        battery=battery,
    )
    vehicle.assign_route(["e1"])

    registry: dict[str, Vehicle] = {"veh0": vehicle}

    # 4. Run Sumo Client
    client = SumoClient(config)
    synchronizer = SumoSynchronizer(config, network, registry)

    try:
        client.start(net_file)
        assert client.is_connected()

        # Add the route and vehicle to SUMO to simulate spawning
        traci.route.add("route1", ["e1"])
        traci.vehicle.add("veh0", "route1")

        # Step 1: Let the vehicle spawn
        client.step()

        # Synchronize states from SUMO to Python
        arrived = synchronizer.sync_from_sumo(dt=1.0)
        assert len(arrived) == 0

        # Assert vehicle kinematics synced
        assert vehicle.speed >= 0.0
        assert vehicle.current_edge_idx == 0
        assert vehicle.state == VehicleState.EN_ROUTE

        # Check battery model step is computed
        # Original SoC was 0.8. Due to motion, it should consume energy.
        # Wait, if speed > 0, SoC should decrease slightly.
        assert vehicle.soc <= 0.8

        # Test bidirectional synchronization: push route update
        # Update Python route
        vehicle.current_route = ["e1"]
        synchronizer.sync_to_sumo()

        # Run several steps until vehicle arrives
        steps = 0
        while steps < 15:
            client.step()
            arrived = synchronizer.sync_from_sumo(dt=1.0)
            if "veh0" in arrived:
                break
            steps += 1

        # Check arrival detection
        assert vehicle.state == VehicleState.ARRIVED

    finally:
        client.stop()
        assert not client.is_connected()


def test_sumo_sync_closures(tmp_path: Path) -> None:
    """Verifies that road closures in Python are correctly synchronized to SUMO."""
    net_file = compile_test_network(tmp_path)
    config = SimulationConfig(
        dt=1.0,
        max_steps=10,
        mode="sumo",
        network_file_path=net_file,
        sumo_binary="sumo",
        use_gui=False,
        step_length=1.0,
        seed=42,
        traci_port=9998,
        enable_subscriptions=True,
    )
    network = SumoAdapter.parse_network(net_file)
    registry: dict[str, Vehicle] = {}

    client = SumoClient(config)
    synchronizer = SumoSynchronizer(config, network, registry)

    try:
        client.start(net_file)
        assert client.is_connected()

        # Close edge e1 in Python
        network.edges["e1"].is_closed = True

        # Sync closures to SUMO
        synchronizer.sync_to_sumo()

        # Check in SUMO via TraCI (e1_0 is the first lane of edge e1)
        disallowed = traci.lane.getDisallowed("e1_0")
        assert "passenger" in disallowed

    finally:
        client.stop()


def test_sumo_experiment_runner(tmp_path: Path) -> None:
    """Verifies that SumoExperimentRunner runs batch experiments correctly."""
    net_file = compile_test_network(tmp_path)
    
    sim_cfg = SimulationConfig(
        dt=1.0,
        max_steps=5,
        mode="sumo",
        network_file_path=net_file,
        sumo_binary="sumo",
        use_gui=False,
        step_length=1.0,
        seed=42,
        traci_port=9997,
        enable_subscriptions=True,
    )

    bat_config = BatteryConfig(
        capacity_kwh=60.0,
        mass_kg=1500.0,
        efficiency=0.9,
        drag_coeff=0.3,
        frontal_area=2.2,
        rolling_res_coeff=0.01,
        regen_efficiency=0.7,
    )

    scenario_cfg = ScenarioConfig(
        name="test_scenario",
        simulation=sim_cfg,
        battery=bat_config,
    )

    runner = SumoExperimentRunner(
        algorithms=[(DijkstraRouter, {})],
        scenarios=[scenario_cfg],
        seeds=[42],
    )

    results = runner.run()
    assert len(results) == 1
    assert results[0].total_charging_events == 0

