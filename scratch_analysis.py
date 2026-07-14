import sys
import os
import random
import time
sys.path.append("/home/shiku/THESIS")

from src.sumo_adapter.adapter import SumoAdapter
from src.routing.e3_hybrid import E3HybridRouter
from src.routing.aco import ACORouter
from src.routing.routing_context import RoutingContext
from src.utils.config import load_scenario_config
from src.core.vehicle import Vehicle, VehicleState
from src.core.battery import BatteryModel

def run_analysis():
    print("Loading network...")
    network = SumoAdapter.parse_network("data/networks/midtown_manhattan.net.xml")
    nodes = list(network.nodes.keys())
    
    cfg = load_scenario_config("configs/benchmarks/normal_traffic.yaml")
    
    # 1. Map custom objectives correctly (simulating the Pydantic bug fix)
    cfg.algorithms.objectives.w_time = 0.7
    cfg.algorithms.objectives.w_energy = 0.2
    cfg.algorithms.objectives.w_emergency = 0.1
    cfg.algorithms.objectives.w_distance = 0.0
    cfg.algorithms.objectives.w_congestion = 0.0
    
    # Let's create a test vehicle
    battery_model = BatteryModel(cfg.battery)
    vehicle = Vehicle(
        vehicle_id="test_vehicle",
        origin_node_id=nodes[0],
        destination_node_id=nodes[1],
        initial_soc=0.8,
        battery=battery_model
    )
    
    # Create 20 random queries
    rng = random.Random(42)
    queries = []
    while len(queries) < 30:
        o = rng.choice(nodes)
        d = rng.choice(nodes)
        if o != d:
            queries.append((o, d))
            
    # We will test E3-Hybrid under max_iterations = 5, 10, 15, 20
    for max_iters in [5, 10, 15, 20]:
        print(f"\n--- Testing max_iterations = {max_iters} ---")
        cfg.algorithms.e3_hybrid.max_iterations = max_iters
        hybrid = E3HybridRouter(cfg.algorithms)
        
        sources = {"ACO": 0, "BCO": 0, "PSO": 0, "None": 0}
        total_time = 0.0
        total_cost = 0.0
        total_valid = 0
        
        for o, d in queries:
            ctx = RoutingContext(network=network, vehicle=vehicle, current_time=0.0)
            # Setup cost function using scorer
            ctx.cost_function = lambda edge, veh, net, context: hybrid.scorer.score_edge(edge, veh, net, [])
            
            try:
                start = time.perf_counter()
                res = hybrid.find_route(o, d, ctx)
                elapsed = time.perf_counter() - start
                
                total_time += elapsed
                total_cost += res.total_cost
                total_valid += 1
                
                # Check metrics history
                last_metric = hybrid.metrics_history[-1]
                sources[last_metric.gbest_source] += 1
            except Exception as e:
                pass
                
        print(f"Valid Queries: {total_valid}/30")
        print(f"Average Execution Time: {total_time/total_valid:.3f}s")
        print(f"Average Path Cost: {total_cost/total_valid:.3f}")
        print(f"G_best Source Counts: {sources}")
        
    # Compare with pure ACO with max_iterations=50
    print("\n--- Comparing with Standalone ACO (max_iterations = 50) ---")
    aco_config = cfg.algorithms.aco
    aco_config.max_iterations = 50
    aco = ACORouter(aco_config, scorer=hybrid.scorer)
    
    aco_sources = 0
    aco_time = 0.0
    aco_cost = 0.0
    aco_valid = 0
    
    for o, d in queries:
        ctx = RoutingContext(network=network, vehicle=vehicle, current_time=0.0)
        ctx.cost_function = lambda edge, veh, net, context: aco.scorer.score_edge(edge, veh, net, [])
        
        try:
            start = time.perf_counter()
            res = aco.find_route(o, d, ctx)
            elapsed = time.perf_counter() - start
            
            aco_time += elapsed
            aco_cost += res.total_cost
            aco_valid += 1
        except Exception as e:
            pass
            
    print(f"Valid Queries: {aco_valid}/30")
    print(f"Average Execution Time: {aco_time/aco_valid:.3f}s")
    print(f"Average Path Cost: {aco_cost/aco_valid:.3f}")

if __name__ == "__main__":
    run_analysis()
