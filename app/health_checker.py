"""Asynchronous component health check logic."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.models import ComponentInput, HealthStatus

DEFAULT_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of checking a component's own health."""

    component: str
    status: HealthStatus
    reason: str


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
    if 400 <= status_code <= 499:
        return HealthCheckResult(
            component=component.name,
            status="degraded",
            reason=f"Component health check returned HTTP {status_code}",
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
    results = await _gather_health_results(components)
    return {result.component: result for result in results}


async def _gather_health_results(
    components: list[ComponentInput],
) -> list[HealthCheckResult]:
    import asyncio

    return await asyncio.gather(
        *(check_component_health(component) for component in components)
    )
