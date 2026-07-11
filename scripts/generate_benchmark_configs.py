#!/usr/bin/env python3
"""Generates the benchmark scenario configuration files for Phase 4.3."""

import os
import yaml

CONFIG_DIR = "configs/benchmarks"

# Base configuration shared by all scenarios
base_config = {
    "simulation": {
        "mode": "sumo",
        "dt": 1.0,
        "max_steps": 1000,
        "osm_file": None,
        "network_file": "data/networks/midtown_manhattan.net.xml",
        "route_file": None,
        "scenario_file": "data/scenarios/manhattan.yaml",
        "output_dir": "outputs",
        "sumo_binary": "sumo",
        "use_gui": False,
        "step_length": 1.0,
        "seed": 42,
        "traci_port": 8813,
        "enable_subscriptions": True,
        "real_time_factor": -1.0,
    },
    "battery": {
        "capacity_kwh": 60.0,
        "mass_kg": 1500.0,
        "efficiency": 0.9,
        "drag_coeff": 0.25,
        "frontal_area": 2.2,
        "rolling_res_coeff": 0.01,
        "regen_efficiency": 0.7,
    },
    "charging_stations": [
        {
            "id": "station_west",
            "node_id": "42432825",
            "capacity": 4,
            "power_kw": 150.0,
            "base_price_per_kwh": 0.35,
        },
        {
            "id": "station_east",
            "node_id": "42437644",
            "capacity": 4,
            "power_kw": 150.0,
            "base_price_per_kwh": 0.35,
        }
    ],
    "communication": {
        "v2v_range_m": 150.0,
        "v2i_range_m": 300.0,
        "channel_bandwidth_mbps": 10.0,
        "packet_loss_rate": 0.02,
        "communication_delay_s": 0.05,
    },
    "algorithms": {
        "objectives": {
            "weight_travel_time": 0.7,
            "weight_energy_consumption": 0.2,
            "weight_safety": 0.1,
        },
        "aco": {
            "alpha": 1.0,
            "beta": 2.0,
            "evaporation_rate": 0.1,
            "pheromone_constant": 100.0,
            "num_ants": 10,
        },
        "bco": {
            "colony_size": 10,
            "max_scout_iterations": 5,
            "loyalty_threshold": 0.6,
        },
        "pso": {
            "swarm_size": 10,
            "w_inertia": 0.7,
            "c1_personal": 1.5,
            "c2_global": 1.5,
        },
        "e3_hybrid": {
            "max_iterations": 5,
        },
    },
    "emergencies": [],
    "infrastructure_failures": [],
    "ambulance_dispatches": [],
    "road_closures": [],
}


def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # 1. Normal Traffic
    normal_cfg = dict(base_config)
    normal_cfg["name"] = "Normal Traffic Scenario"
    with open(f"{CONFIG_DIR}/normal_traffic.yaml", "w") as f:
        yaml.safe_dump(normal_cfg, f, default_flow_style=False)

    # 2. Single Road Closure
    road_closure_cfg = dict(base_config)
    road_closure_cfg["name"] = "Single Road Closure Scenario"
    road_closure_cfg["road_closures"] = [
        {
            "id": "closure_broadway",
            "start_time": 100.0,
            "duration": 800.0,
            "edge_id": "-1088325196#1",
        }
    ]
    with open(f"{CONFIG_DIR}/road_closure.yaml", "w") as f:
        yaml.safe_dump(road_closure_cfg, f, default_flow_style=False)

    # 3. Progressive Closures
    progressive_cfg = dict(base_config)
    progressive_cfg["name"] = "Progressive Closures Scenario"
    progressive_cfg["road_closures"] = [
        {
            "id": "closure_1",
            "start_time": 50.0,
            "duration": 600.0,
            "edge_id": "-1088325196#1",
        },
        {
            "id": "closure_2",
            "start_time": 150.0,
            "duration": 600.0,
            "edge_id": "-1088325194",
        },
        {
            "id": "closure_3",
            "start_time": 250.0,
            "duration": 600.0,
            "edge_id": "-1088325197#1",
        }
    ]
    with open(f"{CONFIG_DIR}/progressive_closures.yaml", "w") as f:
        yaml.safe_dump(progressive_cfg, f, default_flow_style=False)

    # 4. Emergency Incident
    emergency_cfg = dict(base_config)
    emergency_cfg["name"] = "Emergency Incident Scenario"
    emergency_cfg["emergencies"] = [
        {
            "id": "incident_midtown",
            "epicenter_node_id": "42432818",
            "start_time": 80.0,
            "duration": 800.0,
            "initial_radius_m": 15.0,
            "propagation_rate": 1.5,
            "intensity": 0.8,
        }
    ]
    emergency_cfg["ambulance_dispatches"] = [
        {
            "id": "amb_0",
            "start_time": 100.0,
            "origin_node_id": "9971314382",
            "destination_node_id": "42445382",
            "battery_capacity_kwh": 80.0,
            "initial_soc": 0.95,
            "v2v_range_m": 200.0,
            "v2i_range_m": 400.0,
            "speed_m_s": 25.0,
            "route": ["-1088325196#1", "-1088325194"],
        }
    ]
    with open(f"{CONFIG_DIR}/emergency_incident.yaml", "w") as f:
        yaml.safe_dump(emergency_cfg, f, default_flow_style=False)

    # 5. Infrastructure Failure
    infra_cfg = dict(base_config)
    infra_cfg["name"] = "Infrastructure Failure Scenario"
    infra_cfg["infrastructure_failures"] = [
        {
            "id": "station_failure_west",
            "failure_type": "CHARGING_STATION",
            "start_time": 120.0,
            "duration": 600.0,
            "target_id": "station_west",
            "blackout_area": None,
        }
    ]
    with open(f"{CONFIG_DIR}/infrastructure_failure.yaml", "w") as f:
        yaml.safe_dump(infra_cfg, f, default_flow_style=False)

    # 6. Communication Blackout
    comm_cfg = dict(base_config)
    comm_cfg["name"] = "Communication Blackout Scenario"
    comm_cfg["infrastructure_failures"] = [
        {
            "id": "blackout_midtown",
            "failure_type": "COMMUNICATION",
            "start_time": 100.0,
            "duration": 800.0,
            "target_id": "comm_blackout",
            "blackout_area": {
                "min_x": 1000.0,
                "min_y": 500.0,
                "max_x": 3000.0,
                "max_y": 2000.0,
            },
        }
    ]
    with open(f"{CONFIG_DIR}/communication_blackout.yaml", "w") as f:
        yaml.safe_dump(comm_cfg, f, default_flow_style=False)

    print(f"Successfully generated 6 benchmark scenarios in: {CONFIG_DIR}")


if __name__ == "__main__":
    main()
