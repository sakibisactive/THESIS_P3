"""Advanced multi-objective analysis and scientific evaluation metrics."""

import numpy as np
from typing import Any

def perform_pareto_dominance(
    results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Computes Pareto dominance and identifies non-dominated algorithms.
    
    A run is defined by (scenario, vehicles, seed).
    Objectives to minimize:
      - Mean Travel Time (T)
      - Total Energy Consumption (E)
      - Stranded Count + Ambulance response time / emergency risk (S)
    """
    # Group results by scenario, vehicles, seed
    runs: dict[tuple[str, int, int], dict[str, dict[str, float]]] = {}
    for r in results:
        scen = r["scenario_name"]
        veh = r["vehicles"]
        seed = r["seed"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        key = (scen, veh, seed)
        if key not in runs:
            runs[key] = {}
            
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())
        avg_tt = float(np.mean(times)) if times else 0.0
        
        energy_dict = r.get("vehicle_energy_consumed", {})
        total_energy = float(sum(energy_dict.values())) if energy_dict else 0.0
        
        stranded_raw = r.get("stranded_vehicle_count")
        if stranded_raw is None:
            stranded_raw = r.get("stranded_vehicles", 0)
        if stranded_raw is None:
            stranded_raw = 0
        stranded = float(stranded_raw)
        amb_times = list(r.get("ambulance_response_times", {}).values())
        avg_amb = float(np.mean(amb_times)) if amb_times else 0.0
        
        # Combined safety/stranded metric: stranded * 1000 + avg_amb
        safety = stranded * 1000.0 + avg_amb
        
        runs[key][alg] = {
            "time": avg_tt,
            "energy": total_energy,
            "safety": safety
        }
        
    # Compute dominance matrices
    # dominance[A][B] = count of runs where A dominates B
    algs = sorted(list(set(r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for r in results)))
    dominance_count = {a: {b: 0 for b in algs} for a in algs}
    total_runs = len(runs)
    
    non_dominated_counts = {a: 0 for a in algs}
    
    for key, alg_data in runs.items():
        # Find non-dominated for this specific run
        run_non_dominated = set(alg_data.keys())
        for a in alg_data:
            for b in alg_data:
                if a == b:
                    continue
                # Check if a dominates b
                # f(a) <= f(b) for all, and < for at least one
                a_better_or_equal = (
                    alg_data[a]["time"] <= alg_data[b]["time"] and
                    alg_data[a]["energy"] <= alg_data[b]["energy"] and
                    alg_data[a]["safety"] <= alg_data[b]["safety"]
                )
                a_strictly_better = (
                    alg_data[a]["time"] < alg_data[b]["time"] or
                    alg_data[a]["energy"] < alg_data[b]["energy"] or
                    alg_data[a]["safety"] < alg_data[b]["safety"]
                )
                if a_better_or_equal and a_strictly_better:
                    dominance_count[a][b] += 1
                    if b in run_non_dominated:
                        run_non_dominated.remove(b)
                        
        for nd in run_non_dominated:
            non_dominated_counts[nd] += 1
            
    # Normalize dominance
    dominance_ratio = {
        a: {b: (dominance_count[a][b] / total_runs if total_runs > 0 else 0.0) for b in algs}
        for a in algs
    }
    
    return {
        "dominance_ratio": dominance_ratio,
        "non_dominated_percentage": {a: (non_dominated_counts[a] / total_runs if total_runs > 0 else 0.0) for a in algs},
        "total_runs": total_runs
    }

def calculate_hypervolume(
    results: list[dict[str, Any]],
    safety_margin: float = 1.10
) -> dict[str, Any]:
    """Calculates hypervolume bounded by a dynamic reference point.
    
    Reference point computed from the worst observed metrics across all algorithms
    in each scenario run, plus the safety_margin.
    """
    runs: dict[tuple[str, int, int], dict[str, dict[str, float]]] = {}
    for r in results:
        scen = r["scenario_name"]
        veh = r["vehicles"]
        seed = r["seed"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        key = (scen, veh, seed)
        if key not in runs:
            runs[key] = {}
            
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())
        avg_tt = float(np.mean(times)) if times else 0.0
        
        energy_dict = r.get("vehicle_energy_consumed", {})
        total_energy = float(sum(energy_dict.values())) if energy_dict else 0.0
        
        stranded_raw = r.get("stranded_vehicle_count")
        if stranded_raw is None:
            stranded_raw = r.get("stranded_vehicles", 0)
        if stranded_raw is None:
            stranded_raw = 0
        stranded = float(stranded_raw)
        amb_times = list(r.get("ambulance_response_times", {}).values())
        avg_amb = float(np.mean(amb_times)) if amb_times else 0.0
        safety = stranded * 1000.0 + avg_amb
        
        runs[key][alg] = {
            "time": avg_tt,
            "energy": total_energy,
            "safety": safety
        }
        
    algs = sorted(list(set(r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for r in results)))
    hv_scores = {a: [] for a in algs}
    
    for key, alg_data in runs.items():
        # Find worst objectives for reference point
        max_t = max(alg_data[a]["time"] for a in alg_data) if alg_data else 1.0
        max_e = max(alg_data[a]["energy"] for a in alg_data) if alg_data else 1.0
        max_s = max(alg_data[a]["safety"] for a in alg_data) if alg_data else 1.0
        
        # reference point
        ref_t = max_t * safety_margin if max_t > 0 else 10.0
        ref_e = max_e * safety_margin if max_e > 0 else 10.0
        ref_s = max_s * safety_margin if max_s > 0 else 10.0
        
        for a in algs:
            if a in alg_data:
                t = alg_data[a]["time"]
                e = alg_data[a]["energy"]
                s = alg_data[a]["safety"]
                
                # Hypervolume = product of differences
                vol = max(0.0, ref_t - t) * max(0.0, ref_e - e) * max(0.0, ref_s - s)
                hv_scores[a].append(vol)
                
    # Compute mean hypervolume per algorithm
    mean_hv = {a: float(np.mean(hv_scores[a])) if hv_scores[a] else 0.0 for a in algs}
    return mean_hv

def calculate_weighted_utility(
    results: list[dict[str, Any]],
    w_t: float = 0.7,
    w_e: float = 0.2,
    w_s: float = 0.1
) -> dict[str, Any]:
    """Computes normalized weighted utility score using thesis objective weights."""
    runs: dict[tuple[str, int, int], dict[str, dict[str, float]]] = {}
    for r in results:
        scen = r["scenario_name"]
        veh = r["vehicles"]
        seed = r["seed"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        key = (scen, veh, seed)
        if key not in runs:
            runs[key] = {}
            
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())
        avg_tt = float(np.mean(times)) if times else 0.0
        
        energy_dict = r.get("vehicle_energy_consumed", {})
        total_energy = float(sum(energy_dict.values())) if energy_dict else 0.0
        
        stranded_raw = r.get("stranded_vehicle_count")
        if stranded_raw is None:
            stranded_raw = r.get("stranded_vehicles", 0)
        if stranded_raw is None:
            stranded_raw = 0
        stranded = float(stranded_raw)
        amb_times = list(r.get("ambulance_response_times", {}).values())
        avg_amb = float(np.mean(amb_times)) if amb_times else 0.0
        safety = stranded * 1000.0 + avg_amb
        
        runs[key][alg] = {
            "time": avg_tt,
            "energy": total_energy,
            "safety": safety
        }
        
    algs = sorted(list(set(r["algorithm_name"].replace("Router", "").replace("E3Hybrid", "E3-Hybrid") for r in results)))
    utility_scores = {a: [] for a in algs}
    win_counts = {a: 0 for a in algs}
    
    for key, alg_data in runs.items():
        # Min-max normalization values for this run
        min_t = min(alg_data[a]["time"] for a in alg_data) if alg_data else 0.0
        max_t = max(alg_data[a]["time"] for a in alg_data) if alg_data else 1.0
        range_t = max_t - min_t
        if range_t == 0.0: range_t = 1.0
        
        min_e = min(alg_data[a]["energy"] for a in alg_data) if alg_data else 0.0
        max_e = max(alg_data[a]["energy"] for a in alg_data) if alg_data else 1.0
        range_e = max_e - min_e
        if range_e == 0.0: range_e = 1.0
        
        min_s = min(alg_data[a]["safety"] for a in alg_data) if alg_data else 0.0
        max_s = max(alg_data[a]["safety"] for a in alg_data) if alg_data else 1.0
        range_s = max_s - min_s
        if range_s == 0.0: range_s = 1.0
        
        run_utils = {}
        for a in algs:
            if a in alg_data:
                t_norm = (alg_data[a]["time"] - min_t) / range_t
                e_norm = (alg_data[a]["energy"] - min_e) / range_e
                s_norm = (alg_data[a]["safety"] - min_s) / range_s
                
                # Higher utility is better
                score = 1.0 - (w_t * t_norm + w_e * e_norm + w_s * s_norm)
                utility_scores[a].append(score)
                run_utils[a] = score
                
        if run_utils:
            best_alg = max(run_utils, key=lambda k: run_utils[k])
            win_counts[best_alg] += 1
            
    mean_utility = {a: float(np.mean(utility_scores[a])) if utility_scores[a] else 0.0 for a in algs}
    return {
        "mean_utility": mean_utility,
        "win_counts": win_counts
    }

def calculate_robustness(
    results: list[dict[str, Any]]
) -> dict[str, dict[str, dict[str, float]]]:
    """Computes mean, std dev, and coefficient of variation (CV) for travel times and energy."""
    # Group results by scenario and algorithm
    groups: dict[tuple[str, str], list[dict[str, float]]] = {}
    for r in results:
        scen = r["scenario_name"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        key = (scen, alg)
        if key not in groups:
            groups[key] = []
            
        tt_dict = r.get("vehicle_travel_times", {})
        times = list(tt_dict.values())
        avg_tt = float(np.mean(times)) if times else 0.0
        
        energy_dict = r.get("vehicle_energy_consumed", {})
        total_energy = float(sum(energy_dict.values())) if energy_dict else 0.0
        
        groups[key].append({"time": avg_tt, "energy": total_energy})
        
    robustness: dict[str, dict[str, dict[str, float]]] = {}
    for (scen, alg), data in groups.items():
        if scen not in robustness:
            robustness[scen] = {}
            
        times = [d["time"] for d in data]
        energies = [d["energy"] for d in data]
        
        mean_t = float(np.mean(times)) if times else 0.0
        std_t = float(np.std(times)) if len(times) > 1 else 0.0
        cv_t = std_t / mean_t if mean_t > 0.0 else 0.0
        
        mean_e = float(np.mean(energies)) if energies else 0.0
        std_e = float(np.std(energies)) if len(energies) > 1 else 0.0
        cv_e = std_e / mean_e if mean_e > 0.0 else 0.0
        
        robustness[scen][alg] = {
            "time_mean": mean_t,
            "time_std": std_t,
            "time_cv": cv_t,
            "energy_mean": mean_e,
            "energy_std": std_e,
            "energy_cv": cv_e
        }
        
    return robustness

def calculate_emergency_metrics(
    results: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Aggregates metrics related specifically to emergency vehicle dispatches."""
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in results:
        scen = r["scenario_name"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        if "emergency" not in scen.lower():
            continue
            
        if scen not in groups:
            groups[scen] = {}
        if alg not in groups[scen]:
            groups[scen][alg] = []
            
        amb_times = list(r.get("ambulance_response_times", {}).values())
        avg_amb = float(np.mean(amb_times)) if amb_times else 0.0
        
        success_rate = float(r.get("ambulance_success_rate", 1.0))
        corridor_time = float(r.get("emergency_corridor_activation_time", 0.0))
        corridor_count = int(r.get("emergency_corridor_activation_count", 0))
        
        groups[scen][alg].append({
            "amb_time": avg_amb,
            "success_rate": success_rate,
            "corridor_time": corridor_time,
            "corridor_count": corridor_count
        })
        
    metrics_summary: dict[str, dict[str, Any]] = {}
    for scen, algs_data in groups.items():
        metrics_summary[scen] = {}
        for alg, data in algs_data.items():
            metrics_summary[scen][alg] = {
                "avg_response_time": float(np.mean([d["amb_time"] for d in data if d["amb_time"] > 0])),
                "avg_success_rate": float(np.mean([d["success_rate"] for d in data])),
                "avg_corridor_time": float(np.mean([d["corridor_time"] for d in data])),
                "avg_corridor_count": float(np.mean([d["corridor_count"] for d in data]))
            }
    return metrics_summary

def calculate_resilience_metrics(
    results: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Calculates resilience recovery profiles: Performance Loss Area & Recovery Time."""
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in results:
        scen = r["scenario_name"]
        alg = r["algorithm_name"].replace("Router", "")
        if alg == "E3Hybrid":
            alg = "E3-Hybrid"
            
        # Only check scenarios with dynamic disruptions (road closure, failure, blackout)
        if not any(k in scen.lower() for k in ["closure", "failure", "blackout"]):
            continue
            
        if scen not in groups:
            groups[scen] = {}
        if alg not in groups[scen]:
            groups[scen][alg] = []
            
        congestion_profile = r.get("congestion_levels_over_time", [])
        if not congestion_profile:
            continue
            
        # Performance Loss Area: sum of (1.0 - speed_ratio) * dt
        # recovery time: steps from beginning of disruption (assume step 100) to recovery above 0.95
        # or pre-disruption level
        loss_area = 0.0
        recovery_step = len(congestion_profile)
        disruption_step = 100  # standard baseline start in scenario configs
        
        recovered = False
        for step, val in enumerate(congestion_profile):
            # congestion level is average speed ratio (average speed / limit)
            # value of 1.0 means free flow, < 1.0 means congestion/loss
            loss_area += max(0.0, 1.0 - val)
            
            if step > disruption_step and not recovered:
                # check if recovered back above 0.95
                if val >= 0.95:
                    recovery_step = step - disruption_step
                    recovered = True
                    
        groups[scen][alg].append({
            "loss_area": loss_area,
            "recovery_steps": recovery_step if recovered else (len(congestion_profile) - disruption_step)
        })
        
    resilience_summary: dict[str, dict[str, Any]] = {}
    for scen, algs_data in groups.items():
        resilience_summary[scen] = {}
        for alg, data in algs_data.items():
            if not data:
                continue
            resilience_summary[scen][alg] = {
                "avg_performance_loss_area": float(np.mean([d["loss_area"] for d in data])),
                "avg_recovery_steps": float(np.mean([d["recovery_steps"] for d in data]))
            }
    return resilience_summary
