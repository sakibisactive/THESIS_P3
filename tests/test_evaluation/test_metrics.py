"""Unit tests for the MetricsCollector evaluation module."""

import pytest
from src.evaluation.metrics_collector import MetricsCollector, SubsystemContribution


def test_metrics_collection_basic() -> None:
    """Verifies basic vehicular and routing metrics logging."""
    collector = MetricsCollector(
        algorithm_name="Dijkstra",
        scenario_name="test_grid",
        seed=123,
        config_details={"sim": "test"},
        ablation_settings={"test_ablation": True}
    )

    # Spawn and arrive
    collector.record_vehicle_spawn("v1", 0.0)
    collector.record_vehicle_arrival(
        vehicle_id="v1",
        travel_time=50.0,
        energy_consumed=1.5,
        distance_m=1000.0,
        free_flow_time=40.0
    )

    # Rerouting and stranded
    collector.record_reroute("v1")
    collector.record_reroute("v1")
    collector.record_stranded_vehicle()

    # Charging
    collector.record_charging_event("v1")

    # Finalize
    metrics = collector.finalize(total_ambulances=0)

    assert metrics.algorithm_name == "Dijkstra"
    assert metrics.scenario_name == "test_grid"
    assert metrics.seed == 123
    assert metrics.ablation_settings == {"test_ablation": True}
    
    assert metrics.vehicle_travel_times["v1"] == 50.0
    assert metrics.vehicle_delays["v1"] == 10.0
    assert metrics.total_rerouting_events == 2
    assert metrics.vehicle_reroutes["v1"] == 2
    assert metrics.stranded_vehicle_count == 1
    assert metrics.total_charging_events == 1
    assert metrics.vehicle_charging_events["v1"] == 1


def test_emergency_and_communication_metrics() -> None:
    """Verifies emergency yields and V2X telemetry metric logs."""
    collector = MetricsCollector(
        algorithm_name="E3HybridRouter",
        scenario_name="test_emergency",
        seed=42,
        config_details={}
    )

    # Communication
    collector.record_packet_transmit("v1")
    collector.record_packet_transmit("v1")
    collector.record_packet_deliver(0.005)
    collector.record_packet_loss()

    # Ambulance dispatch and arrival
    collector.record_ambulance_dispatch("amb1", 10.0)
    collector.record_ambulance_arrival("amb1", travel_time=30.0, response_time=40.0)

    # Step update yielding
    collector.update_step_metrics(
        active_yielding_vehicles={"v1", "v2"},
        dt=1.0,
        average_queue_len=0.5,
        throughput=1,
        average_speed_ratio=0.85
    )
    
    # Finalize
    metrics = collector.finalize(total_ambulances=1)

    assert metrics.packets_sent == 2
    assert metrics.packets_delivered == 1
    assert metrics.packet_loss_count == 1
    assert metrics.packet_delivery_ratio == 0.5
    assert metrics.message_latencies == [0.005]
    assert metrics.communication_overhead_per_vehicle["v1"] == 2

    assert metrics.ambulance_travel_times["amb1"] == 30.0
    assert metrics.ambulance_response_times["amb1"] == 40.0
    assert metrics.ambulance_success_rate == 1.0

    assert metrics.emergency_corridor_activation_time == 2.0  # 1.0 * 2 vehicles
    assert metrics.emergency_corridor_activation_count == 2
    assert metrics.charging_queue_lengths_over_time == [0.5]
    assert metrics.congestion_levels_over_time == [0.85]


def test_algorithm_subsystem_metrics() -> None:
    """Verifies execution time and subsystem contribution logging."""
    collector = MetricsCollector(
        algorithm_name="E3HybridRouter",
        scenario_name="test_hybrid",
        seed=99,
        config_details={}
    )

    collector.record_router_invocation(execution_time=0.15, convergence_iter=12, exploration_ratio=0.4)
    collector.record_subsystem_contribution(aco=0.4, bco=0.3, pso=0.3)
    collector.record_route_stability(0.95)
    collector.record_adaptation_time(5.0)

    metrics = collector.finalize(total_ambulances=0)

    assert metrics.router_execution_times == [0.15]
    assert metrics.router_convergence_speeds == [12]
    assert metrics.exploration_ratios == [0.4]
    assert metrics.subsystem_contributions[0].aco_contrib == 0.4
    assert metrics.route_stability_metrics == [0.95]
    assert metrics.adaptation_times_after_disruptions == [5.0]
