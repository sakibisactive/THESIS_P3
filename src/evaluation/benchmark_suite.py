"""Benchmark suite for comparison of standalone and E3-Hybrid routers."""

from typing import Any

from src.evaluation.experiment_runner import ExperimentRunner
from src.evaluation.metrics_collector import SimulationRunMetrics
from src.routing.router import Router
from src.utils.config import (
    BatteryConfig,
    CommunicationConfig,
    ScenarioConfig,
    SimulationConfig,
)


class BenchmarkSuite:
    """Standardizes routing algorithm benchmarking across predefined scenarios."""

    def __init__(self, output_dir: str, seeds: list[int] | None = None) -> None:
        """Initializes the suite.

        Args:
            output_dir: Root location to write benchmark charts/metrics.
            seeds: Target seed list (default: [42, 43, 44]).
        """
        self.output_dir = output_dir
        self.seeds = seeds or [42, 43, 44]

    def create_default_benchmark_scenario(self, net_file_path: str) -> ScenarioConfig:
        """Helper to build a standard, repeatable evaluation configuration.

        Args:
            net_file_path: Path to the target network configuration.

        Returns:
            ScenarioConfig: Default testing scenario configuration parameters.
        """
        sim_cfg = SimulationConfig(
            dt=1.0, max_steps=200, mode="standalone", network_file_path=net_file_path
        )

        bat_cfg = BatteryConfig(
            capacity_kwh=50.0,
            mass_kg=1500.0,
            efficiency=0.9,
            drag_coeff=0.25,
            frontal_area=2.2,
            rolling_res_coeff=0.01,
            regen_efficiency=0.7,
        )

        comm_cfg = CommunicationConfig(
            v2v_range_m=300.0,
            v2i_range_m=500.0,
            base_packet_loss_rate=0.05,
            base_latency_s=0.002,
            latency_jitter_s=0.001,
        )

        return ScenarioConfig(
            name="default_benchmark",
            simulation=sim_cfg,
            battery=bat_cfg,
            communication=comm_cfg,
            charging_stations=[],
            emergencies=[],
            infrastructure_failures=[],
            ambulance_dispatches=[],
            road_closures=[],
        )

    def run_benchmark(
        self,
        algorithms: list[tuple[type[Router], dict[str, Any]]],
        scenario: ScenarioConfig,
    ) -> list[SimulationRunMetrics]:
        """Runs the benchmark comparison across all algorithms and seeds.

        Args:
            algorithms: List of tuples containing (RouterClass, constructor kwargs).
            scenario: Target ScenarioConfig.

        Returns:
            list[SimulationRunMetrics]: Run-level metrics.
        """
        runner = ExperimentRunner(
            algorithms=algorithms,
            scenarios=[scenario],
            seeds=self.seeds,
            use_multiprocessing=False,  # Sequential for deterministic safety during benchmarking
        )
        return runner.run()
