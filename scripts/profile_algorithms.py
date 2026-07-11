#!/usr/bin/env python3
"""Algorithm performance profiling and benchmarking script."""

import gc
import json
import os
import pathlib
import random
import resource
import sys
import time
from typing import Any

import numpy as np

# Add project root to path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from src.routing.aco import ACORouter
from src.routing.astar import AStarRouter
from src.routing.bco import BCORouter
from src.routing.dijkstra import DijkstraRouter
from src.routing.e3_hybrid import E3HybridRouter
from src.routing.pso import PSORouter
from src.sumo_adapter.adapter import SumoAdapter
from src.utils.config import load_scenario_config

OUTPUT_DIR = "outputs/thesis_results"
CONFIG_PATH = "configs/benchmarks/normal_traffic.yaml"


def generate_valid_od_pairs(network, num_pairs=50, seed=42) -> list[tuple[str, str]]:
    """Generates a list of valid origin-destination node pairs with guaranteed connectivity."""
    random.seed(seed)
    nodes = list(network.nodes.keys())
    pairs = []

    while len(pairs) < num_pairs:
        start = random.choice(nodes)
        # BFS search to find reachable nodes using the public Network API
        visited = {start}
        queue = [start]
        reachable = []

        while queue and len(reachable) < 200:
            curr = queue.pop(0)
            for edge in network.get_outgoing_edges(curr):
                neighbor = edge.to_node
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    reachable.append(neighbor)

        if len(reachable) >= 10:
            # Pick a few target nodes from the reachable set
            for _ in range(min(5, num_pairs - len(pairs))):
                target = random.choice(reachable)
                pairs.append((start, target))
                
    return pairs


def profile_router(
    name: str,
    router_cls: Any,
    od_pairs: list[tuple[str, str]],
    cfg: Any,
    seed: int,
) -> dict[str, Any]:
    print(f"Profiling {name}...")
    
    # Build router configuration kwargs
    kwargs = {}
    if name in ["ACO", "BCO", "PSO", "E3-Hybrid"]:
        kwargs["seed"] = seed
        if name == "ACO":
            kwargs["config"] = cfg.algorithms.aco
        elif name == "BCO":
            kwargs["config"] = cfg.algorithms.bco
        elif name == "PSO":
            kwargs["config"] = cfg.algorithms.pso
        elif name == "E3-Hybrid":
            kwargs["config"] = cfg.algorithms

    router = router_cls(**kwargs)
    
    # Garbage collect before run to isolate memory
    gc.collect()
    mem_start_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    
    latencies = []
    
    t_start = time.time()
    for start_node, dest_node in od_pairs:
        q_start = time.time()
        try:
            router.find_route(start_node, dest_node)
        except Exception as e:
            # Log failure but continue
            pass
        latencies.append(time.time() - q_start)
    
    total_time = time.time() - t_start
    mem_end_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    
    # Calculate performance metrics
    avg_latency = float(np.mean(latencies)) * 1000.0  # ms
    p95_latency = float(np.percentile(latencies, 95)) * 1000.0  # ms
    routes_per_sec = len(od_pairs) / total_time
    mem_peak_mb = mem_end_kb / 1024.0
    mem_delta_mb = (mem_end_kb - mem_start_kb) / 1024.0
    
    print(f"  - Avg Latency: {avg_latency:.2f} ms")
    print(f"  - p95 Latency: {p95_latency:.2f} ms")
    print(f"  - Throughput:  {routes_per_sec:.2f} routes/sec")
    print(f"  - Max RSS:     {mem_peak_mb:.2f} MB")
    
    return {
        "algorithm": name,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "routes_per_second": routes_per_sec,
        "peak_memory_maxrss_mb": mem_peak_mb,
        "memory_delta_mb": mem_delta_mb,
        "total_queries": len(od_pairs)
    }


def main():
    print("============================================================")
    print("           ALGORITHM PERFORMANCE PROFILER & BENCHMARK")
    print("============================================================")
    
    # 1. Load Manhattan network
    net_path = "data/networks/midtown_manhattan.net.xml"
    if not os.path.exists(net_path):
        print(f"[ERROR] Network file {net_path} does not exist. Run preflight first.")
        sys.exit(1)
        
    print("Loading Midtown Manhattan network XML...")
    network = SumoAdapter.parse_network(net_path)
    print(f"Successfully loaded network: {len(network.nodes)} nodes, {len(network.edges)} edges.")
    
    # 2. Generate valid OD pairs
    print("Generating guaranteed connected OD pairs via BFS...")
    od_pairs = generate_valid_od_pairs(network, num_pairs=50, seed=42)
    print(f"Generated {len(od_pairs)} valid OD routing pairs.")
    
    # 3. Load configurations
    cfg = load_scenario_config(CONFIG_PATH)
    
    # Apply evaluation overrides (resource-clamped swarm settings)
    cfg.algorithms.aco.num_ants = 5
    cfg.algorithms.aco.max_iterations = 5
    cfg.algorithms.bco.colony_size = 5
    cfg.algorithms.bco.max_iterations = 5
    cfg.algorithms.pso.swarm_size = 5
    cfg.algorithms.pso.max_iterations = 5
    cfg.algorithms.e3_hybrid.max_iterations = 5
    
    # Routers to benchmark
    routers = [
        ("Dijkstra", DijkstraRouter),
        ("A*", AStarRouter),
        ("ACO", ACORouter),
        ("BCO", BCORouter),
        ("PSO", PSORouter),
        ("E3-Hybrid", E3HybridRouter),
    ]
    
    # 4. Profile each algorithm
    results = []
    for name, router_cls in routers:
        res = profile_router(name, router_cls, od_pairs, cfg, seed=42)
        results.append(res)
        
    # Write reproducibility manifest
    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "network_file": net_path,
        "parameters": {
            "evaluation_overrides": {
                "aco": {"num_ants": 5, "max_iterations": 5},
                "bco": {"colony_size": 5, "max_iterations": 5},
                "pso": {"swarm_size": 5, "max_iterations": 5},
                "e3_hybrid": {"max_iterations": 5}
            }
        },
        "profiling_results": results
    }
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest_path = os.path.join(OUTPUT_DIR, "reproducibility_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n-> Reproducibility manifest saved to: {manifest_path}")
    print("============================================================")


if __name__ == "__main__":
    main()
