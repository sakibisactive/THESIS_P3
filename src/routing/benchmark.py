"""Defines the routing benchmarking framework for algorithm comparison."""

from typing import Any

from pydantic import BaseModel, Field

from src.routing.router import Router
from src.routing.routing_context import RoutingContext
from src.routing.routing_metrics import RoutingMetrics


class RouteBenchmarkMetrics(BaseModel):
    """Performance metrics for a single route query execution."""

    success: bool = Field(
        ..., description="Indicates if a valid route was found."
    )
    path_nodes: list[str] = Field(
        default_factory=list, description="Nodes along the computed path."
    )
    path_edges: list[str] = Field(
        default_factory=list, description="Edges along the computed path."
    )
    total_cost: float = Field(
        default=0.0, description="The cumulative cost returned by the router."
    )
    distance_m: float = Field(
        default=0.0, description="Physical distance of path in meters."
    )
    travel_time_s: float = Field(
        default=0.0, description="Traverse time of path in seconds."
    )
    energy_kwh: float = Field(
        default=0.0, description="Energy consumed by path in kWh."
    )
    expanded_nodes: int = Field(
        default=0, description="Nodes popped during graph traversal."
    )
    search_time_s: float = Field(
        default=0.0,
        description="CPU time duration of the search query in seconds.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details in case of execution failure.",
    )


class RouterBenchmarkResult(BaseModel):
    """Aggregate benchmark metrics for a router across multiple queries."""

    router_name: str = Field(..., description="The name of the router.")
    queries: list[RouteBenchmarkMetrics] = Field(
        default_factory=list, description="Detailed metrics for each query."
    )
    total_searches: int = Field(
        default=0, description="Total number of queries executed."
    )
    successful_searches: int = Field(
        default=0, description="Number of queries that completed successfully."
    )
    avg_search_time_s: float = Field(
        default=0.0, description="Average search query duration in seconds."
    )
    total_expanded_nodes: int = Field(
        default=0, description="Total search nodes popped across all queries."
    )
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="The router's custom statistics snapshot.",
    )


class RoutingBenchmark:
    """Benchmark class to compare and evaluate multiple routing algorithms.

    Executes list of routers against a series of origin-destination queries
    and builds detailed performance reports for comparisons.
    """

    @staticmethod
    def run_benchmark(
        routers: dict[str, Router],
        od_pairs: list[tuple[str, str]],
        context: RoutingContext,
    ) -> dict[str, RouterBenchmarkResult]:
        """Runs the benchmark on the given routers and OD pairs.

        Args:
            routers: Dict mapping router names to Router instances.
            od_pairs: List of (origin_node_id, destination_node_id) tuples.
            context: RoutingContext with network and cost parameters.

        Returns:
            Dict mapping router names to RouterBenchmarkResult summary reports.
        """
        reports: dict[str, RouterBenchmarkResult] = {}

        for name, router in routers.items():
            # Reset router history
            router.reset()

            result_list = []
            successful_count = 0
            total_expanded = 0
            total_time = 0.0

            for origin, destination in od_pairs:
                try:
                    res = router.find_route(origin, destination, context)

                    dist_m = RoutingMetrics.calculate_path_distance(
                        context.network, res.path_edges
                    )
                    time_s = RoutingMetrics.calculate_travel_time(
                        context.network, res.path_edges
                    )
                    energy_kwh = RoutingMetrics.calculate_energy_consumption(
                        context.network, res.path_edges, context.vehicle
                    )

                    metrics = RouteBenchmarkMetrics(
                        success=True,
                        path_nodes=res.path_nodes,
                        path_edges=res.path_edges,
                        total_cost=res.total_cost,
                        distance_m=dist_m,
                        travel_time_s=time_s,
                        energy_kwh=energy_kwh,
                        expanded_nodes=res.expanded_nodes,
                        search_time_s=res.search_time_s,
                    )
                    successful_count += 1
                    total_expanded += res.expanded_nodes
                    total_time += res.search_time_s

                except Exception as e:
                    metrics = RouteBenchmarkMetrics(
                        success=False,
                        error_message=str(e),
                    )

                result_list.append(metrics)

            avg_time = (
                (total_time / len(od_pairs)) if len(od_pairs) > 0 else 0.0
            )

            reports[name] = RouterBenchmarkResult(
                router_name=name,
                queries=result_list,
                total_searches=len(od_pairs),
                successful_searches=successful_count,
                avg_search_time_s=avg_time,
                total_expanded_nodes=total_expanded,
                statistics=router.get_statistics(),
            )

        return reports
