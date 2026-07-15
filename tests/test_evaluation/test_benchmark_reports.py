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


def test_e3_hybrid_variants_configuration(monkeypatch) -> None:
    """Verifies that execute_single_task configures e3-hybrid variants and objective weights correctly."""
    from src.utils.config import ScenarioConfig
    import yaml
    
    dummy_yaml = """
    name: "test_scen"
    simulation:
      network_file: "dummy.net.xml"
      traci_port: 8813
      seed: 42
    battery:
      capacity_kwh: 50.0
      mass_kg: 1500.0
      initial_soc: 0.8
    algorithms:
      objectives:
        weight_travel_time: 0.5
        weight_energy_consumption: 0.3
        weight_safety: 0.2
      aco:
        alpha: 1.0
      bco:
        colony_size: 5
      pso:
        cognitive_weight: 1.5
      e3_hybrid:
        disable_aco: False
        disable_bco: False
        disable_pso: False
        disable_elite_sharing: False
        enable_adaptive_weighting: False
    """
    
    cfg = ScenarioConfig.model_validate(yaml.safe_load(dummy_yaml))
    monkeypatch.setattr(rb, "load_scenario_config", lambda path: cfg)
    
    # Mock SumoScenarioExecutor.__init__ and execute
    class MockMetrics:
        def model_dump(self):
            return {"vehicle_travel_times": {}, "vehicle_energy_consumed": {}, "router_execution_times": []}
            
    class MockCollector:
        metrics = MockMetrics()
        
    class MockExecutor:
        def __init__(self, *args, **kwargs):
            pass
        def generate_random_traffic(self, *args, **kwargs):
            pass
        def execute(self):
            return MockCollector()
            
    monkeypatch.setattr(rb, "SumoScenarioExecutor", MockExecutor)
    monkeypatch.setattr(rb, "get_network_checksum", lambda *args: "dummy_checksum")
    
    # Verify E3-Hybrid-NoACO override
    rb.execute_single_task(("test_scen", "E3-Hybrid-NoACO", 50, 1, 0, False))
    assert cfg.algorithms.e3_hybrid.disable_aco is True
    assert cfg.algorithms.e3_hybrid.disable_bco is False
    
    # Verify E3-Hybrid-NoElite override
    rb.execute_single_task(("test_scen", "E3-Hybrid-NoElite", 50, 1, 0, False))
    assert cfg.algorithms.e3_hybrid.disable_elite_sharing is True
    
    # Verify E3-Hybrid-WithAdaptive override
    rb.execute_single_task(("test_scen", "E3-Hybrid-WithAdaptive", 50, 1, 0, False))
    assert cfg.algorithms.e3_hybrid.enable_adaptive_weighting is True
    
    # Verify E3-Hybrid-WTime override
    rb.execute_single_task(("test_scen", "E3-Hybrid-WTime", 50, 1, 0, False))
    assert cfg.algorithms.objectives.w_time == 1.0
    assert cfg.algorithms.objectives.w_energy == 0.0
    assert cfg.algorithms.objectives.w_emergency == 0.0
    
    # Verify E3-Hybrid-Balanced override
    rb.execute_single_task(("test_scen", "E3-Hybrid-Balanced", 50, 1, 0, False))
    assert cfg.algorithms.objectives.w_time == 0.33
    assert cfg.algorithms.objectives.w_energy == 0.33
    assert cfg.algorithms.objectives.w_emergency == 0.34
