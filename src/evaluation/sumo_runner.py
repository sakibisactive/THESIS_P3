"""SUMO experiment runner for batch execution and management."""

import copy
import multiprocessing
from typing import Any

from src.evaluation.metrics_collector import SimulationRunMetrics
from src.evaluation.sumo_executor import SumoScenarioExecutor
from src.routing.router import Router
from src.utils.config import ScenarioConfig


def _run_single_sumo_experiment_worker(
    args: tuple[ScenarioConfig, type[Router], dict[str, Any], int, float, float, int],
) -> SimulationRunMetrics:
    """Helper worker for running SUMO experiments in parallel."""
    (
        scenario_cfg,
        router_cls,
        router_init_kwargs,
        seed,
        reroute_soc,
        target_soc,
        port_offset,
    ) = args

    # Deep copy configuration to avoid cross-thread modifications
    cfg_copy = copy.deepcopy(scenario_cfg)

    # If running in parallel, allocate distinct TraCI ports
    if port_offset > 0:
        cfg_copy.simulation.traci_port += port_offset
        # Ensure we don't start GUI for background parallel jobs
        # to avoid display server crashes.
        cfg_copy.simulation.use_gui = False

    # Instantiate the router with a specific seed if supported
    kwargs = dict(router_init_kwargs)
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
    executor = SumoScenarioExecutor(
        scenario_config=cfg_copy,
        router=router_instance,
        reroute_threshold_soc=reroute_soc,
        target_charge_soc=target_soc,
        traffic_seed=seed,
    )

    # Generate traffic matching the scenario needs
    executor.generate_random_traffic(num_vehicles=15)

    # Execute simulation
    metrics_coll = executor.execute()
    return metrics_coll.metrics


class SumoExperimentRunner:
    """Orchestrates batch runs of simulation scenarios on SUMO.

    Evaluates different routers and seeds.
    """

    def __init__(
        self,
        algorithms: list[tuple[type[Router], dict[str, Any]]],
        scenarios: list[ScenarioConfig],
        seeds: list[int],
        reroute_threshold_soc: float = 0.20,
        target_charge_soc: float = 1.00,
        use_multiprocessing: bool = False,
    ) -> None:
        """Initializes the SUMO batch runner.

        Args:
            algorithms: List of tuples containing (RouterClass, kwargs).
            scenarios: List of ScenarioConfigs to evaluate.
            seeds: List of random seeds to test.
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
        """Executes all batch runs on SUMO.

        Returns:
            list[SimulationRunMetrics]: Collection of metrics logs from all runs.
        """
        tasks = []
        port_counter = 0

        for scenario_cfg in self.scenarios:
            for router_cls, router_kwargs in self.algorithms:
                for seed in self.seeds:
                    # Allocate unique port offset if using multiprocessing
                    port_offset = port_counter if self.use_multiprocessing else 0
                    port_counter += 1

                    tasks.append(
                        (
                            scenario_cfg,
                            router_cls,
                            router_kwargs,
                            seed,
                            self.reroute_threshold_soc,
                            self.target_charge_soc,
                            port_offset,
                        )
                    )

        results: list[SimulationRunMetrics] = []
        if self.use_multiprocessing and len(tasks) > 1:
            pool_size = min(multiprocessing.cpu_count(), len(tasks))
            with multiprocessing.Pool(pool_size) as pool:
                results = pool.map(_run_single_sumo_experiment_worker, tasks)
        else:
            for task in tasks:
                results.append(_run_single_sumo_experiment_worker(task))

        return results
