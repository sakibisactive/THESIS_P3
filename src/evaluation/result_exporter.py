"""Result exporter for saving simulation metrics to CSV and JSON formats."""

import csv
import json
import os

from src.evaluation.metrics_collector import SimulationRunMetrics


class ResultExporter:
    """Exports collected simulation metrics to storage files."""

    def __init__(self, output_dir: str) -> None:
        """Initializes the exporter.

        Args:
            output_dir: Directory where result files will be saved.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_to_csv(
        self, results: list[SimulationRunMetrics], filename: str = "summary_results.csv"
    ) -> str:
        """Exports high-level run summaries to a CSV file.

        Args:
            results: List of run metrics.
            filename: Output CSV filename.

        Returns:
            str: Path to the created CSV file.
        """
        filepath = os.path.join(self.output_dir, filename)

        # Headers mapping standard metrics
        headers = [
            "algorithm_name",
            "scenario_name",
            "seed",
            "timestamp",
            "avg_travel_time",
            "median_travel_time",
            "total_rerouting_events",
            "pdr",
            "avg_latency",
            "packet_loss",
            "stranded_vehicles",
            "total_charging_events",
            "avg_execution_time",
            "ablation_settings",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for r in results:
                travel_times = list(r.vehicle_travel_times.values())
                avg_tt = sum(travel_times) / len(travel_times) if travel_times else 0.0
                med_tt = (
                    float(sorted(travel_times)[len(travel_times) // 2])
                    if travel_times
                    else 0.0
                )

                avg_exec = (
                    sum(r.router_execution_times) / len(r.router_execution_times)
                    if r.router_execution_times
                    else 0.0
                )
                avg_lat = (
                    sum(r.message_latencies) / len(r.message_latencies)
                    if r.message_latencies
                    else 0.0
                )

                writer.writerow(
                    {
                        "algorithm_name": r.algorithm_name,
                        "scenario_name": r.scenario_name,
                        "seed": r.seed,
                        "timestamp": r.timestamp,
                        "avg_travel_time": avg_tt,
                        "median_travel_time": med_tt,
                        "total_rerouting_events": r.total_rerouting_events,
                        "pdr": r.packet_delivery_ratio,
                        "avg_latency": avg_lat,
                        "packet_loss": r.packet_loss_count,
                        "stranded_vehicles": r.stranded_vehicle_count,
                        "total_charging_events": r.total_charging_events,
                        "avg_execution_time": avg_exec,
                        "ablation_settings": json.dumps(r.ablation_settings),
                    }
                )

        return filepath

    def export_to_json(self, result: SimulationRunMetrics, filename: str) -> str:
        """Exports a single detailed run's metrics to a JSON file.

        Args:
            result: Single simulation run metrics log.
            filename: Output JSON filename.

        Returns:
            str: Path to the created JSON file.
        """
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, mode="w", encoding="utf-8") as f:
            # We dump the SimulationRunMetrics model directly using Pydantic serializer
            f.write(result.model_dump_json(indent=2))

        return filepath
