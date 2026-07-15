"""Unit tests for exporter, plotting, runner, and benchmark suite modules."""

import os
import pytest
from src.routing.dijkstra import DijkstraRouter
from src.utils.config import ScenarioConfig, SimulationConfig, BatteryConfig, CommunicationConfig
from src.evaluation.metrics_collector import SimulationRunMetrics
from src.evaluation.result_exporter import ResultExporter
from src.evaluation.plot_generator import PlotGenerator
from src.evaluation.experiment_runner import ExperimentRunner
from src.evaluation.benchmark_suite import BenchmarkSuite


@pytest.fixture
def mock_run_metrics() -> SimulationRunMetrics:
    return SimulationRunMetrics(
        algorithm_name="Dijkstra",
        scenario_name="test_grid",
        seed=42,
        config_details={"test": True},
        timestamp="2026-07-11T22:00:00",
        ablation_settings={},
        vehicle_travel_times={"v0": 50.0, "v1": 60.0},
        vehicle_free_flow_times={"v0": 45.0, "v1": 45.0},
        vehicle_delays={"v0": 5.0, "v1": 15.0},
        total_rerouting_events=1,
        vehicle_reroutes={"v0": 1},
        congestion_levels_over_time=[0.9, 0.85],
        throughput_over_time=[0, 2],
        ambulance_travel_times={"amb0": 30.0},
        ambulance_response_times={"amb0": 35.0},
        ambulance_success_rate=1.0,
        emergency_corridor_activation_time=10.0,
        emergency_corridor_activation_count=1,
        packets_sent=5,
        packets_delivered=4,
        packet_delivery_ratio=0.8,
        message_latencies=[0.003, 0.004, 0.002, 0.005],
        packet_loss_count=1,
        communication_overhead_per_vehicle={"v0": 5},
        vehicle_energy_consumed={"v0": 1.2, "v1": 1.4},
        vehicle_travelled_distance={"v0": 1000.0, "v1": 1200.0},
        charging_queue_lengths_over_time=[0.0, 0.0],
        stranded_vehicle_count=0,
        total_charging_events=0,
        vehicle_charging_events={},
        router_execution_times=[0.01, 0.015],
        router_convergence_speeds=[],
        adaptation_times_after_disruptions=[],
        route_stability_metrics=[],
        subsystem_contributions=[],
        exploration_ratios=[]
    )


def test_result_exporter(tmp_path, mock_run_metrics) -> None:
    """Verifies that CSV and JSON metric exports are written successfully."""
    exporter = ResultExporter(str(tmp_path))
    
    csv_file = exporter.export_to_csv([mock_run_metrics], "test_summary.csv")
    assert os.path.exists(csv_file)
    assert os.path.getsize(csv_file) > 0
    
    json_file = exporter.export_to_json(mock_run_metrics, "test_detail.json")
    assert os.path.exists(json_file)
    assert os.path.getsize(json_file) > 0


def test_plot_generator(tmp_path) -> None:
    """Verifies that Agg matplotlib generates and saves all required charts."""
    plotter = PlotGenerator(str(tmp_path))
    
    # 1. Convergence
    paths = plotter.generate_convergence_plot([100.0, 80.0, 75.0, 75.0], formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])
    
    # 2. Travel Time Comparison
    alg_data = {"Dijkstra": [50.0, 60.0], "E3-Hybrid": [45.0, 48.0]}
    paths = plotter.generate_travel_time_comparison(alg_data, formats=["png", "pdf"])
    assert len(paths) == 2
    assert all(os.path.exists(p) for p in paths)
    
    # 3. CDF
    paths = plotter.generate_travel_time_cdf(alg_data, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])
    
    # 4. Emergency Response
    amb_data = {"Dijkstra": [35.0], "E3-Hybrid": [28.0]}
    paths = plotter.generate_emergency_response_plot(amb_data, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])
    
    # 5. Congestion level
    paths = plotter.generate_congestion_level_plot([0.0, 1.0, 2.0], [1.0, 0.9, 0.85], formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 6. Pareto fronts
    pareto_data = {
        "Dijkstra": (120.0, 10.0, 15.0, 1.0),
        "E3-Hybrid": (100.0, 8.0, 12.0, 0.8)
    }
    paths = plotter.generate_pareto_fronts(pareto_data, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 7. Scalability curves
    scalability_data = {
        "Dijkstra": {25: 100.0, 50: 120.0, 100: 160.0},
        "E3-Hybrid": {25: 90.0, 50: 105.0, 100: 130.0}
    }
    paths = plotter.generate_scalability_curves(scalability_data, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 8. Resilience profiles
    resilience_data = {
        "Dijkstra": [1.0, 0.8, 0.82, 0.85, 0.90],
        "E3-Hybrid": [1.0, 0.8, 0.88, 0.95, 0.98]
    }
    paths = plotter.generate_resilience_profiles([0.0, 100.0, 200.0, 300.0, 400.0], resilience_data, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 9. Rank heatmap
    import numpy as np
    heatmap_data = np.array([[1.0, 2.0], [2.0, 1.0]])
    paths = plotter.generate_rank_heatmap(heatmap_data, ["Scen1", "Scen2"], ["Dijkstra", "E3-Hybrid"], formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 10. Rank comparison
    ranks = {"Dijkstra": 2.5, "E3-Hybrid": 1.2}
    paths = plotter.generate_rank_comparison(ranks, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    # 11. Radar chart
    radar_metrics = {
        "Dijkstra": [0.5, 0.6, 0.8, 0.4, 0.7],
        "E3-Hybrid": [0.9, 0.8, 0.7, 0.9, 0.9]
    }
    paths = plotter.generate_radar_chart(["Time", "Energy", "Latency", "Resilience", "Robustness"], radar_metrics, formats=["png"])
    assert len(paths) == 1
    assert os.path.exists(paths[0])


def test_experiment_runner_and_benchmark(tmp_path) -> None:
    """Runs a complete test benchmark with ExperimentRunner and BenchmarkSuite."""
    # Write a dummy network file
    net_file = tmp_path / "dummy_net.json"
    net_file.write_text("""{
        "nodes": [
            {"id": "n1", "x": 0.0, "y": 0.0},
            {"id": "n2", "x": 100.0, "y": 0.0}
        ],
        "edges": [
            {"id": "e1", "from": "n1", "to": "n2", "length": 100.0, "speed_limit": 15.0, "gradient_rad": 0.0}
        ],
        "stations": []
    }""", encoding="utf-8")
    
    suite = BenchmarkSuite(str(tmp_path), seeds=[42])
    scenario = suite.create_default_benchmark_scenario(str(net_file))
    
    algorithms = [(DijkstraRouter, {})]
    
    results = suite.run_benchmark(algorithms, scenario)
    
    assert len(results) == 1
    assert results[0].algorithm_name == "DijkstraRouter"
    assert results[0].scenario_name == "default_benchmark"
    assert results[0].seed == 42
