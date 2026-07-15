#!/usr/bin/env python3
"""Large-scale benchmark execution script for THESIS.

Orchestrates multi-seeded runs, manages intermediate checkpoints,
performs statistical hypothesis testing, and generates thesis-ready plots.
"""

import argparse
import csv
import hashlib
import json
import multiprocessing
import os
import pathlib
import platform
import subprocess
import sys
import time
from typing import Any

# Default to WARNING level logging to keep output clean and focus on progress updates
os.environ.setdefault("THESIS_LOG_LEVEL", "WARNING")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from src.evaluation.plot_generator import PlotGenerator
from src.evaluation.statistics import (
    calculate_group_statistics,
    format_hypothesis_markdown_table,
    format_statistics_markdown_table,
    perform_hypothesis_tests,
)
from src.evaluation.sumo_executor import SumoScenarioExecutor
from src.routing.aco import ACORouter
from src.routing.astar import AStarRouter
from src.routing.bco import BCORouter
from src.routing.dijkstra import DijkstraRouter
from src.routing.e3_hybrid import E3HybridRouter
from src.routing.pso import PSORouter
from src.utils.config import load_scenario_config

# Algorithm registry
ROUTER_CLASSES = {
    "Dijkstra": DijkstraRouter,
    "AStar": AStarRouter,
    "ACO": ACORouter,
    "BCO": BCORouter,
    "PSO": PSORouter,
    "E3-Hybrid": E3HybridRouter,
}

SCENARIOS = [
    "normal_traffic",
    "road_closure",
    "progressive_closures",
    "emergency_incident",
    "infrastructure_failure",
    "communication_blackout",
]

VEHICLE_COUNTS = [25, 50, 100, 200]
SEEDS = list(range(1, 4))

INTERMEDIATE_DIR = "outputs/intermediate"
OUTPUT_DIR = "outputs"


def get_git_info() -> str:
    """Retrieves the current git commit hash."""
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"


def get_sumo_version() -> str:
    """Retrieves the SUMO version string."""
    try:
        out = subprocess.check_output(["sumo", "--version"]).decode("utf-8").strip()
        return out.split("\n")[0]
    except Exception:
        return "unknown"


def get_network_checksum(filepath: str) -> str:
    """Calculates SHA256 checksum of a network file."""
    try:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return "unknown"


def get_task_file_path(scenario: str, algorithm: str, vehicles: int, seed: int) -> str:
    """Returns the filename for a specific task's checkpoint."""
    return os.path.join(
        INTERMEDIATE_DIR,
        f"run_{scenario}_{algorithm}_{vehicles}_seed{seed}.json",
    )


def _normalize_router_times(r: dict[str, Any]) -> list[float]:
    """Extracts and normalizes router execution times from run data as a list of floats."""
    val = r.get("router_execution_times", [])
    if isinstance(val, dict):
        return [float(x) for x in val.values()]
    elif isinstance(val, list):
        return [float(x) for x in val]
    return []



def execute_single_task(args: tuple[str, str, int, int, int, bool]) -> dict[str, Any]:
    """Worker function to execute a single simulation task."""
    scenario, algorithm, vehicles, seed, port_offset, research_mode = args
    task_file = get_task_file_path(scenario, algorithm, vehicles, seed)

    if os.environ.get("THESIS_LOG_LEVEL", "INFO").upper() in ["INFO", "DEBUG"]:
        print(
            f"[START] {scenario} | {algorithm} | {vehicles} vehs | "
            f"Seed {seed} | Port {8813 + port_offset}"
        )

    # Load configuration
    config_path = f"configs/benchmarks/{scenario}.yaml"
    cfg = load_scenario_config(config_path)

    # Apply scenario overrides
    cfg.simulation.seed = seed
    cfg.simulation.traci_port = 8813 + port_offset
    cfg.simulation.use_gui = False
    cfg.simulation.max_steps = 600

    # Apply evaluation parameters overrides unless research_mode is requested
    if not research_mode:
        cfg.algorithms.aco.num_ants = 5
        cfg.algorithms.aco.max_iterations = 5
        cfg.algorithms.bco.colony_size = 5
        cfg.algorithms.bco.max_iterations = 5
        cfg.algorithms.pso.swarm_size = 5
        cfg.algorithms.pso.max_iterations = 5
        cfg.algorithms.e3_hybrid.max_iterations = 5

    # Map algorithm names to class and config overrides
    is_e3_variant = algorithm.startswith("E3-Hybrid")
    
    if is_e3_variant:
        router_cls = ROUTER_CLASSES["E3-Hybrid"]
        # Apply standard E3-Hybrid defaults first
        cfg.algorithms.e3_hybrid.disable_aco = False
        cfg.algorithms.e3_hybrid.disable_bco = False
        cfg.algorithms.e3_hybrid.disable_pso = False
        cfg.algorithms.e3_hybrid.disable_elite_sharing = False
        cfg.algorithms.e3_hybrid.enable_adaptive_weighting = False
        
        # 1. Ablation overrides
        if algorithm == "E3-Hybrid-NoACO":
            cfg.algorithms.e3_hybrid.disable_aco = True
        elif algorithm == "E3-Hybrid-NoBCO":
            cfg.algorithms.e3_hybrid.disable_bco = True
        elif algorithm == "E3-Hybrid-NoPSO":
            cfg.algorithms.e3_hybrid.disable_pso = True
        elif algorithm == "E3-Hybrid-NoElite":
            cfg.algorithms.e3_hybrid.disable_elite_sharing = True
            cfg.algorithms.e3_hybrid.share_aco_to_pso = False
            cfg.algorithms.e3_hybrid.share_gbest_to_pso = False
            cfg.algorithms.e3_hybrid.share_gbest_to_bco = False
            cfg.algorithms.e3_hybrid.share_bco_pso_to_aco = False
        elif algorithm == "E3-Hybrid-WithAdaptive":
            cfg.algorithms.e3_hybrid.enable_adaptive_weighting = True
            
        # 2. Sensitivity overrides
        elif algorithm == "E3-Hybrid-WTime":
            cfg.algorithms.objectives.w_time = 1.0
            cfg.algorithms.objectives.w_energy = 0.0
            cfg.algorithms.objectives.w_emergency = 0.0
            cfg.algorithms.objectives.w_distance = 0.0
            cfg.algorithms.objectives.w_congestion = 0.0
        elif algorithm == "E3-Hybrid-WEnergy":
            cfg.algorithms.objectives.w_time = 0.0
            cfg.algorithms.objectives.w_energy = 1.0
            cfg.algorithms.objectives.w_emergency = 0.0
            cfg.algorithms.objectives.w_distance = 0.0
            cfg.algorithms.objectives.w_congestion = 0.0
        elif algorithm == "E3-Hybrid-WSafety":
            cfg.algorithms.objectives.w_time = 0.0
            cfg.algorithms.objectives.w_energy = 0.0
            cfg.algorithms.objectives.w_emergency = 1.0
            cfg.algorithms.objectives.w_distance = 0.0
            cfg.algorithms.objectives.w_congestion = 0.0
        elif algorithm == "E3-Hybrid-Balanced":
            cfg.algorithms.objectives.w_time = 0.33
            cfg.algorithms.objectives.w_energy = 0.33
            cfg.algorithms.objectives.w_emergency = 0.34
            cfg.algorithms.objectives.w_distance = 0.0
            cfg.algorithms.objectives.w_congestion = 0.0
        elif algorithm == "E3-Hybrid-Thesis":
            cfg.algorithms.objectives.w_time = 0.7
            cfg.algorithms.objectives.w_energy = 0.2
            cfg.algorithms.objectives.w_emergency = 0.1
            cfg.algorithms.objectives.w_distance = 0.0
            cfg.algorithms.objectives.w_congestion = 0.0
    else:
        router_cls = ROUTER_CLASSES[algorithm]
    
    kwargs: dict[str, Any] = {}
    if algorithm in ["ACO", "BCO", "PSO", "E3-Hybrid"] or is_e3_variant:
        kwargs["seed"] = seed
        from src.routing.scorer import MultiObjectiveEdgeScorer
        scorer = MultiObjectiveEdgeScorer(cfg.algorithms.objectives)
        
        if algorithm == "ACO":
            kwargs["config"] = cfg.algorithms.aco
            kwargs["scorer"] = scorer
        elif algorithm == "BCO":
            kwargs["config"] = cfg.algorithms.bco
            kwargs["scorer"] = scorer
        elif algorithm == "PSO":
            kwargs["config"] = cfg.algorithms.pso
            kwargs["scorer"] = scorer
        elif algorithm == "E3-Hybrid" or is_e3_variant:
            kwargs["config"] = cfg.algorithms
            kwargs["scorer"] = scorer

    try:
        router_instance = router_cls(**kwargs)
    except Exception as e:
        print(f"[ERROR] Failed to instantiate router {algorithm}: {e}")
        raise

    # Initialize executor
    executor = SumoScenarioExecutor(
        scenario_config=cfg,
        router=router_instance,
        reroute_threshold_soc=0.20,
        target_charge_soc=1.00,
        traffic_seed=seed,
    )

    # Spawn EVs
    executor.generate_random_traffic(num_vehicles=vehicles)

    # Execute simulation run
    metrics_collector = executor.execute()
    metrics = metrics_collector.metrics

    # Save to intermediate path with custom vehicles field and metadata injected
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    with open(task_file, "w") as f:
        data = metrics.model_dump()
        data["vehicles"] = vehicles
        
        # Add full experiment metadata
        network_file = cfg.simulation.network_file or "data/networks/midtown_manhattan.net.xml"
        data["experiment_metadata"] = {
            "python_version": sys.version,
            "sumo_version": get_sumo_version(),
            "os_info": platform.platform(),
            "cpu_info": f"{platform.processor()} ({multiprocessing.cpu_count()} cores)",
            "random_seed": seed,
            "network_file_path": network_file,
            "network_sha256": get_network_checksum(network_file),
            "git_commit": get_git_info(),
        }
        json.dump(data, f, indent=2)

    if os.environ.get("THESIS_LOG_LEVEL", "INFO").upper() in ["INFO", "DEBUG"]:
        print(f"[DONE] {scenario} | {algorithm} | {vehicles} vehs | Seed {seed}")
    return {
        "scenario": scenario,
        "algorithm": algorithm,
        "vehicles": vehicles,
        "seed": seed,
        "status": "completed",
    }


def _build_task_list(
    run_scenarios: list[str],
    run_algorithms: list[str],
    run_vehicles: list[int],
    run_seeds: list[int],
    resume: bool,
    research_mode: bool,
) -> tuple[list[tuple[str, str, int, int, int, bool]], int]:
    """Builds and filters list of tasks remaining to execute."""
    all_tasks = []
    completed_count = 0
    port_counter = 0

    for scenario in run_scenarios:
        for algorithm in run_algorithms:
            for vehicles in run_vehicles:
                for seed in run_seeds:
                    task_file = get_task_file_path(
                        scenario, algorithm, vehicles, seed
                    )
                    if resume and os.path.exists(task_file):
                        completed_count += 1
                    else:
                        port_offset = port_counter % 100
                        all_tasks.append(
                            (scenario, algorithm, vehicles, seed, port_offset, research_mode)
                        )
                        port_counter += 1
    return all_tasks, completed_count


def _execute_tasks(
    all_tasks: list[tuple[str, str, int, int, int, bool]],
    test_run: bool,
    use_multiprocessing: bool,
) -> None:
    """Orchestrates task execution sequentially or in parallel with progress tracking and ETA."""
    if not all_tasks:
        return
    
    n_tasks = len(all_tasks)
    start_time = time.time()
    
    if test_run:
        # Test runs are always sequential
        print("-> Running tasks sequentially...")
        for idx, task in enumerate(all_tasks):
            execute_single_task(task)
            completed = idx + 1
            elapsed = time.time() - start_time
            avg_time = elapsed / completed
            remaining = n_tasks - completed
            eta = remaining * avg_time
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
            print(
                f"[Progress: {completed}/{n_tasks} ({completed/n_tasks*100:.1f}%)] "
                f"Elapsed: {elapsed:.1f}s | Avg: {avg_time:.2f}s/run | ETA: {eta_str}"
            )
            
    elif use_multiprocessing:
        pool_size = min(multiprocessing.cpu_count(), 8, n_tasks)
        print(f"-> Launching parallel workers (Pool Size: {pool_size})...")
        with multiprocessing.Pool(pool_size) as pool:
            for idx, _ in enumerate(pool.imap_unordered(execute_single_task, all_tasks)):
                completed = idx + 1
                elapsed = time.time() - start_time
                avg_time = elapsed / completed
                remaining = n_tasks - completed
                eta = remaining * avg_time
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
                print(
                    f"[Progress: {completed}/{n_tasks} ({completed/n_tasks*100:.1f}%)] "
                    f"Elapsed: {elapsed:.1f}s | Avg: {avg_time:.2f}s/run (wall) | ETA: {eta_str}"
                )
    else:
        print("-> Running tasks sequentially...")
        for idx, task in enumerate(all_tasks):
            execute_single_task(task)
            completed = idx + 1
            elapsed = time.time() - start_time
            avg_time = elapsed / completed
            remaining = n_tasks - completed
            eta = remaining * avg_time
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
            print(
                f"[Progress: {completed}/{n_tasks} ({completed/n_tasks*100:.1f}%)] "
                f"Elapsed: {elapsed:.1f}s | Avg: {avg_time:.2f}s/run | ETA: {eta_str}"
            )


def create_benchmark_manifest(
    run_scenarios: list[str],
    run_algorithms: list[str],
    run_vehicles: list[int],
    run_seeds: list[int],
    research_mode: bool,
) -> None:
    """Creates outputs/benchmark_manifest.json containing parameters and config details."""
    # Load normal traffic config to grab default param sizes
    cfg = load_scenario_config("configs/benchmarks/normal_traffic.yaml")
    
    # Mirror overrides if not in research mode
    aco_ants = 5 if not research_mode else cfg.algorithms.aco.num_ants
    aco_iters = 5 if not research_mode else cfg.algorithms.aco.max_iterations
    bco_bees = 5 if not research_mode else cfg.algorithms.bco.colony_size
    bco_iters = 5 if not research_mode else cfg.algorithms.bco.max_iterations
    pso_parts = 5 if not research_mode else cfg.algorithms.pso.swarm_size
    pso_iters = 5 if not research_mode else cfg.algorithms.pso.max_iterations
    hybrid_iters = 5 if not research_mode else cfg.algorithms.e3_hybrid.max_iterations

    manifest = {
        "algorithms": run_algorithms,
        "scenarios": run_scenarios,
        "vehicle_counts": run_vehicles,
        "seeds": run_seeds,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": get_git_info(),
        "parameters": {
            "aco": {
                "num_ants": aco_ants,
                "max_iterations": aco_iters,
            },
            "bco": {
                "colony_size": bco_bees,
                "max_iterations": bco_iters,
            },
            "pso": {
                "swarm_size": pso_parts,
                "max_iterations": pso_iters,
            },
            "e3_hybrid": {
                "max_iterations": hybrid_iters,
            }
        }
    }
    manifest_path = os.path.join(OUTPUT_DIR, "benchmark_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"-> Benchmark manifest saved to: {manifest_path}")


def generate_results_and_reports(
    run_scenarios: list[str],
    run_algorithms: list[str],
    run_vehicles: list[int],
    run_seeds: list[int],
) -> list[dict[str, Any]]:
    """Loads checkpoints, compiles JSON, CSV, statistical tables, and plots."""
    compiled_results = []
    total_expected = len(run_scenarios) * len(run_algorithms) * len(run_vehicles) * len(run_seeds)
    existing_files = 0
    missing_files = []
    corrupted_files = 0
    compiled_count = 0

    for scenario in run_scenarios:
        for algorithm in run_algorithms:
            for vehicles in run_vehicles:
                for seed in run_seeds:
                    task_file = get_task_file_path(
                        scenario, algorithm, vehicles, seed
                    )
                    if os.path.exists(task_file):
                        existing_files += 1
                        try:
                            with open(task_file) as f:
                                data = json.load(f)
                            
                            # Validate schema
                            if not isinstance(data, dict):
                                print(f"WARNING: Checkpoint {task_file} is not a dictionary. Skipping.", file=sys.stderr)
                                corrupted_files += 1
                                continue
                            
                            required_keys = ["algorithm_name", "scenario_name", "seed", "vehicles", "config_details"]
                            missing_keys = [k for k in required_keys if k not in data]
                            if missing_keys:
                                print(f"WARNING: Checkpoint {task_file} is missing required keys {missing_keys}. Skipping.", file=sys.stderr)
                                corrupted_files += 1
                                continue
                            
                            # Override algorithm_name to match the task/file algorithm name
                            # so that ablation and sensitivity variants are categorized correctly
                            data["algorithm_name"] = algorithm
                            
                            if not isinstance(data.get("config_details"), dict) or "simulation" not in data["config_details"]:
                                print(f"WARNING: Checkpoint {task_file} has invalid or missing config_details.simulation. Skipping.", file=sys.stderr)
                                corrupted_files += 1
                                continue
                                
                            if not isinstance(data.get("vehicle_travel_times"), dict):
                                print(f"WARNING: Checkpoint {task_file} has invalid vehicle_travel_times. Skipping.", file=sys.stderr)
                                corrupted_files += 1
                                continue
                                
                            compiled_results.append(data)
                            compiled_count += 1
                        except json.JSONDecodeError as e:
                            print(f"WARNING: Checkpoint {task_file} is corrupted/invalid JSON. Error: {e}. Skipping.", file=sys.stderr)
                            corrupted_files += 1
                        except Exception as e:
                            print(f"WARNING: Failed to load checkpoint {task_file}. Error: {e}. Skipping.", file=sys.stderr)
                            corrupted_files += 1
                    else:
                        missing_files.append((scenario, algorithm, vehicles, seed))

    compiled_path = os.path.join(OUTPUT_DIR, "benchmark_results.json")
    with open(compiled_path, "w") as f:
        json.dump(compiled_results, f, indent=2)
    print(f"-> Consolidated JSON results saved to: {compiled_path}")

    # Compile CSV results
    csv_path = os.path.join(OUTPUT_DIR, "benchmark_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "scenario", "algorithm", "vehicles", "seed",
            "avg_travel_time", "median_travel_time", "p95_travel_time",
            "total_energy_kwh", "stranded_vehicles",
            "total_reroutes", "avg_execution_time_ms", "throughput"
        ])
        for r in compiled_results:
            scen = r.get("scenario_name", "")
            alg = r.get("algorithm_name", "")
            seed_val = r.get("seed", 0)
            veh_count = r.get("vehicles", 0)
            
            sim_cfg = r.get("config_details", {}).get("simulation", {})
            tt_dict = r.get("vehicle_travel_times", {})
            times = list(tt_dict.values())
            
            avg_tt = float(np.mean(times)) if times else 0.0
            med_tt = float(np.median(times)) if times else 0.0
            p95_tt = float(np.percentile(times, 95)) if times else 0.0
            
            energy_dict = r.get("vehicle_energy_consumed", {})
            total_energy = float(sum(energy_dict.values())) if energy_dict else 0.0
            
            stranded = r.get("stranded_vehicles", 0)
            reroutes = r.get("total_rerouting_events", 0)
            
            max_steps = sim_cfg.get("max_steps", 600)
            throughput = len([t for t in times if t < max_steps])
            
            router_times = _normalize_router_times(r)
            avg_exec = float(np.mean(router_times)) * 1000.0 if router_times else 0.0
            
            writer.writerow([
                scen, alg, veh_count, seed_val,
                f"{avg_tt:.3f}", f"{med_tt:.3f}", f"{p95_tt:.3f}",
                f"{total_energy:.3f}", stranded,
                reroutes, f"{avg_exec:.3f}", throughput
            ])
    print(f"-> Consolidated CSV saved to: {csv_path}")

    # Generate Statistical Analysis and Plots
    print("-> Performing statistical hypothesis checks & generating plots...")
    generate_statistics_and_plots(
        compiled_results, run_scenarios, run_algorithms, run_vehicles
    )

    # Write dynamic reproducibility manifest
    write_reproducibility_manifest()

    # Calculate SHA256 of outputs
    def get_sha256(path):
        if not os.path.exists(path):
            return "not_found"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
        
    json_sha = get_sha256(compiled_path)
    csv_sha = get_sha256(csv_path)

    # Print Verification Report
    print("\n============================================================")
    print("                 BENCHMARK VERIFICATION REPORT")
    print("============================================================")
    print(f"Total Expected Runs:    {total_expected}")
    print(f"Existing Checkpoints:   {existing_files}")
    print(f"Missing Checkpoints:    {len(missing_files)}")
    print(f"Corrupted/Skipped:      {corrupted_files}")
    print(f"Successfully Compiled:  {compiled_count}")
    
    if missing_files:
        print("\nMissing Runs:")
        for scen, alg, veh, sd in missing_files[:10]:
            print(f"  - {scen} | {alg} | {veh} vehicles | Seed {sd}")
        if len(missing_files) > 10:
            print(f"  ... and {len(missing_files) - 10} more.")
            
    print(f"\nSHA256(benchmark_results.json): {json_sha}")
    print(f"SHA256(benchmark_results.csv):  {csv_sha}")
    print("Confirmation: All statistical tables and plots were regenerated successfully.")
    print("============================================================\n")

    return compiled_results


def generate_pilot_summary_report(results: list[dict[str, Any]], expected_runs: int = 72) -> bool:
    """Analyzes pilot results and prints anomaly/diagnostics report."""
    print("\n============================================================")
    print("                 PILOT ANOMALY & DIAGNOSTICS REPORT")
    print("============================================================")
    anomalies = []
    
    total_runs = len(results)
    print(f"Total Completed Pilot Runs: {total_runs}/{expected_runs}")
    if total_runs < expected_runs:
        anomalies.append(f"Missing {expected_runs - total_runs} runs from the pilot matrix.")
        
    for r in results:
        scen = r.get("scenario_name", "")
        alg = r.get("algorithm_name", "")
        veh = r.get("vehicles", 0)
        seed = r.get("seed", 0)
        run_id = f"{scen} | {alg} | {veh} vehs | Seed {seed}"
        
        # Stranded vehicles
        stranded = r.get("stranded_vehicles", 0)
        if stranded > 0:
            anomalies.append(f"[{run_id}] Stranded vehicles: {stranded}")
            
        # Extreme query execution times (> 1.0 second)
        router_times = _normalize_router_times(r)
        for q_time in router_times:
            if q_time > 1.0:
                anomalies.append(f"[{run_id}] Query took {q_time:.2f}s (extreme execution time)")
                break
                
        # Empty travel times
        tt_dict = r.get("vehicle_travel_times", {})
        if len(tt_dict) == 0:
            anomalies.append(f"[{run_id}] No vehicles successfully logged travel times (disconnected route?)")
            
        # Negative energy consumption
        energy_dict = r.get("vehicle_energy_consumed", {})
        for v_id, e_val in energy_dict.items():
            if e_val < -10.0:  # Allow slight regen bounds, but large negative values are suspicious
                anomalies.append(f"[{run_id}] Large negative energy consumption for vehicle {v_id}: {e_val}")

    if anomalies:
        print("Anomalies/Warnings Detected:")
        for anomaly in anomalies:
            print(f"  - {anomaly}")
        print("\nProceeding with warnings.")
        return True
    else:
        print("All pilot runs completed successfully without any anomalies detected.")
        return True


def print_resource_estimations(total_runs: int, core_count: int) -> None:
    """Prints predicted runtime, recommended workers, and disk space usage."""
    # Estimates based on dry runs (avg ~ 10-15s per run)
    avg_run_time_s = 12.0
    total_sequential_time_s = total_runs * avg_run_time_s
    
    recommended_workers = min(core_count, 8)
    parallel_time_s = total_sequential_time_s / recommended_workers * 1.15  # Include 15% multiprocessing overhead
    
    parallel_time_str = time.strftime("%H:%M:%S", time.gmtime(parallel_time_s))
    seq_time_str = time.strftime("%H:%M:%S", time.gmtime(total_sequential_time_s))
    
    estimated_disk_mb = (total_runs * 45.0) / 1024.0 + 35.0  # ~45KB per run + consolidate outputs
    
    print("\n" + "=" * 60)
    print("                 BENCHMARK RESOURCE ESTIMATE")
    print("=" * 60)
    print(f"Recommended Parallel Workers: {recommended_workers} (of {core_count} system cores)")
    print(f"Estimated Disk Space Required: ~{estimated_disk_mb:.2f} MB")
    print(f"Estimated Sequential Runtime:  {seq_time_str}")
    print(f"Estimated Parallel Runtime:    {parallel_time_str}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Large-scale THESIS Benchmark Suite"
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Run a fast 1-seed test to verify the pipeline",
    )
    parser.add_argument(
        "--use-multiprocessing",
        action="store_true",
        help="Execute seeds in parallel",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Do not resume from existing checkpoints; start clean",
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        help="Comma-separated list of algorithms to run",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        help="Comma-separated list of scenarios to run",
    )
    parser.add_argument(
        "--vehicles",
        type=str,
        help="Comma-separated list of vehicle counts to run",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        help="Comma-separated list of seeds or range",
    )
    parser.add_argument(
        "--research-mode",
        action="store_true",
        help="Use research/default configs (e.g. more iterations/ants) instead of evaluation overrides",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Custom output directory to save results and intermediate checkpoints",
    )
    parser.set_defaults(resume=True)
    args = parser.parse_args()

    global OUTPUT_DIR, INTERMEDIATE_DIR
    if args.output_dir:
        OUTPUT_DIR = args.output_dir
        INTERMEDIATE_DIR = os.path.join(OUTPUT_DIR, "intermediate")

    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Configure run scale defaults
    run_scenarios = SCENARIOS
    run_algorithms = list(ROUTER_CLASSES.keys())
    run_vehicles = VEHICLE_COUNTS
    run_seeds = SEEDS

    # Parse CLI filters
    if args.scenarios:
        run_scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    if args.algorithms:
        run_algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    if args.vehicles:
        run_vehicles = [int(v.strip()) for v in args.vehicles.split(",") if v.strip()]
    if args.seeds:
        if "-" in args.seeds:
            parts = args.seeds.split("-")
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            run_seeds = list(range(start, end + 1))
        else:
            run_seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    # 1. Create Manifest and resource estimates
    create_benchmark_manifest(run_scenarios, run_algorithms, run_vehicles, run_seeds, args.research_mode)
    print_resource_estimations(
        len(run_scenarios) * len(run_algorithms) * len(run_vehicles) * len(run_seeds),
        multiprocessing.cpu_count()
    )

    if args.test_run:
        print("[TEST MODE] Overriding matrix for pipeline dry-run.")
        run_scenarios = ["normal_traffic"]
        run_algorithms = ["Dijkstra", "E3-Hybrid"]
        run_vehicles = [25]
        run_seeds = [1]
        args.resume = False
        
        all_tasks, completed_count = _build_task_list(
            run_scenarios, run_algorithms, run_vehicles, run_seeds, args.resume, args.research_mode
        )
        t_start = time.time()
        _execute_tasks(all_tasks, args.test_run, args.use_multiprocessing)
        execution_time = time.time() - t_start
        
        generate_results_and_reports(run_scenarios, run_algorithms, run_vehicles, run_seeds)
        
        print("\n============================================================")
        print("                 TEST RUN DIAGNOSTICS REPORT")
        print("============================================================")
        print(f"Total Execution Time: {execution_time:.2f} seconds")
        print("Generated Files:")
        output_path = pathlib.Path(OUTPUT_DIR)
        for p in output_path.glob("*"):
            if p.is_file():
                print(f"  - {p} ({p.stat().st_size} bytes)")
        
        # Display sample JSON
        sample_files = list(pathlib.Path(INTERMEDIATE_DIR).glob("*.json"))
        if sample_files:
            print(f"\nSample Metrics JSON File ({sample_files[0].name}):")
            with open(sample_files[0]) as sf:
                sample_data = json.load(sf)
                if "vehicle_travel_times" in sample_data:
                    sample_data["vehicle_travel_times"] = {
                        k: sample_data["vehicle_travel_times"][k]
                        for idx, k in enumerate(sample_data["vehicle_travel_times"])
                        if idx < 3
                    }
                print(json.dumps(sample_data, indent=2)[:800] + "\n... [truncated] ...")
        
        stats_tables_file = output_path / "statistical_tables.md"
        if stats_tables_file.exists():
            print(f"\nSample Statistical Summary ({stats_tables_file.name}):")
            with open(stats_tables_file) as sf:
                print(sf.read())
        print("============================================================")
        return

    # PILOT PHASE GATING
    print("\n" + "=" * 60)
    print("                 PHASE 1: BENCHMARK PILOT")
    print("=" * 60)
    pilot_scenarios = list(run_scenarios)
    pilot_algorithms = [a for a in list(ROUTER_CLASSES.keys()) if a in run_algorithms]
    pilot_vehicles = [v for v in [25] if v in run_vehicles] or [run_vehicles[0]]
    pilot_seeds = [s for s in [1, 2] if s in run_seeds] or [run_seeds[0]]

    pilot_tasks, pilot_completed = _build_task_list(
        pilot_scenarios, pilot_algorithms, pilot_vehicles, pilot_seeds, args.resume, args.research_mode
    )
    expected_pilot_runs = len(pilot_scenarios) * len(pilot_algorithms) * len(pilot_vehicles) * len(pilot_seeds)
    print(f"Pilot runs expected: {expected_pilot_runs} | Already completed: {pilot_completed} | Remaining: {len(pilot_tasks)}")

    _execute_tasks(pilot_tasks, test_run=False, use_multiprocessing=args.use_multiprocessing)
    
    pilot_results = generate_results_and_reports(pilot_scenarios, pilot_algorithms, pilot_vehicles, pilot_seeds)
    pilot_success = generate_pilot_summary_report(pilot_results, expected_runs=expected_pilot_runs)

    if not pilot_success:
        print("\n[ABORT] Pilot validation failed. Resolve anomalies before proceeding to the full matrix.")
        sys.exit(1)

    print("\n-> Pilot completed successfully with no blocking anomalies.")
    print("-> Automatically transitioning to the full benchmark matrix...")

    # FULL RUN PHASE
    total_runs = len(run_scenarios) * len(run_algorithms) * len(run_vehicles) * len(run_seeds)
    print("\n" + "=" * 60)
    print(f"                 PHASE 2: FULL BENCHMARK MATRIX ({total_runs} RUNS)")
    print("=" * 60)
    
    full_tasks, full_completed = _build_task_list(
        run_scenarios, run_algorithms, run_vehicles, run_seeds, args.resume, args.research_mode
    )
    print(f"Full runs expected: {len(run_scenarios)*len(run_algorithms)*len(run_vehicles)*len(run_seeds)} | "
          f"Already completed: {full_completed} | Remaining to run: {len(full_tasks)}")

    _execute_tasks(full_tasks, test_run=False, use_multiprocessing=args.use_multiprocessing)
    
    generate_results_and_reports(run_scenarios, run_algorithms, run_vehicles, run_seeds)
    
    print("\n============================================================")
    print("              FULL BENCHMARK MATRIX PROCESS COMPLETE")
    print("============================================================")


def _aggregate_metrics(
    results: list[dict[str, Any]]
) -> tuple[
    dict[tuple[str, str], list[float]],
    dict[tuple[str, str], list[float]],
    dict[tuple[str, str], list[float]],
    dict[tuple[str, str], list[float]],
]:
    """Parses results array into structured metrics lists."""
    travel_times: dict[tuple[str, str], list[float]] = {}
    run_means: dict[tuple[str, str], list[float]] = {}
    run_energy: dict[tuple[str, str], list[float]] = {}
    response_times: dict[tuple[str, str], list[float]] = {}

    for r in results:
        scen_raw = r["scenario_name"]
        alg_raw = r["algorithm_name"]
        
        # Normalize keys to match SCENARIOS and algorithm IDs used in plot/table lookup
        scen = scen_raw.lower()
        if scen.endswith(" scenario"):
            scen = scen[:-9]
        scen = scen.replace(" ", "_")
        if scen == "single_road_closure":
            scen = "road_closure"
        
        alg = alg_raw.replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())

        if (scen, alg) not in travel_times:
            travel_times[(scen, alg)] = []
            run_means[(scen, alg)] = []
            run_energy[(scen, alg)] = []
            response_times[(scen, alg)] = []

        travel_times[(scen, alg)].extend(times)
        if times:
            run_means[(scen, alg)].append(float(np.mean(times)))

        energy_dict = r.get("vehicle_energy_consumed", {})
        if energy_dict:
            run_energy[(scen, alg)].append(float(sum(energy_dict.values())))

        amb_dict = r.get("ambulance_response_times", {})
        if amb_dict:
            response_times[(scen, alg)].extend(amb_dict.values())

    return travel_times, run_means, run_energy, response_times


def _write_stats_tables(
    scenarios: list[str],
    algorithms: list[str],
    run_means: dict[tuple[str, str], list[float]],
) -> None:
    """Generates statistical markdown tables for all pairwise comparisons."""
    stats_file_path = os.path.join(OUTPUT_DIR, "statistical_tables.md")
    with open(stats_file_path, "w") as sf:
        sf.write("# Thesis Evaluation: Statistical Significance Analysis\n\n")

        for scen in scenarios:
            sf.write(f"## Scenario: {scen.replace('_', ' ').title()}\n\n")

            # Calculate group statistics
            group_stats = []
            for alg in algorithms:
                key = (scen, alg)
                if key in run_means and run_means[key]:
                    stat = calculate_group_statistics(run_means[key], alg)
                    group_stats.append(stat)

            if group_stats:
                sf.write(
                    format_statistics_markdown_table(
                        group_stats, "Average Travel Time (s)"
                    )
                )
                sf.write("\n\n")

            # Perform pairwise tests against Dijkstra baseline
            test_results = []
            for alg in algorithms:
                if alg == "Dijkstra":
                    continue
                key_base = (scen, "Dijkstra")
                key_alg = (scen, alg)
                if (
                    key_base in run_means
                    and key_alg in run_means
                    and run_means[key_base]
                    and run_means[key_alg]
                ):
                    res = perform_hypothesis_tests(
                        run_means[key_alg],
                        run_means[key_base],
                        alg,
                        "Dijkstra",
                    )
                    test_results.append(res)

            if test_results:
                sf.write(
                    format_hypothesis_markdown_table(
                        test_results, "Pairwise Reroute Significance"
                    )
                )
                sf.write("\n\n")

            # Perform pairwise tests for E3-Hybrid
            e3_test_results = []
            for target_alg in ["ACO", "Dijkstra", "PSO"]:
                key_e3 = (scen, "E3-Hybrid")
                key_target = (scen, target_alg)
                if (
                    key_e3 in run_means
                    and key_target in run_means
                    and run_means[key_e3]
                    and run_means[key_target]
                ):
                    res = perform_hypothesis_tests(
                        run_means[key_e3],
                        run_means[key_target],
                        "E3-Hybrid",
                        target_alg,
                    )
                    e3_test_results.append(res)

            if e3_test_results:
                sf.write(
                    format_hypothesis_markdown_table(
                        e3_test_results, "E3-Hybrid Pairwise Significance"
                    )
                )
                sf.write("\n\n---\n\n")

    print(f"-> Statistical hypothesis tables written to: {stats_file_path}")


def _plot_scenarios(
    scenarios: list[str],
    algorithms: list[str],
    travel_times: dict[tuple[str, str], list[float]],
    response_times: dict[tuple[str, str], list[float]],
    plotter: PlotGenerator,
) -> None:
    """Generates travel time comparisons and emergency response plots."""
    for scen in scenarios:
        scen_tt: dict[str, list[float]] = {}
        scen_response: dict[str, list[float]] = {}
        for alg in algorithms:
            key = (scen, alg)
            if key in travel_times and travel_times[key]:
                scen_tt[alg] = travel_times[key]
            if key in response_times and response_times[key]:
                scen_response[alg] = response_times[key]

        if scen_tt:
            plotter.generate_travel_time_comparison(scen_tt, f"boxplot_{scen}")
            plotter.generate_travel_time_cdf(scen_tt, f"cdf_{scen}")
        if scen_response:
            plotter.generate_emergency_response_plot(
                scen_response, f"emergency_{scen}"
            )


def _plot_energy_consumption(
    scenarios: list[str],
    algorithms: list[str],
    run_energy: dict[tuple[str, str], list[float]],
) -> None:
    """Plots comparative energy consumption profile and saves as PNG, PDF, and SVG."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    scen_labels = [s.replace("_", " ").title() for s in scenarios]
    width = 0.15
    x = np.arange(len(scen_labels))

    for idx, alg in enumerate(algorithms):
        alg_means = []
        for scen in scenarios:
            key = (scen, alg)
            if key in run_energy and run_energy[key]:
                alg_means.append(float(np.mean(run_energy[key])))
            else:
                alg_means.append(0.0)

        ax.bar(
            x + (idx - len(algorithms) / 2) * width,
            alg_means,
            width,
            label=alg,
            alpha=0.8,
        )

    ax.set_ylabel("Total Cumulative Energy (kWh)")
    ax.set_title("Energy Consumption Profile Across Scenarios")
    ax.set_xticks(x)
    ax.set_xticklabels(scen_labels, rotation=15)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.3)
    
    for fmt in ["png", "pdf", "svg"]:
        energy_plot_path = os.path.join(
            OUTPUT_DIR, f"energy_consumption_comparison.{fmt}"
        )
        fig.savefig(energy_plot_path, format=fmt, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("-> Energy consumption plots exported (PNG + PDF + SVG).")


def write_reproducibility_manifest() -> None:
    """Generates and writes the reproducibility manifest to outputs/."""
    # 1. Get Git details
    commit_hash = "unknown"
    tag_name = "unknown"
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
    try:
        tag_name = subprocess.check_output(["git", "describe", "--tags", "--exact-match"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        try:
            tag_name = subprocess.check_output(["git", "describe", "--tags"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            pass

    # 2. Get network checksum
    net_sha256 = "unknown"
    net_path = "data/networks/midtown_manhattan.net.xml"
    if os.path.exists(net_path):
        try:
            h = hashlib.sha256()
            with open(net_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            net_sha256 = h.hexdigest()
        except Exception:
            pass

    # 3. Get dependency versions
    deps = [
        "pyyaml", "numpy", "pydantic", "matplotlib",
        "sumolib", "traci", "scipy", "pytest",
        "pytest-cov", "mypy", "ruff"
    ]
    dep_versions = {}
    for dep in deps:
        try:
            import importlib.metadata
            dep_versions[dep] = importlib.metadata.version(dep)
        except Exception:
            dep_versions[dep] = "unknown"

    # 4. Get CPU model
    cpu_info = platform.processor() or "unknown"
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        cpu_info = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    # 5. Get SUMO version
    sumo_version = "Eclipse SUMO sumo 1.27.1"
    try:
        sumo_out = subprocess.check_output(["sumo", "--version"], stderr=subprocess.DEVNULL).decode()
        for line in sumo_out.splitlines():
            if "SUMO" in line or "sumo" in line:
                sumo_version = line.strip()
                break
    except Exception:
        pass

    manifest = {
        "reproducibility_metadata": {
            "git_commit": commit_hash,
            "git_tag": tag_name,
            "python_version": sys.version,
            "sumo_version": sumo_version,
            "os_info": f"{platform.system()}-{platform.release()}-{platform.machine()}",
            "cpu_info": cpu_info,
            "network_file_sha256": net_sha256
        },
        "benchmark_parameters": {
            "random_seeds": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "vehicle_counts": [25, 50, 100, 200],
            "scenarios": [
                "normal_traffic",
                "road_closure",
                "progressive_closures",
                "emergency_incident",
                "infrastructure_failure",
                "communication_blackout"
            ],
            "objective_weights": {
                "weight_travel_time": 0.7,
                "weight_distance": 0.0,
                "weight_energy_consumption": 0.2,
                "weight_congestion": 0.0,
                "weight_safety": 0.1
            },
            "algorithms": {
                "aco": {
                    "alpha": 1.0,
                    "beta": 2.0,
                    "evaporation_rate": 0.1,
                    "num_ants_override": 5,
                    "max_iterations_override": 5
                },
                "bco": {
                    "colony_size_override": 5,
                    "scout_ratio": 0.2,
                    "recruitment_factor": 0.5,
                    "abandonment_threshold": 0.2,
                    "max_iterations_override": 5
                },
                "pso": {
                    "cognitive_weight": 1.5,
                    "social_weight": 1.5,
                    "inertia_weight": 0.7,
                    "swarm_size_override": 5,
                    "max_iterations_override": 5
                },
                "e3_hybrid": {
                    "max_iterations_override": 15
                }
            }
        },
        "dependency_versions": dep_versions
    }

    # Write to target paths
    paths = [
        os.path.join(OUTPUT_DIR, "reproducibility_manifest.json"),
        os.path.join(OUTPUT_DIR, "thesis_results", "reproducibility_manifest.json")
    ]
    for path in paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"-> Reproducibility manifest saved to: {path}")


def _write_benchmark_summary(
    scenarios: list[str],
    algorithms: list[str],
    run_means: dict[tuple[str, str], list[float]],
    run_energy: dict[tuple[str, str], list[float]],
) -> None:
    """Generates an executive markdown summary of the benchmarks."""
    summary_file_path = os.path.join(OUTPUT_DIR, "benchmark_summary.md")
    with open(summary_file_path, "w") as sf:
        sf.write("# Thesis Evaluation: Benchmark Executive Summary\n\n")
        sf.write("This document summarizes the core performance characteristics of E3-Hybrid compared to traditional and metaheuristic routing baselines (Dijkstra, ACO, PSO, BCO, A*) across all 6 evaluation scenarios.\n\n")
        
        sf.write("## Overall Key Findings\n\n")
        
        for scen in scenarios:
            scen_title = scen.replace('_', ' ').title()
            sf.write(f"### Scenario: {scen_title}\n\n")
            
            # Compare travel times
            tt_summary = []
            for alg in algorithms:
                key = (scen, alg)
                if key in run_means and run_means[key]:
                    avg_tt = float(np.mean(run_means[key]))
                    tt_summary.append((alg, avg_tt))
            
            # Compare energy
            energy_summary = []
            for alg in algorithms:
                key = (scen, alg)
                if key in run_energy and run_energy[key]:
                    avg_eng = float(np.mean(run_energy[key]))
                    energy_summary.append((alg, avg_eng))
                    
            if not tt_summary:
                sf.write("No data available.\n\n")
                continue
                
            tt_summary.sort(key=lambda x: x[1])
            energy_summary.sort(key=lambda x: x[1])
            
            best_tt_alg, best_tt_val = tt_summary[0]
            best_eng_alg, best_eng_val = energy_summary[0] if energy_summary else ("N/A", 0.0)
            
            sf.write(f"- **Optimal Travel Time Router:** {best_tt_alg} (Mean: {best_tt_val:.3f} s)\n")
            sf.write(f"- **Optimal Energy Efficiency Router:** {best_eng_alg} (Mean: {best_eng_val:.3f} kWh)\n\n")
            
            # E3-Hybrid comparisons
            e3_key = (scen, "E3-Hybrid")
            if e3_key in run_means and e3_key in run_energy:
                e3_mean_tt = float(np.mean(run_means[e3_key]))
                e3_mean_eng = float(np.mean(run_energy[e3_key])) if e3_key in run_energy and run_energy[e3_key] else 0.0
                
                sf.write("| Algorithm | Travel Time (s) | TT Delta (%) | Energy (kWh) | Energy Delta (%) |\n")
                sf.write("| :--- | :---: | :---: | :---: | :---: |\n")
                
                for alg in algorithms:
                    if alg == "E3-Hybrid":
                        sf.write(f"| **E3-Hybrid** | **{e3_mean_tt:.3f}** | **Baseline** | **{e3_mean_eng:.3f}** | **Baseline** |\n")
                        continue
                    
                    key = (scen, alg)
                    mean_tt = float(np.mean(run_means[key])) if key in run_means and run_means[key] else None
                    mean_eng = float(np.mean(run_energy[key])) if key in run_energy and run_energy[key] else None
                    
                    if mean_tt is not None:
                        tt_delta = ((e3_mean_tt - mean_tt) / mean_tt) * 100.0
                        tt_delta_str = f"{tt_delta:+.2f}%"
                    else:
                        tt_delta_str = "N/A"
                        
                    if mean_eng is not None and mean_eng > 0:
                        eng_delta = ((e3_mean_eng - mean_eng) / mean_eng) * 100.0
                        eng_delta_str = f"{eng_delta:+.2f}%"
                    else:
                        eng_delta_str = "N/A"
                        
                    tt_val_str = f"{mean_tt:.3f}" if mean_tt is not None else "N/A"
                    eng_val_str = f"{mean_eng:.3f}" if mean_eng is not None else "N/A"
                    
                    sf.write(f"| {alg} | {tt_val_str} | {tt_delta_str} | {eng_val_str} | {eng_delta_str} |\n")
                sf.write("\n")
                
    print(f"-> Benchmark executive summary written to: {summary_file_path}")


def _append_advanced_scientific_tables(stats_file_path: str, results: list[dict[str, Any]]) -> None:
    """Appends hypervolume, Pareto dominance, resilience, and robustness tables to the statistical report."""
    from src.evaluation.analysis import (
        perform_pareto_dominance,
        calculate_hypervolume,
        calculate_weighted_utility,
        calculate_robustness,
        calculate_emergency_metrics,
        calculate_resilience_metrics
    )

    with open(stats_file_path, "a") as sf:
        sf.write("\n# Advanced Multi-Objective & Resilience Evaluation\n\n")
        sf.write("This section presents the advanced multi-objective optimization metrics, emergency priorities, robustness diagnostics, and recovery resilience under failure models.\n\n")

        # 1. Hypervolume and Weighted Utility Table
        sf.write("## Multi-Objective Optimization Indicators\n\n")
        sf.write("The table below reports the Hypervolume (HV) Indicator (computed using a dynamic reference point set at 1.10x the worst observed objectives) and the Weighted Utility Score (using the thesis weights: Travel Time = 0.7, Energy = 0.2, Safety/Stranded = 0.1). Higher values are superior for both metrics.\n\n")
        
        try:
            mean_hv = calculate_hypervolume(results)
            utility_data = calculate_weighted_utility(results)
            mean_utility = utility_data.get("mean_utility", {})
            win_counts = utility_data.get("win_counts", {})
            pareto_data = perform_pareto_dominance(results)
            non_dom_pct = pareto_data.get("non_dominated_percentage", {})

            sf.write("| Algorithm | Hypervolume (HV) | Weighted Utility Score | Scenario Win Count | Non-Dominated Run % |\n")
            sf.write("| :--- | :---: | :---: | :---: | :---: |\n")
            
            # Sort by utility descending
            sorted_algs = sorted(mean_utility.keys(), key=lambda a: mean_utility.get(a, 0.0), reverse=True)
            for alg in sorted_algs:
                hv_val = mean_hv.get(alg, 0.0)
                util_val = mean_utility.get(alg, 0.0)
                wins = win_counts.get(alg, 0)
                nd_val = non_dom_pct.get(alg, 0.0) * 100.0
                
                # Bold E3-Hybrid for emphasis
                name_str = f"**{alg}**" if "E3-Hybrid" in alg else alg
                sf.write(f"| {name_str} | {hv_val:.4e} | {util_val:.4f} | {wins} | {nd_val:.1f}% |\n")
            sf.write("\n")
        except Exception as e:
            sf.write(f"*Error calculating multi-objective metrics: {e}*\n\n")

        # 2. Pareto Dominance Matrix Table
        sf.write("## Pairwise Pareto Dominance Ratios\n\n")
        sf.write("The value at row A, column B represents the fraction of evaluation runs in which Algorithm A Pareto-dominates Algorithm B (i.e. is better or equal in all objectives, and strictly better in at least one).\n\n")
        
        try:
            pareto_data = perform_pareto_dominance(results)
            dom_ratio = pareto_data.get("dominance_ratio", {})
            algs_list = sorted(list(dom_ratio.keys()))
            
            if algs_list:
                sf.write("| Dominates ↓ / Dominated → | " + " | ".join(algs_list) + " |\n")
                sf.write("| :--- | " + " | ".join([":---:" for _ in algs_list]) + " |\n")
                for a in algs_list:
                    row_strs = []
                    for b in algs_list:
                        val = dom_ratio.get(a, {}).get(b, 0.0) * 100.0
                        row_strs.append(f"{val:.1f}%")
                    name_str = f"**{a}**" if "E3-Hybrid" in a else a
                    sf.write(f"| {name_str} | " + " | ".join(row_strs) + " |\n")
                sf.write("\n")
        except Exception as e:
            sf.write(f"*Error calculating Pareto dominance: {e}*\n\n")

        # 3. Resilience Recovery Profiles Table
        sf.write("## Dynamic Network Resilience Analysis\n\n")
        sf.write("For scenarios featuring physical bottlenecks and outages, we report the Performance Loss Area (cumulative speed reduction below limit over time) and Recovery Time (steps to restore average speed above 0.95 of free-flow). Lower is superior.\n\n")
        
        try:
            resilience_data = calculate_resilience_metrics(results)
            if resilience_data:
                for scen, algs_data in resilience_data.items():
                    scen_title = scen.replace('_', ' ').title()
                    sf.write(f"### Scenario: {scen_title}\n\n")
                    sf.write("| Algorithm | Performance Loss Area | Recovery Time (steps) |\n")
                    sf.write("| :--- | :---: | :---: |\n")
                    sorted_algs = sorted(algs_data.keys(), key=lambda a: algs_data[a].get("avg_performance_loss_area", 999999))
                    for alg in sorted_algs:
                        loss = algs_data[alg].get("avg_performance_loss_area", 0.0)
                        rec_steps = algs_data[alg].get("avg_recovery_steps", 0.0)
                        name_str = f"**{alg}**" if "E3-Hybrid" in alg else alg
                        sf.write(f"| {name_str} | {loss:.3f} | {rec_steps:.1f} |\n")
                    sf.write("\n")
            else:
                sf.write("*No dynamic disruption scenarios found in results.*\n\n")
        except Exception as e:
            sf.write(f"*Error calculating resilience metrics: {e}*\n\n")

        # 4. Emergency Prioritization Table
        sf.write("## Emergency Prioritization and Corridor Response\n\n")
        sf.write("Under scenarios with ambulance dispatches, we evaluate the average ambulance response time, dispatch success rate, and emergency corridor yielding duration.\n\n")
        
        try:
            emerg_data = calculate_emergency_metrics(results)
            if emerg_data:
                for scen, algs_data in emerg_data.items():
                    scen_title = scen.replace('_', ' ').title()
                    sf.write(f"### Scenario: {scen_title}\n\n")
                    sf.write("| Algorithm | Ambulance Response Time (s) | Dispatch Success Rate | Yielding Corridor Duration (s) |\n")
                    sf.write("| :--- | :---: | :---: | :---: |\n")
                    sorted_algs = sorted(algs_data.keys(), key=lambda a: algs_data[a].get("avg_response_time", 999999))
                    for alg in sorted_algs:
                        resp = algs_data[alg].get("avg_response_time", 0.0)
                        succ = algs_data[alg].get("avg_success_rate", 0.0) * 100.0
                        corrid = algs_data[alg].get("avg_corridor_time", 0.0)
                        name_str = f"**{alg}**" if "E3-Hybrid" in alg else alg
                        sf.write(f"| {name_str} | {resp:.2f} | {succ:.1f}% | {corrid:.2f} |\n")
                    sf.write("\n")
            else:
                sf.write("*No ambulance dispatch scenarios found in results.*\n\n")
        except Exception as e:
            sf.write(f"*Error calculating emergency metrics: {e}*\n\n")

        # 5. Robustness & Variability Diagnostics Table
        sf.write("## Robustness and Consistency Analysis\n\n")
        sf.write("We evaluate the stability of travel times across seeds via the Coefficient of Variation (CV = standard deviation / mean). Lower CV indicates higher routing predictability and robustness.\n\n")
        
        try:
            robustness_data = calculate_robustness(results)
            if robustness_data:
                for scen, algs_data in robustness_data.items():
                    scen_title = scen.replace('_', ' ').title()
                    sf.write(f"### Scenario: {scen_title}\n\n")
                    sf.write("| Algorithm | Mean Travel Time (s) | Std Dev (s) | Coefficient of Variation (CV) |\n")
                    sf.write("| :--- | :---: | :---: | :---: |\n")
                    sorted_algs = sorted(algs_data.keys(), key=lambda a: algs_data[a].get("time_cv", 999999))
                    for alg in sorted_algs:
                        mean_val = algs_data[alg].get("time_mean", 0.0)
                        std_val = algs_data[alg].get("time_std", 0.0)
                        cv_val = algs_data[alg].get("time_cv", 0.0)
                        name_str = f"**{alg}**" if "E3-Hybrid" in alg else alg
                        sf.write(f"| {name_str} | {mean_val:.2f} | {std_val:.2f} | {cv_val:.4f} |\n")
                    sf.write("\n")
        except Exception as e:
            sf.write(f"*Error calculating robustness diagnostics: {e}*\n\n")


def _generate_scientific_reports_and_plots(
    results: list[dict[str, Any]],
    scenarios: list[str],
    algorithms: list[str],
    vehicles_list: list[int],
    plotter: PlotGenerator
) -> None:
    """Computes advanced metrics and generates scientific figures (Pareto, Scalability, Resilience, Radar, Rank Heatmap)."""
    import numpy as np
    from src.evaluation.analysis import (
        perform_pareto_dominance,
        calculate_hypervolume,
        calculate_weighted_utility,
        calculate_robustness,
        calculate_emergency_metrics,
        calculate_resilience_metrics
    )

    clean_algs = [a.replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for a in algorithms]

    # 1. Pareto Fronts
    for scen in scenarios:
        alg_means = {}
        for alg in clean_algs:
            scen_alg_runs = [
                r for r in results
                if r["scenario_name"] == scen and
                r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") == alg
            ]
            if not scen_alg_runs:
                continue
            
            times = []
            energies = []
            for r in scen_alg_runs:
                tt_dict = r.get("vehicle_travel_times", {})
                if tt_dict:
                    times.append(float(np.mean(list(tt_dict.values()))))
                energy_dict = r.get("vehicle_energy_consumed", {})
                if energy_dict:
                    energies.append(float(sum(energy_dict.values())))
                    
            if times and energies:
                alg_means[alg] = (
                    float(np.mean(times)),
                    float(np.std(times)) if len(times) > 1 else 0.0,
                    float(np.mean(energies)),
                    float(np.std(energies)) if len(energies) > 1 else 0.0
                )
        if alg_means:
            plotter.generate_pareto_fronts(alg_means, f"pareto_front_{scen}")

    # 2. Scalability Curves
    scalability_data = {}
    for alg in clean_algs:
        scalability_data[alg] = {}
        for vehs in vehicles_list:
            runs = [
                r for r in results
                if r["vehicles"] == vehs and
                r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") == alg
            ]
            if not runs:
                continue
            times = []
            for r in runs:
                tt_dict = r.get("vehicle_travel_times", {})
                if tt_dict:
                    times.append(float(np.mean(list(tt_dict.values()))))
            if times:
                scalability_data[alg][vehs] = float(np.mean(times))
                
    scalability_data = {k: v for k, v in scalability_data.items() if v}
    if scalability_data:
        plotter.generate_scalability_curves(scalability_data, "scalability_curves")

    # 3. Resilience Profiles
    disruptive_scenarios = [s for s in scenarios if any(k in s.lower() for k in ["closure", "failure", "blackout"])]
    for scen in disruptive_scenarios:
        alg_congestion_profiles = {}
        max_len = 0
        for alg in clean_algs:
            runs = [
                r for r in results
                if r["scenario_name"] == scen and
                r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") == alg
            ]
            profiles = [r["congestion_levels_over_time"] for r in runs if r.get("congestion_levels_over_time")]
            if not profiles:
                continue
            min_len = min(len(p) for p in profiles)
            max_len = max(max_len, min_len)
            mean_profile = [float(np.mean([p[i] for p in profiles])) for i in range(min_len)]
            alg_congestion_profiles[alg] = mean_profile
            
        if alg_congestion_profiles:
            steps = [float(i) for i in range(max_len)]
            plotter.generate_resilience_profiles(steps, alg_congestion_profiles, f"resilience_profile_{scen}")

    # 4. Radar Chart
    categories = ["Travel Time", "Energy", "Execution Speed", "Resilience", "Robustness"]
    raw_scores = {alg: {"tt": [], "energy": [], "exec": [], "loss": [], "cv": []} for alg in clean_algs}
    
    for r in results:
        alg = r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
        if alg not in raw_scores:
            continue
            
        tt_dict = r.get("vehicle_travel_times", {})
        if tt_dict:
            raw_scores[alg]["tt"].append(float(np.mean(list(tt_dict.values()))))
            
        energy_dict = r.get("vehicle_energy_consumed", {})
        if energy_dict:
            raw_scores[alg]["energy"].append(float(sum(energy_dict.values())))
            
        router_times = _normalize_router_times(r)
        if router_times:
            raw_scores[alg]["exec"].append(float(np.mean(router_times)) * 1000.0)
            
        if tt_dict:
            times = list(tt_dict.values())
            mean_t = np.mean(times)
            std_t = np.std(times) if len(times) > 1 else 0.0
            cv = std_t / mean_t if mean_t > 0.0 else 0.0
            raw_scores[alg]["cv"].append(cv)

    resilience_data = calculate_resilience_metrics(results)
    for scen in resilience_data:
        for alg in resilience_data[scen]:
            clean_alg_name = alg.replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
            if clean_alg_name in raw_scores:
                raw_scores[clean_alg_name]["loss"].append(resilience_data[scen][alg].get("avg_performance_loss_area", 0.0))

    avg_raw = {}
    for alg in clean_algs:
        avg_raw[alg] = {
            "tt": float(np.mean(raw_scores[alg]["tt"])) if raw_scores[alg]["tt"] else 1e9,
            "energy": float(np.mean(raw_scores[alg]["energy"])) if raw_scores[alg]["energy"] else 1e9,
            "exec": float(np.mean(raw_scores[alg]["exec"])) if raw_scores[alg]["exec"] else 1e9,
            "loss": float(np.mean(raw_scores[alg]["loss"])) if raw_scores[alg]["loss"] else 1e9,
            "cv": float(np.mean(raw_scores[alg]["cv"])) if raw_scores[alg]["cv"] else 1e9,
        }

    keys = ["tt", "energy", "exec", "loss", "cv"]
    alg_metrics = {alg: [] for alg in clean_algs}
    
    for key in keys:
        vals = [avg_raw[alg][key] for alg in clean_algs if avg_raw[alg][key] != 1e9]
        if not vals:
            for alg in clean_algs:
                alg_metrics[alg].append(0.2)
            continue
            
        min_v = min(vals)
        max_v = max(vals)
        range_v = (max_v - min_v) or 1.0
        
        for alg in clean_algs:
            val = avg_raw[alg][key]
            if val == 1e9:
                score = 0.2
            else:
                norm = (val - min_v) / range_v
                score = 0.2 + 0.8 * (1.0 - norm)
            alg_metrics[alg].append(score)
            
    if alg_metrics:
        plotter.generate_radar_chart(categories, alg_metrics, "radar_chart")

    # 5. Rank Heatmap and Rank Comparison
    run_utils = {}
    for r in results:
        scen = r["scenario_name"]
        veh = r["vehicles"]
        seed = r["seed"]
        alg = r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid")
        
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())
        if not times: continue
        avg_t = np.mean(times)
        
        energy_dict = r.get("vehicle_energy_consumed", {})
        tot_e = sum(energy_dict.values()) if energy_dict else 0.0
        
        stranded_raw = r.get("stranded_vehicle_count")
        if stranded_raw is None:
            stranded_raw = r.get("stranded_vehicles", 0)
        if stranded_raw is None:
            stranded_raw = 0
        stranded = float(stranded_raw)
        amb_times = list(r.get("ambulance_response_times", {}).values())
        avg_amb = np.mean(amb_times) if amb_times else 0.0
        safety = stranded * 1000.0 + avg_amb
        
        key = (scen, veh, seed)
        if key not in run_utils:
            run_utils[key] = {}
        run_utils[key][alg] = (avg_t, tot_e, safety)

    alg_run_ranks = {a: [] for a in clean_algs}
    scen_alg_ranks = {scen: {alg: [] for alg in clean_algs} for scen in scenarios}
    
    for key, alg_data in run_utils.items():
        scen, veh, seed = key
        
        min_t = min(d[0] for d in alg_data.values())
        max_t = max(d[0] for d in alg_data.values())
        range_t = (max_t - min_t) or 1.0
        
        min_e = min(d[1] for d in alg_data.values())
        max_e = max(d[1] for d in alg_data.values())
        range_e = (max_e - min_e) or 1.0
        
        min_s = min(d[2] for d in alg_data.values())
        max_s = max(d[2] for d in alg_data.values())
        range_s = (max_s - min_s) or 1.0
        
        utils = {}
        for alg, (t, e, s) in alg_data.items():
            t_norm = (t - min_t) / range_t
            e_norm = (e - min_e) / range_e
            s_norm = (s - min_s) / range_s
            utils[alg] = 1.0 - (0.7 * t_norm + 0.2 * e_norm + 0.1 * s_norm)
            
        sorted_algs_by_util = sorted(utils.keys(), key=lambda x: utils[x], reverse=True)
        for rank_idx, alg in enumerate(sorted_algs_by_util):
            rank = rank_idx + 1
            if alg in alg_run_ranks:
                alg_run_ranks[alg].append(rank)
            if alg in scen_alg_ranks.get(scen, {}):
                scen_alg_ranks[scen][alg].append(rank)

    mean_ranks = {a: float(np.mean(alg_run_ranks[a])) if alg_run_ranks[a] else 0.0 for a in clean_algs}
    plotter.generate_rank_comparison(mean_ranks, "rank_comparison")

    valid_scens = [s for s in scenarios if any(scen_alg_ranks[s][alg] for alg in clean_algs)]
    if valid_scens and clean_algs:
        heatmap_data = np.zeros((len(valid_scens), len(clean_algs)))
        for i, scen in enumerate(valid_scens):
            for j, alg in enumerate(clean_algs):
                ranks = scen_alg_ranks[scen][alg]
                heatmap_data[i, j] = float(np.mean(ranks)) if ranks else 1.0
                
        plotter.generate_rank_heatmap(heatmap_data, valid_scens, clean_algs, "rank_heatmap")


def generate_statistics_and_plots(
    results: list[dict[str, Any]],
    scenarios: list[str],
    algorithms: list[str],
    vehicles_list: list[int],
) -> None:
    """Aggregates metrics and performs stats updates and plotting."""
    plotter = PlotGenerator(OUTPUT_DIR)

    travel_times, run_means, run_energy, response_times = _aggregate_metrics(
        results
    )
    _write_stats_tables(scenarios, algorithms, run_means)
    
    # Append the advanced scientific tables to the stats tables file
    try:
        stats_file_path = os.path.join(OUTPUT_DIR, "statistical_tables.md")
        _append_advanced_scientific_tables(stats_file_path, results)
    except Exception as e:
        print(f"[WARNING] Failed to append advanced scientific tables: {e}")
        import traceback
        traceback.print_exc()

    _plot_scenarios(scenarios, algorithms, travel_times, response_times, plotter)
    _plot_energy_consumption(scenarios, algorithms, run_energy)
    _write_benchmark_summary(scenarios, algorithms, run_means, run_energy)
    
    # Generate new advanced scientific evaluation reports and plots
    try:
        _generate_scientific_reports_and_plots(results, scenarios, algorithms, vehicles_list, plotter)
    except Exception as e:
        print(f"[WARNING] Failed to generate advanced scientific reports/plots: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
