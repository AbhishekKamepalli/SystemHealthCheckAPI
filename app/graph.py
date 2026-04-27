"""Graph construction, validation, cycle detection, and BFS traversal."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app.exceptions import ValidationError400
from app.models import ComponentInput


@dataclass(frozen=True)
class GraphData:
    """Structured graph data derived from the request payload."""

    components_in_order: list[str]
    adjacency: dict[str, list[str]]
    reverse_adjacency: dict[str, list[str]]
    indegree: dict[str, int]


def build_graph(
    components: list[ComponentInput],
    dependencies: list[tuple[str, str]],
) -> GraphData:
    """Build graph structures and validate references."""
    component_names = [component.name for component in components]
    valid_names = set(component_names)

    adjacency = {name: [] for name in component_names}
    reverse_adjacency = {name: [] for name in component_names}
    indegree = {name: 0 for name in component_names}

    for dependent, dependency in dependencies:
        if dependent not in valid_names or dependency not in valid_names:
            raise ValidationError400(
                f"Invalid dependency reference: {dependent} -> {dependency}."
            )
        adjacency[dependent].append(dependency)
        reverse_adjacency[dependency].append(dependent)
        indegree[dependency] += 1

    graph = GraphData(
        components_in_order=component_names,
        adjacency=adjacency,
        reverse_adjacency=reverse_adjacency,
        indegree=indegree,
    )
    ensure_acyclic(graph)
    return graph


def ensure_acyclic(graph: GraphData) -> None:
    """Reject cyclic graphs using Kahn's topological algorithm."""
    indegree = dict(graph.indegree)
    queue = deque(
        name for name in graph.components_in_order if indegree[name] == 0
    )
    visited_count = 0

    while queue:
        node = queue.popleft()
        visited_count += 1
        for dependency in graph.adjacency[node]:
            indegree[dependency] -= 1
            if indegree[dependency] == 0:
                queue.append(dependency)

    if visited_count != len(graph.components_in_order):
        raise ValidationError400("Cycle detected in dependency graph. The graph must be acyclic.")


def bfs_traversal(graph: GraphData) -> list[str]:
    """Traverse the graph breadth-first from root dependents toward dependencies."""
    traversal: list[str] = []
    visited: set[str] = set()
    queue = deque(name for name in graph.components_in_order if graph.indegree[name] == 0)

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        traversal.append(node)
        for dependency in graph.adjacency[node]:
            if dependency not in visited:
                queue.append(dependency)

    for name in graph.components_in_order:
        if name not in visited:
            traversal.append(name)

    return traversal


def reverse_topological_order(graph: GraphData) -> list[str]:
    """Return nodes in an order where dependencies appear before dependents."""
    indegree = dict(graph.indegree)
    queue = deque(
        name for name in graph.components_in_order if indegree[name] == 0
    )
    topological_order: list[str] = []

    while queue:
        node = queue.popleft()
        topological_order.append(node)
        for dependency in graph.adjacency[node]:
            indegree[dependency] -= 1
            if indegree[dependency] == 0:
                queue.append(dependency)

    return list(reversed(topological_order))
