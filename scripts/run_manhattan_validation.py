#!/usr/bin/env python3
"""Small-scale validation experiment script for Manhattan SUMO-TraCI integration."""

import os
import pathlib
import sys

# Add project root to path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from src.evaluation.plot_generator import PlotGenerator
from src.evaluation.result_exporter import ResultExporter
from src.evaluation.sumo_executor import SumoScenarioExecutor
from src.routing.dijkstra import DijkstraRouter
from src.utils.config import load_scenario_config

VALIDATION_VEHICLES = 15
VALIDATION_STEPS = 400


def run_validation_experiment(config_path: str) -> None:
    """Runs a 400-second, 15-vehicle validation experiment using DijkstraRouter.

    Args:
        config_path: Path to the YAML scenario configuration file.
    """
    print(f"[{config_path}] Loading scenario configuration for validation...")
    scenario_cfg = load_scenario_config(config_path)

    # Override simulation steps for validation milestone
    scenario_cfg.simulation.max_steps = VALIDATION_STEPS
    print(f"-> Overrode simulation steps to: {VALIDATION_STEPS} seconds.")

    # Initialize DijkstraRouter and SumoScenarioExecutor
    router = DijkstraRouter()
    executor = SumoScenarioExecutor(
        scenario_config=scenario_cfg,
        router=router,
        reroute_threshold_soc=0.20,
        target_charge_soc=1.00,
        traffic_seed=scenario_cfg.simulation.seed,
    )

    # Generate 15 vehicles
    print(f"-> Generating {VALIDATION_VEHICLES} random EV vehicles on the network...")
    executor.generate_random_traffic(num_vehicles=VALIDATION_VEHICLES)
    print(f"-> Vehicles successfully added to registry: {len(executor.vehicles)}")

    # Execute simulation
    print("-> Starting SUMO-TraCI simulation execution...")
    metrics_collector = executor.execute()
    metrics = metrics_collector.metrics
    print("-> Simulation execution completed successfully.")

    # Export results
    output_dir = scenario_cfg.simulation.output_directory or "outputs"
    print(f"-> Exporting metrics and plots to directory: '{output_dir}'")
    exporter = ResultExporter(output_dir)
    json_path = exporter.export_to_json(metrics, "validation_metrics.json")
    csv_path = exporter.export_to_csv([metrics], "validation_summary.csv")

    plotter = PlotGenerator(output_dir)
    # Generate CDF plot
    travel_times = list(metrics.vehicle_travel_times.values())
    plot_paths = plotter.generate_travel_time_cdf(
        alg_travel_times={router.__class__.__name__: travel_times},
        name="validation_travel_time_cdf",
    )

    # Print Validation Diagnostic Summary
    print("\n" + "=" * 60)
    print("           MANHATTAN VALIDATION EXPERIMENT SUMMARY")
    print("=" * 60)
    print(f"Total Vehicles Spawned: {len(executor.vehicles)}")
    print(f"Completed Journeys:     {len(metrics.vehicle_travel_times)}")
    print(f"Stranded Vehicles:      {metrics.stranded_vehicle_count}")
    print(f"Charging Diverts:       {metrics.total_charging_events}")
    
    if travel_times:
        avg_tt = sum(travel_times) / len(travel_times)
        print(f"Average Travel Time:    {avg_tt:.2f} seconds")
    else:
        print("Average Travel Time:    N/A (No vehicles completed journey yet)")
        
    avg_soc = sum(v.soc for v in executor.vehicles.values()) / len(executor.vehicles)
    print(f"Average Final SoC:      {avg_soc * 100:.2f}%")
    print("-" * 60)
    print(f"JSON Export:            {json_path}")
    print(f"CSV Export:             {csv_path}")
    print(f"Plot Export (CDF):      {plot_paths[0] if plot_paths else 'N/A'}")
    print("=" * 60)

    # Verify files exist on disk
    assert os.path.exists(json_path), "JSON metrics file missing!"
    assert os.path.exists(csv_path), "CSV summary file missing!"
    print("Verification: Export files successfully validated on disk.")


if __name__ == "__main__":
    default_config = "configs/manhattan_sample.yaml"
    if len(sys.argv) > 1:
        default_config = sys.argv[1]

    try:
        run_validation_experiment(default_config)
    except Exception as exc:
        print(f"\n[ERROR] Validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
