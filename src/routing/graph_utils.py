"""Graph traversal utility functions."""


def reconstruct_path(
    origin_node_id: str,
    destination_node_id: str,
    parent: dict[str, tuple[str, str]],
) -> tuple[list[str], list[str]]:
    """Reconstructs path nodes and edges by backtracking parent pointers.

    Args:
        origin_node_id: Starting node identifier.
        destination_node_id: Ending node identifier.
        parent: Pointer map containing parent nodes and traversal edge IDs.

    Returns:
        tuple[list[str], list[str]]: Ordered path nodes and edge IDs.
    """
    path_nodes: list[str] = []
    path_edges: list[str] = []
    curr = destination_node_id
    while curr != origin_node_id:
        p_node, edge_id = parent[curr]
        path_nodes.append(curr)
        path_edges.append(edge_id)
        curr = p_node
    path_nodes.append(origin_node_id)

    path_nodes.reverse()
    path_edges.reverse()
    return path_nodes, path_edges
