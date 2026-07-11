"""Experiment runner for batch simulation execution and management."""

import multiprocessing
from typing import Any

from src.evaluation.metrics_collector import SimulationRunMetrics
from src.evaluation.scenario_executor import ScenarioExecutor
from src.routing.router import Router
from src.utils.config import ScenarioConfig


def _run_single_experiment_worker(
    args: tuple[ScenarioConfig, type[Router], dict[str, Any], int, float, float],
) -> SimulationRunMetrics:
    """Helper worker for running experiments in parallel."""
    scenario_cfg, router_cls, router_init_kwargs, seed, reroute_soc, target_soc = args

    # Instantiate the router with a specific seed if supported
    kwargs = dict(router_init_kwargs)
    if "seed" in kwargs or "config" in kwargs:
        # Check if the router class accepts seed or config
        pass

    # Try to inject seed if constructor supports it
    try:
        router_instance = router_cls(seed=seed, **kwargs)  # type: ignore[call-arg]
    except Exception:
        try:
            router_instance = router_cls(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate router {router_cls.__name__}: {e}"
            ) from e

    # Create executor
    executor = ScenarioExecutor(
        scenario_config=scenario_cfg,
        router=router_instance,
        reroute_threshold_soc=reroute_soc,
        target_charge_soc=target_soc,
        traffic_seed=seed,
    )

    # Generate traffic
    # Defaulting to 15 vehicles for standalone test evaluation
    executor.generate_random_traffic(num_vehicles=15)

    # Run
    metrics_coll = executor.execute()
    return metrics_coll.metrics


class ExperimentRunner:
    """Orchestrates batch runs of simulation scenarios over multiple algorithms and seeds."""

    def __init__(
        self,
        algorithms: list[tuple[type[Router], dict[str, Any]]],
        scenarios: list[ScenarioConfig],
        seeds: list[int],
        reroute_threshold_soc: float = 0.20,
        target_charge_soc: float = 1.00,
        use_multiprocessing: bool = False,
    ) -> None:
        """Initializes the batch runner.

        Args:
            algorithms: List of tuples containing (RouterClass, constructor kwargs dictionary).
            scenarios: List of ScenarioConfigs to evaluate.
            seeds: List of random seeds to test for statistical analysis.
            reroute_threshold_soc: Battery limit for charging trigger.
            target_charge_soc: Battery limit for charging complete.
            use_multiprocessing: True to run seeds in parallel using multiprocessing.
        """
        self.algorithms = algorithms
        self.scenarios = scenarios
        self.seeds = seeds
        self.reroute_threshold_soc = reroute_threshold_soc
        self.target_charge_soc = target_charge_soc
        self.use_multiprocessing = use_multiprocessing

    def run(self) -> list[SimulationRunMetrics]:
        """Executes all batch runs.

        Returns:
            list[SimulationRunMetrics]: Collection of metrics logs from all runs.
        """
        tasks = []
        for scenario_cfg in self.scenarios:
            for router_cls, router_kwargs in self.algorithms:
                for seed in self.seeds:
                    tasks.append(
                        (
                            scenario_cfg,
                            router_cls,
                            router_kwargs,
                            seed,
                            self.reroute_threshold_soc,
                            self.target_charge_soc,
                        )
                    )

        results: list[SimulationRunMetrics] = []
        if self.use_multiprocessing and len(tasks) > 1:
            # Run tasks in parallel
            pool_size = min(multiprocessing.cpu_count(), len(tasks))
            with multiprocessing.Pool(pool_size) as pool:
                results = pool.map(_run_single_experiment_worker, tasks)
        else:
            # Run tasks sequentially (deterministic and easy to debug)
            for task in tasks:
                results.append(_run_single_experiment_worker(task))

        return results
