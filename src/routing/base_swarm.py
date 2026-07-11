"""Base definitions for Iterative Swarm Engines.

To support the E3-Hybrid architecture via composition rather than tight coupling,
the baseline swarm algorithms (ACO, BCO, PSO) expose an iterative execution interface.
This allows a master orchestrator (the Hybrid router) to step through the algorithms
one iteration at a time, facilitating the exchange of information across the Blackboard
without accessing private implementation methods.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from src.routing.routing_context import RoutingContext


@dataclass
class SwarmIterationResult:
    """The outcome of a single execution iteration of a swarm engine."""

    # Valid paths discovered during this iteration
    path_nodes: list[list[str]] = field(default_factory=list)
    path_edges: list[list[str]] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)

    # Performance tracking
    nodes_expanded: int = 0
    custom_metrics: dict[str, float] = field(default_factory=dict)


@runtime_checkable
class IterativeSwarmEngine(Protocol):
    """Protocol defining the public interface for hybrid-compatible swarms."""

    def initialize_search(
        self, origin: str, dest: str, context: RoutingContext
    ) -> None:
        """Initializes per-query state before iterations begin."""
        ...

    def execute_iteration(
        self, origin: str, dest: str, context: RoutingContext
    ) -> SwarmIterationResult:
        """Executes one single iteration of the underlying swarm algorithm.

        Returns all valid paths discovered during the step.
        """
        ...

    def inject_global_best(
        self, path_nodes: list[str], path_edges: list[str], cost: float
    ) -> None:
        """Injects a globally discovered best path into the engine.

        Depending on the engine, this may:
        - ACO: Apply global pheromone deposit.
        - BCO: Seed the recruiter bee pool.
        - PSO: Act as the social attractor (G_best) for particle velocity updates.
        """
        ...

    def get_pheromone_matrix(self) -> dict[str, float] | None:
        """Returns the normalized pheromone matrix if the engine supports it.

        Returns None for engines that do not naturally use pheromones (e.g., BCO, PSO).
        """
        ...

    def inject_pheromone_matrix(self, matrix: dict[str, float]) -> None:
        """Injects a pheromone matrix into the engine.

        For PSO, this can be used to bias particle initialization.
        """
        ...
