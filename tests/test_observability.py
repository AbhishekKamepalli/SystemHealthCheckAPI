import json
import logging

from app.services import (
    JsonLogFormatter,
    build_liveness_payload,
    build_readiness_payload,
    request_log_extra,
)


def test_json_log_formatter_outputs_structured_json():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="dag_health_api",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request_complete",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.path = "/health/live"

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "request_complete"
    assert payload["severity"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["path"] == "/health/live"


def test_build_readiness_payload_returns_ready_status():
    status_code, payload = build_readiness_payload([])

    assert status_code == 200
    assert payload["status"] == "ready"


def test_liveness_payload_contains_service_metadata():
    payload = build_liveness_payload()

    assert payload["service"] == "dag-health-api"
    assert payload["status"] == "ok"


def test_request_log_extra_contains_operational_fields():
    payload = request_log_extra(
        request_id="req-123",
        method="GET",
        path="/evaluate-health",
        status_code=200,
        duration_ms=12.345,
        client_ip="127.0.0.1",
    )

    assert payload["request_id"] == "req-123"
    assert payload["event"] == "http_request"
    assert payload["duration_ms"] == 12.35
