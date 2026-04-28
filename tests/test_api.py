from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_returns_table_style_summary(monkeypatch):
    from app import services

    async def fake_evaluate_system_health(components, graph):
        from app.models import HealthEvaluationResponse, SummaryRow

        return HealthEvaluationResponse(
            overall_status="unhealthy",
            bfs_traversal_order=["frontend", "api-service", "database"],
            summary_table=[
                SummaryRow(
                    component="database",
                    own_status="unhealthy",
                    effective_status="unhealthy",
                    dependencies=[],
                    reason="Component health check failed",
                )
            ],
            summary_table_markdown=(
                "| Component | Own Status | Effective Status | Dependencies | Reason |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| database | unhealthy | unhealthy | none | Component health check failed |"
            ),
        )

    monkeypatch.setattr(services, "evaluate_system_health", fake_evaluate_system_health)

    response = client.post(
        "/evaluate-health",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
                {"name": "api-service", "health_check_url": "http://api-service/health"},
                {"name": "database", "health_check_url": "http://database/health"},
            ],
            "dependencies": [["frontend", "api-service"], ["api-service", "database"]],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "unhealthy"
    assert body["bfs_traversal_order"] == ["frontend", "api-service", "database"]
    assert isinstance(body["summary_table"], list)
    assert body["summary_table"][0]["component"] == "database"
    assert "| Component | Own Status | Effective Status | Dependencies | Reason |" in body["summary_table_markdown"]
    assert "| database | unhealthy | unhealthy | none | Component health check failed |" in body["summary_table_markdown"]


def test_health_report_render_returns_html_table(monkeypatch):
    from app import services

    async def fake_evaluate_system_health(components, graph):
        from app.models import HealthEvaluationResponse, SummaryRow

        return HealthEvaluationResponse(
            overall_status="unhealthy",
            bfs_traversal_order=["frontend", "api-service", "database"],
            summary_table=[
                SummaryRow(
                    component="database",
                    own_status="unhealthy",
                    effective_status="unhealthy",
                    dependencies=[],
                    reason="Component health check failed",
                ),
                SummaryRow(
                    component="api-service",
                    own_status="healthy",
                    effective_status="unhealthy",
                    dependencies=["database"],
                    reason="Dependency database is unhealthy",
                ),
            ],
            summary_table_markdown="unused in html test",
        )

    monkeypatch.setattr(services, "evaluate_system_health", fake_evaluate_system_health)

    response = client.post(
        "/health-report/render",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
                {"name": "api-service", "health_check_url": "http://api-service/health"},
                {"name": "database", "health_check_url": "http://database/health"},
            ],
            "dependencies": [["frontend", "api-service"], ["api-service", "database"]],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<table>" in response.text
    assert "<th>Component</th>" in response.text
    assert "<td>database</td>" in response.text
    assert "<td>Component health check failed</td>" in response.text


def test_invalid_dependency_reference_returns_400():
    response = client.post(
        "/evaluate-health",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
            ],
            "dependencies": [["frontend", "missing-service"]],
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Validation failed."
    assert body["errors"] == ["Invalid dependency reference: frontend -> missing-service."]


def test_health_report_page_loads():
    response = client.get("/health-report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Health Report Viewer" in response.text
    assert "Render Health Table" in response.text


def test_liveness_endpoint_returns_ok_and_request_id():
    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "dag-health-api"
    assert body["status"] == "ok"
    assert "X-Request-ID" in response.headers


def test_readiness_endpoint_returns_ready_checks():
    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert any(check["name"] == "application_startup" for check in body["checks"])


def test_cycle_returns_400():
    response = client.post(
        "/evaluate-health",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
                {"name": "api-service", "health_check_url": "http://api-service/health"},
            ],
            "dependencies": [["frontend", "api-service"], ["api-service", "frontend"]],
        },
    )

    assert response.status_code == 400
    assert "Cycle detected" in response.json()["errors"][0]


def test_duplicate_component_names_return_400():
    response = client.post(
        "/evaluate-health",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
                {"name": "frontend", "health_check_url": "http://frontend-2/health"},
            ],
            "dependencies": [],
        },
    )

    assert response.status_code == 400
    assert any("Duplicate component names found" in message for message in response.json()["errors"])


def test_dependency_with_wrong_length_returns_400():
    response = client.post(
        "/evaluate-health",
        json={
            "components": [
                {"name": "frontend", "health_check_url": "http://frontend/health"},
                {"name": "api-service", "health_check_url": "http://api-service/health"},
            ],
            "dependencies": [["frontend"]],
        },
    )

    assert response.status_code == 400
    assert any("exactly two values" in message for message in response.json()["errors"])
