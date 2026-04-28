"""Core application services for graph evaluation, reporting, and logging."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any
from uuid import uuid4

import httpx

from app.models import (
    ComponentInput,
    HealthEvaluationResponse,
    HealthStatus,
    SummaryRow,
)

DEFAULT_TIMEOUT_SECONDS = 2.0
LOGGER_NAME = "dag_health_api"
STATUS_RANK: dict[HealthStatus, int] = {
    "healthy": 0,
    "unknown": 1,
    "degraded": 2,
    "unhealthy": 3,
}
SAMPLE_PAYLOAD = """{
  "components": [
    {
      "name": "frontend",
      "health_check_url": "http://frontend/health"
    },
    {
      "name": "api-service",
      "health_check_url": "http://api-service/health"
    },
    {
      "name": "database",
      "health_check_url": "http://database/health"
    }
  ],
  "dependencies": [
    ["frontend", "api-service"],
    ["api-service", "database"]
  ]
}"""


class ValidationError400(Exception):
    """Raised when request data fails domain-specific validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class GraphData:
    """Structured graph data derived from the request payload."""

    components_in_order: list[str]
    adjacency: dict[str, list[str]]
    reverse_adjacency: dict[str, list[str]]
    indegree: dict[str, int]


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of checking a component's own health."""

    component: str
    status: HealthStatus
    reason: str


@dataclass(frozen=True)
class EffectiveHealth:
    """Effective health derived from a component and its dependencies."""

    status: HealthStatus
    reason: str


@dataclass(frozen=True)
class ReadinessCheck:
    """Represents a readiness signal returned by the readiness endpoint."""

    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""
        return {"name": self.name, "status": self.status, "detail": self.detail}


class JsonLogFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }
        }
        payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> logging.Logger:
    """Configure application logging to emit structured JSON to stdout."""
    log_level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        logger.setLevel(log_level)
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    logger.setLevel(log_level)
    logger.handlers = [handler]
    logger.propagate = False

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    logger.info(
        "logging_configured",
        extra={
            "event": "logging_configured",
            "service": get_service_name(),
            "environment": get_environment(),
        },
    )
    return logger


def get_service_name() -> str:
    """Return the logical service name used in logs and health responses."""
    return os.getenv("APP_SERVICE_NAME", "dag-health-api")


def get_environment() -> str:
    """Return the current application environment."""
    return os.getenv("APP_ENV", "local")


def get_app_version() -> str:
    """Return the app version for health responses."""
    return os.getenv("APP_VERSION", "0.1.0")


def new_request_id() -> str:
    """Generate a unique request identifier for log correlation."""
    return str(uuid4())


def monotonic_now() -> float:
    """Wrapper used to simplify request timing and testing."""
    return time.perf_counter()


def request_log_extra(
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str | None,
) -> dict[str, Any]:
    """Build structured fields for HTTP request logs."""
    return {
        "event": "http_request",
        "service": get_service_name(),
        "environment": get_environment(),
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": client_ip,
    }


def build_liveness_payload() -> dict[str, Any]:
    """Build the liveness response payload."""
    return {
        "service": get_service_name(),
        "status": "ok",
        "environment": get_environment(),
        "version": get_app_version(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def build_readiness_payload(checks: list[ReadinessCheck]) -> tuple[int, dict[str, Any]]:
    """Build the readiness response and status code."""
    is_ready = all(check.status == "pass" for check in checks)
    payload = {
        "service": get_service_name(),
        "status": "ready" if is_ready else "not_ready",
        "environment": get_environment(),
        "version": get_app_version(),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "checks": [check.as_dict() for check in checks],
    }
    return (200 if is_ready else 503, payload)


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
    queue = deque(name for name in graph.components_in_order if indegree[name] == 0)
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
    queue = deque(name for name in graph.components_in_order if indegree[name] == 0)
    topological_order: list[str] = []

    while queue:
        node = queue.popleft()
        topological_order.append(node)
        for dependency in graph.adjacency[node]:
            indegree[dependency] -= 1
            if indegree[dependency] == 0:
                queue.append(dependency)

    return list(reversed(topological_order))


async def check_component_health(
    component: ComponentInput,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> HealthCheckResult:
    """Evaluate a single component's own health from its health check URL."""
    if not component.health_check_url:
        return HealthCheckResult(
            component=component.name,
            status="unknown",
            reason="No health_check_url provided",
        )

    try:
        timeout = httpx.Timeout(timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(component.health_check_url)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
        return HealthCheckResult(
            component=component.name,
            status="unhealthy",
            reason="Component health check failed",
        )

    status_code = response.status_code
    if status_code == 200:
        return HealthCheckResult(
            component=component.name,
            status="healthy",
            reason="Component health check passed",
        )
    if status_code >= 500:
        return HealthCheckResult(
            component=component.name,
            status="unhealthy",
            reason="Component health check failed",
        )
    return HealthCheckResult(
        component=component.name,
        status="degraded",
        reason=f"Component health check returned HTTP {status_code}",
    )


async def check_all_components(
    components: list[ComponentInput],
) -> dict[str, HealthCheckResult]:
    """Check all component health endpoints concurrently."""
    results = await asyncio.gather(
        *(check_component_health(component) for component in components)
    )
    return {result.component: result for result in results}


def worst_status(*statuses: HealthStatus) -> HealthStatus:
    """Return the most severe health status."""
    return max(statuses, key=lambda status: STATUS_RANK[status])


async def evaluate_system_health(
    components: list[ComponentInput],
    graph: GraphData,
) -> HealthEvaluationResponse:
    """Evaluate component health and aggregate system status."""
    own_health_results = await check_all_components(components)
    effective_health = calculate_effective_health(graph, own_health_results)
    bfs_order = bfs_traversal(graph)
    summary_table = build_summary_table(graph, own_health_results, effective_health)
    summary_table_markdown = render_summary_table_markdown(summary_table)
    overall_status = worst_status(*(row.effective_status for row in summary_table))

    return HealthEvaluationResponse(
        overall_status=overall_status,
        bfs_traversal_order=bfs_order,
        summary_table=summary_table,
        summary_table_markdown=summary_table_markdown,
    )


def calculate_effective_health(
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


def build_summary_table(
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


def render_summary_table_markdown(summary_table: list[SummaryRow]) -> str:
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


def render_health_report_page() -> str:
    """Render the browser page used to submit JSON and view the HTML report."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Health Report Viewer</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffdf9;
      --border: #d7cbb9;
      --ink: #221d18;
      --muted: #6e665e;
      --accent: #9a4028;
      --accent-soft: #f5dfd9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top, #efe4d2 0%, var(--bg) 55%);
      color: var(--ink);
      padding: 28px;
    }}
    .layout {{
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      gap: 20px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 50px rgba(31, 21, 13, 0.08);
      overflow: hidden;
    }}
    .hero {{
      padding: 28px 30px 16px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.1;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .editor {{
      padding: 0 24px 24px;
    }}
    textarea {{
      width: 100%;
      min-height: 320px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      font: 14px/1.5 Consolas, "Courier New", monospace;
      background: #fffdfa;
      color: var(--ink);
    }}
    .actions {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 14px;
      flex-wrap: wrap;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
    }}
    .hint {{
      color: var(--muted);
      font-size: 14px;
    }}
    .error {{
      display: none;
      margin: 16px 24px 0;
      padding: 14px 16px;
      border-radius: 12px;
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid #e6bdb2;
      white-space: pre-wrap;
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
    }}
    iframe {{
      width: 100%;
      min-height: 520px;
      border: 0;
      background: white;
    }}
  </style>
</head>
<body>
  <main class="layout">
    <section class="panel">
      <div class="hero">
        <h1>Health Report Viewer</h1>
        <p>Paste your DAG request JSON and render the health summary as a browser table.</p>
      </div>
      <div id="error" class="error"></div>
      <div class="editor">
        <textarea id="payload">{escape(SAMPLE_PAYLOAD)}</textarea>
        <div class="actions">
          <button id="renderButton" type="button">Render Health Table</button>
          <span class="hint">This submits the JSON to <code>/health-report/render</code> and shows the HTML report below.</span>
        </div>
      </div>
    </section>
    <section class="panel">
      <iframe id="reportFrame" title="Health report output"></iframe>
    </section>
  </main>
  <script>
    const payloadEl = document.getElementById("payload");
    const buttonEl = document.getElementById("renderButton");
    const errorEl = document.getElementById("error");
    const frameEl = document.getElementById("reportFrame");

    async function renderReport() {{
      errorEl.style.display = "none";
      errorEl.textContent = "";

      let parsed;
      try {{
        parsed = JSON.parse(payloadEl.value);
      }} catch (error) {{
        errorEl.style.display = "block";
        errorEl.textContent = `Invalid JSON: ${{error.message}}`;
        return;
      }}

      const response = await fetch("/health-report/render", {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json"
        }},
        body: JSON.stringify(parsed)
      }});

      const responseText = await response.text();
      if (!response.ok) {{
        errorEl.style.display = "block";
        errorEl.textContent = responseText;
        return;
      }}

      frameEl.srcdoc = responseText;
    }}

    buttonEl.addEventListener("click", renderReport);
  </script>
</body>
</html>"""


def render_health_report_html(response: HealthEvaluationResponse) -> str:
    """Render a browser-friendly health report table."""
    rows = []
    for row in response.summary_table:
        dependencies = ", ".join(row.dependencies) if row.dependencies else "none"
        rows.append(
            "<tr>"
            f"<td>{escape(row.component)}</td>"
            f"<td>{escape(row.own_status)}</td>"
            f"<td>{escape(row.effective_status)}</td>"
            f"<td>{escape(dependencies)}</td>"
            f"<td>{escape(row.reason)}</td>"
            "</tr>"
        )

    bfs_order = " -> ".join(response.bfs_traversal_order)
    overall_status = escape(response.overall_status)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DAG Health Evaluation</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f1e8;
      --surface: #fffdf8;
      --ink: #1e1b16;
      --muted: #6a6257;
      --border: #d9cfbf;
      --accent: #8f3b2e;
    }}
    body {{
      margin: 0;
      padding: 32px;
      background: linear-gradient(180deg, #efe7d7 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .shell {{
      max-width: 1080px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 60px rgba(41, 31, 20, 0.08);
      overflow: hidden;
    }}
    .header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 32px;
      line-height: 1.1;
    }}
    .meta {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .status {{
      display: inline-block;
      margin-top: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: #f6ded9;
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      font-size: 12px;
    }}
    .table-wrap {{
      padding: 22px 26px 30px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 15px;
    }}
    th, td {{
      text-align: left;
      padding: 14px 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    th {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      background: #fbf6ed;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="header">
      <h1>System Health Summary</h1>
      <p class="meta"><strong>BFS Traversal:</strong> <code>{escape(bfs_order)}</code></p>
      <div class="status">Overall Status: {overall_status}</div>
    </section>
    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>Own Status</th>
            <th>Effective Status</th>
            <th>Dependencies</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>"""
