"""Health aggregation and response construction logic."""

from __future__ import annotations

from dataclasses import dataclass

from app.graph import GraphData, bfs_traversal, reverse_topological_order
from app.health_checker import HealthCheckResult, check_all_components
from app.models import (
    ComponentInput,
    HealthEvaluationResponse,
    HealthStatus,
    SummaryRow,
)

STATUS_RANK: dict[HealthStatus, int] = {
    "healthy": 0,
    "unknown": 1,
    "degraded": 2,
    "unhealthy": 3,
}


@dataclass(frozen=True)
class EffectiveHealth:
    """Effective health derived from a component and its dependencies."""

    status: HealthStatus
    reason: str


def worst_status(*statuses: HealthStatus) -> HealthStatus:
    """Return the most severe health status."""
    return max(statuses, key=lambda status: STATUS_RANK[status])


async def evaluate_system_health(
    components: list[ComponentInput],
    graph: GraphData,
) -> HealthEvaluationResponse:
    """Evaluate component health and aggregate system status."""
    own_health_results = await check_all_components(components)
    effective_health = _calculate_effective_health(graph, own_health_results)
    bfs_order = bfs_traversal(graph)
    summary_table = _build_summary_table(graph, own_health_results, effective_health)
    summary_table_markdown = _render_summary_table_markdown(summary_table)
    overall_status = worst_status(*(row.effective_status for row in summary_table))

    return HealthEvaluationResponse(
        overall_status=overall_status,
        bfs_traversal_order=bfs_order,
        summary_table=summary_table,
        summary_table_markdown=summary_table_markdown,
    )


def _calculate_effective_health(
    graph: GraphData,
    own_health_results: dict[str, HealthCheckResult],
) -> dict[str, EffectiveHealth]:
    """Compute effective health bottom-up so dependency health propagates upward."""
    effective: dict[str, EffectiveHealth] = {}

    for component_name in reverse_topological_order(graph):
        own_result = own_health_results[component_name]
        dependency_names = graph.adjacency[component_name]

        if not dependency_names:
            effective[component_name] = EffectiveHealth(
                status=own_result.status,
                reason=own_result.reason,
            )
            continue

        worst_dependency_name = min(
            dependency_names,
            key=lambda name: (-STATUS_RANK[effective[name].status], dependency_names.index(name)),
        )
        worst_dependency_status = effective[worst_dependency_name].status
        combined_status = worst_status(own_result.status, worst_dependency_status)

        if STATUS_RANK[worst_dependency_status] > STATUS_RANK[own_result.status]:
            reason = f"Dependency {worst_dependency_name} is {worst_dependency_status}"
        else:
            reason = own_result.reason

        effective[component_name] = EffectiveHealth(status=combined_status, reason=reason)

    return effective


def _build_summary_table(
    graph: GraphData,
    own_health_results: dict[str, HealthCheckResult],
    effective_health: dict[str, EffectiveHealth],
) -> list[SummaryRow]:
    """Build the table-style response rows in dependency-first order."""
    rows: list[SummaryRow] = []
    for component_name in reverse_topological_order(graph):
        rows.append(
            SummaryRow(
                component=component_name,
                own_status=own_health_results[component_name].status,
                effective_status=effective_health[component_name].status,
                dependencies=graph.adjacency[component_name],
                reason=effective_health[component_name].reason,
            )
        )
    return rows


def _render_summary_table_markdown(summary_table: list[SummaryRow]) -> str:
    """Render summary rows as a human-readable Markdown table."""
    header = [
        "| Component | Own Status | Effective Status | Dependencies | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    body = []
    for row in summary_table:
        dependency_text = ", ".join(row.dependencies) if row.dependencies else "none"
        body.append(
            f"| {row.component} | {row.own_status} | {row.effective_status} | "
            f"{dependency_text} | {row.reason} |"
        )
    return "\n".join(header + body)
