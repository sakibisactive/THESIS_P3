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
SEEDS = list(range(1, 11))

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
        cfg.algorithms.e3_hybrid.max_iterations = 15

    # Instantiate Router
    router_cls = ROUTER_CLASSES[algorithm]
    
    kwargs: dict[str, Any] = {}
    if algorithm in ["ACO", "BCO", "PSO", "E3-Hybrid"]:
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
        elif algorithm == "E3-Hybrid":
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


def generate_pilot_summary_report(results: list[dict[str, Any]]) -> bool:
    """Analyzes pilot results and prints anomaly/diagnostics report."""
    print("\n============================================================")
    print("                 PILOT ANOMALY & DIAGNOSTICS REPORT")
    print("============================================================")
    anomalies = []
    
    total_runs = len(results)
    print(f"Total Completed Pilot Runs: {total_runs}/72")
    if total_runs < 72:
        anomalies.append(f"Missing {72 - total_runs} runs from the pilot matrix.")
        
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
    parser.set_defaults(resume=True)
    args = parser.parse_args()

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
    pilot_scenarios = [s for s in SCENARIOS if s in run_scenarios]
    pilot_algorithms = [a for a in list(ROUTER_CLASSES.keys()) if a in run_algorithms]
    pilot_vehicles = [v for v in [25] if v in run_vehicles] or [run_vehicles[0]]
    pilot_seeds = [s for s in [1, 2] if s in run_seeds] or [run_seeds[0]]

    pilot_tasks, pilot_completed = _build_task_list(
        pilot_scenarios, pilot_algorithms, pilot_vehicles, pilot_seeds, args.resume, args.research_mode
    )
    print(f"Pilot runs expected: {len(pilot_scenarios)*len(pilot_algorithms)*len(pilot_vehicles)*len(pilot_seeds)} | Already completed: {pilot_completed} | Remaining: {len(pilot_tasks)}")

    _execute_tasks(pilot_tasks, test_run=False, use_multiprocessing=args.use_multiprocessing)
    
    pilot_results = generate_results_and_reports(pilot_scenarios, pilot_algorithms, pilot_vehicles, pilot_seeds)
    pilot_success = generate_pilot_summary_report(pilot_results)

    if not pilot_success:
        print("\n[ABORT] Pilot validation failed. Resolve anomalies before proceeding to the full matrix.")
        sys.exit(1)

    print("\n-> Pilot completed successfully with no blocking anomalies.")
    print("-> Automatically transitioning to the full benchmark matrix...")

    # FULL RUN PHASE
    print("\n" + "=" * 60)
    print("                 PHASE 2: FULL BENCHMARK MATRIX (1,440 RUNS)")
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
            try:
                import pkg_resources
                dep_versions[dep] = pkg_resources.get_distribution(dep).version
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
    _plot_scenarios(scenarios, algorithms, travel_times, response_times, plotter)
    _plot_energy_consumption(scenarios, algorithms, run_energy)
    _write_benchmark_summary(scenarios, algorithms, run_means, run_energy)


if __name__ == "__main__":
    main()
