import os
import sys
import json
import pytest
import numpy as np

# Add repo root to path to import scripts.run_benchmarks
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import scripts.run_benchmarks as rb


@pytest.fixture
def patch_dirs(tmp_path):
    """Fixture to patch output and intermediate directories for safety during testing."""
    original_output_dir = rb.OUTPUT_DIR
    original_intermediate_dir = rb.INTERMEDIATE_DIR
    original_gen_stats_plots = rb.generate_statistics_and_plots
    original_write_reproducibility = rb.write_reproducibility_manifest

    rb.OUTPUT_DIR = str(tmp_path)
    rb.INTERMEDIATE_DIR = os.path.join(str(tmp_path), "intermediate")
    os.makedirs(rb.INTERMEDIATE_DIR, exist_ok=True)

    # Mock stats and reproducibility generators to prevent disk/file side effects
    rb.generate_statistics_and_plots = lambda *args, **kwargs: None
    rb.write_reproducibility_manifest = lambda *args, **kwargs: None

    yield tmp_path

    # Restore originals
    rb.OUTPUT_DIR = original_output_dir
    rb.INTERMEDIATE_DIR = original_intermediate_dir
    rb.generate_statistics_and_plots = original_gen_stats_plots
    rb.write_reproducibility_manifest = original_write_reproducibility


def test_generate_results_and_reports_with_list_router_times(patch_dirs) -> None:
    """Verifies results aggregation and reports generation when router_execution_times is a list."""
    scenarios = ["test_scen"]
    algorithms = ["test_alg"]
    vehicles = [50]
    seeds = [1]
    
    task_file = os.path.join(rb.INTERMEDIATE_DIR, "run_test_scen_test_alg_50_seed1.json")
    
    mock_run_data = {
        "algorithm_name": "test_alg",
        "scenario_name": "test_scen",
        "seed": 1,
        "vehicles": 50,
        "config_details": {
            "simulation": {
                "max_steps": 600
            }
        },
        "vehicle_travel_times": {
            "v0": 100.0,
            "v1": 150.0
        },
        "vehicle_energy_consumed": {
            "v0": 10.0,
            "v1": 12.0
        },
        "stranded_vehicles": 0,
        "total_rerouting_events": 2,
        "router_execution_times": [0.012, 0.015, 0.010]
    }
    
    with open(task_file, "w") as f:
        json.dump(mock_run_data, f)
        
    results = rb.generate_results_and_reports(scenarios, algorithms, vehicles, seeds)
    
    assert len(results) == 1
    assert results[0]["algorithm_name"] == "test_alg"
    
    csv_path = os.path.join(rb.OUTPUT_DIR, "benchmark_results.csv")
    assert os.path.exists(csv_path)
    
    with open(csv_path) as f:
        lines = f.readlines()
        assert len(lines) == 2
        data_line = lines[1].strip().split(",")
        assert abs(float(data_line[10]) - 12.333) < 0.01


def test_generate_results_and_reports_with_dict_router_times(patch_dirs) -> None:
    """Verifies results aggregation and reports generation when router_execution_times is a dict."""
    scenarios = ["test_scen"]
    algorithms = ["test_alg"]
    vehicles = [50]
    seeds = [1]
    
    task_file = os.path.join(rb.INTERMEDIATE_DIR, "run_test_scen_test_alg_50_seed1.json")
    
    mock_run_data = {
        "algorithm_name": "test_alg",
        "scenario_name": "test_scen",
        "seed": 1,
        "vehicles": 50,
        "config_details": {
            "simulation": {
                "max_steps": 600
            }
        },
        "vehicle_travel_times": {
            "v0": 100.0,
            "v1": 150.0
        },
        "vehicle_energy_consumed": {
            "v0": 10.0,
            "v1": 12.0
        },
        "stranded_vehicles": 0,
        "total_rerouting_events": 2,
        "router_execution_times": {
            "query_0": 0.012,
            "query_1": 0.015,
            "query_2": 0.010
        }
    }
    
    with open(task_file, "w") as f:
        json.dump(mock_run_data, f)
        
    results = rb.generate_results_and_reports(scenarios, algorithms, vehicles, seeds)
    
    assert len(results) == 1
    assert results[0]["algorithm_name"] == "test_alg"
    
    csv_path = os.path.join(rb.OUTPUT_DIR, "benchmark_results.csv")
    assert os.path.exists(csv_path)
    
    with open(csv_path) as f:
        lines = f.readlines()
        assert len(lines) == 2
        data_line = lines[1].strip().split(",")
        assert abs(float(data_line[10]) - 12.333) < 0.01


def test_generate_results_and_reports_with_corrupt_json(patch_dirs) -> None:
    """Verifies that corrupted JSON files do not crash the aggregation and are skipped."""
    scenarios = ["test_scen"]
    algorithms = ["test_alg"]
    vehicles = [50]
    seeds = [1]
    
    task_file = os.path.join(rb.INTERMEDIATE_DIR, "run_test_scen_test_alg_50_seed1.json")
    
    # Write garbage content to file
    with open(task_file, "w") as f:
        f.write("{invalid json content, this should fail parsing}")
        
    results = rb.generate_results_and_reports(scenarios, algorithms, vehicles, seeds)
    
    # Verify it completed successfully without exceptions and returned an empty list
    assert len(results) == 0


def test_generate_results_and_reports_with_missing_keys(patch_dirs) -> None:
    """Verifies that checkpoints missing required schema keys are skipped gracefully."""
    scenarios = ["test_scen"]
    algorithms = ["test_alg"]
    vehicles = [50]
    seeds = [1]
    
    task_file = os.path.join(rb.INTERMEDIATE_DIR, "run_test_scen_test_alg_50_seed1.json")
    
    # Missing required 'algorithm_name' key
    mock_run_data = {
        "scenario_name": "test_scen",
        "seed": 1,
        "vehicles": 50,
        "config_details": {
            "simulation": {
                "max_steps": 600
            }
        },
        "vehicle_travel_times": {}
    }
    
    with open(task_file, "w") as f:
        json.dump(mock_run_data, f)
        
    results = rb.generate_results_and_reports(scenarios, algorithms, vehicles, seeds)
    
    # Verify it skipped the file and returned empty list
    assert len(results) == 0
