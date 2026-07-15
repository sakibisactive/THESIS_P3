import pytest
from src.evaluation.analysis import (
    perform_pareto_dominance,
    calculate_hypervolume,
    calculate_weighted_utility,
    calculate_robustness,
    calculate_emergency_metrics,
    calculate_resilience_metrics
)

@pytest.fixture
def mock_results():
    return [
        {
            "scenario_name": "Emergency Incident Scenario",
            "vehicles": 50,
            "seed": 1,
            "algorithm_name": "E3HybridRouter",
            "vehicle_travel_times": {"v0": 100.0, "v1": 150.0},
            "vehicle_energy_consumed": {"v0": 10.0, "v1": 15.0},
            "stranded_vehicle_count": 0,
            "ambulance_response_times": {"a0": 80.0},
            "ambulance_success_rate": 1.0,
            "emergency_corridor_activation_time": 20.0,
            "emergency_corridor_activation_count": 2,
            "congestion_levels_over_time": [1.0, 0.8, 0.85, 0.96, 0.98]
        },
        {
            "scenario_name": "Emergency Incident Scenario",
            "vehicles": 50,
            "seed": 1,
            "algorithm_name": "DijkstraRouter",
            "vehicle_travel_times": {"v0": 120.0, "v1": 180.0},
            "vehicle_energy_consumed": {"v0": 12.0, "v1": 18.0},
            "stranded_vehicle_count": 1,
            "ambulance_response_times": {"a0": 110.0},
            "ambulance_success_rate": 1.0,
            "emergency_corridor_activation_time": 5.0,
            "emergency_corridor_activation_count": 1,
            "congestion_levels_over_time": [1.0, 0.7, 0.75, 0.80, 0.82]
        }
    ]

def test_pareto_dominance(mock_results):
    res = perform_pareto_dominance(mock_results)
    assert res["total_runs"] == 1
    # E3-Hybrid is strictly better in all dimensions than Dijkstra in the mock data, so E3-Hybrid dominates Dijkstra
    assert res["dominance_ratio"]["E3-Hybrid"]["Dijkstra"] == 1.0
    assert res["dominance_ratio"]["Dijkstra"]["E3-Hybrid"] == 0.0
    assert res["non_dominated_percentage"]["E3-Hybrid"] == 1.0
    assert res["non_dominated_percentage"]["Dijkstra"] == 0.0

def test_hypervolume(mock_results):
    res = calculate_hypervolume(mock_results)
    assert res["E3-Hybrid"] > res["Dijkstra"]

def test_weighted_utility(mock_results):
    res = calculate_weighted_utility(mock_results)
    assert res["mean_utility"]["E3-Hybrid"] == pytest.approx(1.0)
    assert res["mean_utility"]["Dijkstra"] == pytest.approx(0.0)
    assert res["win_counts"]["E3-Hybrid"] == 1

def test_robustness(mock_results):
    res = calculate_robustness(mock_results)
    assert "Emergency Incident Scenario" in res
    assert "E3-Hybrid" in res["Emergency Incident Scenario"]
    assert res["Emergency Incident Scenario"]["E3-Hybrid"]["time_mean"] == 125.0

def test_emergency_metrics(mock_results):
    res = calculate_emergency_metrics(mock_results)
    assert "Emergency Incident Scenario" in res
    assert res["Emergency Incident Scenario"]["E3-Hybrid"]["avg_response_time"] == 80.0
    assert res["Emergency Incident Scenario"]["E3-Hybrid"]["avg_corridor_time"] == 20.0

def test_resilience_metrics(mock_results):
    # The mock results have "Emergency Incident Scenario" but the function filters scenarios with:
    # "closure", "failure", "blackout" in name. Let's modify scenario name to match.
    for r in mock_results:
        r["scenario_name"] = "road_closure_scenario"
    res = calculate_resilience_metrics(mock_results)
    assert "road_closure_scenario" in res
    assert "E3-Hybrid" in res["road_closure_scenario"]
