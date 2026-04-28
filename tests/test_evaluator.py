import httpx
import pytest

from app.models import ComponentInput
from app.services import build_graph, check_component_health, evaluate_system_health


def make_component(name: str, url: str | None) -> ComponentInput:
    return ComponentInput(name=name, health_check_url=url)


@pytest.mark.asyncio
async def test_all_healthy_components_result_in_healthy_overall(monkeypatch):
    async def fake_get(self, url: str):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    components = [
        make_component("frontend", "http://frontend/health"),
        make_component("api-service", "http://api-service/health"),
        make_component("database", "http://database/health"),
    ]
    graph = build_graph(
        components,
        [("frontend", "api-service"), ("api-service", "database")],
    )

    result = await evaluate_system_health(components, graph)

    assert result.overall_status == "healthy"
    assert "| frontend | healthy | healthy | api-service |" in result.summary_table_markdown


@pytest.mark.asyncio
async def test_unhealthy_dependency_propagates_to_dependents(monkeypatch):
    async def fake_get(self, url: str):
        status_code = 500 if "database" in url else 200
        return httpx.Response(status_code, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    components = [
        make_component("frontend", "http://frontend/health"),
        make_component("api-service", "http://api-service/health"),
        make_component("database", "http://database/health"),
    ]
    graph = build_graph(
        components,
        [("frontend", "api-service"), ("api-service", "database")],
    )

    result = await evaluate_system_health(components, graph)
    rows = {row.component: row for row in result.summary_table}

    assert result.overall_status == "unhealthy"
    assert rows["database"].effective_status == "unhealthy"
    assert rows["api-service"].effective_status == "unhealthy"
    assert rows["frontend"].effective_status == "unhealthy"
    assert rows["api-service"].reason == "Dependency database is unhealthy"
    assert "| database | unhealthy | unhealthy | none | Component health check failed |" in result.summary_table_markdown
    assert "| api-service | healthy | unhealthy | database | Dependency database is unhealthy |" in result.summary_table_markdown


@pytest.mark.asyncio
async def test_missing_health_check_url_returns_unknown():
    component = make_component("cache", None)

    result = await check_component_health(component)

    assert result.status == "unknown"
    assert result.reason == "No health_check_url provided"


@pytest.mark.asyncio
async def test_timeout_or_connection_error_is_unhealthy(monkeypatch):
    async def fake_get(self, url: str):
        raise httpx.ConnectError("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    component = make_component("database", "http://database/health")
    result = await check_component_health(component)

    assert result.status == "unhealthy"
    assert result.reason == "Component health check failed"


@pytest.mark.asyncio
async def test_overall_status_uses_worst_effective_status(monkeypatch):
    async def fake_get(self, url: str):
        if "cache" in url:
            return httpx.Response(404, request=httpx.Request("GET", url))
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    components = [
        make_component("frontend", "http://frontend/health"),
        make_component("cache", "http://cache/health"),
    ]
    graph = build_graph(components, [])

    result = await evaluate_system_health(components, graph)

    assert result.overall_status == "degraded"
