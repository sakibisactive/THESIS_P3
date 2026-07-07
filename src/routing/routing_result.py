"""Defines the representation of a path search query's result."""

from pydantic import BaseModel, Field


class RoutingResult(BaseModel):
    """Contains the output path, total cost, and stats of a routing query."""

    path_nodes: list[str] = Field(
        ..., description="Ordered list of Node IDs along the generated route."
    )
    path_edges: list[str] = Field(
        ..., description="Ordered list of Edge IDs along the generated route."
    )
    total_cost: float = Field(
        ..., description="The cumulative optimized cost of the calculated path."
    )
    expanded_nodes: int = Field(
        ..., description="The count of graph nodes popped during traversal."
    )
    search_time_s: float = Field(
        ..., description="The duration of search execution in seconds."
    )
