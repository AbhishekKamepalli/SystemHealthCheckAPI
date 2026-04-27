"""Observability helpers for logging, health endpoints, and metrics."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

LOGGER_NAME = "dag_health_api"

REQUEST_COUNT = Counter(
    "dag_health_api_http_requests_total",
    "Total number of HTTP requests handled by the API.",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY_SECONDS = Histogram(
    "dag_health_api_http_request_duration_seconds",
    "Latency of HTTP requests handled by the API.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_PROGRESS_REQUESTS = Gauge(
    "dag_health_api_http_requests_in_progress",
    "Number of in-flight HTTP requests currently being served.",
)


class JsonLogFormatter(logging.Formatter):
    """Format log records as structured JSON for Cloud Logging ingestion."""

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
    """Configure structured JSON logging for the application."""
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
    """Return the logical service name used in observability payloads."""
    return os.getenv("APP_SERVICE_NAME", "dag-health-api")


def get_environment() -> str:
    """Return the current application environment."""
    return os.getenv("APP_ENV", "local")


def get_app_version() -> str:
    """Return the app version for health and troubleshooting responses."""
    return os.getenv("APP_VERSION", "0.1.0")


def get_metrics_payload() -> bytes:
    """Render metrics in Prometheus exposition format."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Return the HTTP content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


def extract_trace_id(traceparent_header: str | None) -> str | None:
    """Extract the trace ID from a W3C traceparent header when present."""
    if not traceparent_header:
        return None
    segments = traceparent_header.split("-")
    if len(segments) != 4:
        return None
    trace_id = segments[1]
    return trace_id if trace_id else None


def new_request_id() -> str:
    """Generate a unique request identifier for log correlation."""
    return str(uuid4())


@dataclass(frozen=True)
class ReadinessCheck:
    """Represents a readiness signal returned by the readiness endpoint."""

    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""
        return {"name": self.name, "status": self.status, "detail": self.detail}


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


def request_log_extra(
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str | None,
    trace_id: str | None,
    event: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build structured fields for request logs."""
    payload: dict[str, Any] = {
        "event": event,
        "service": get_service_name(),
        "environment": get_environment(),
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": client_ip,
        "trace_id": trace_id,
    }
    if extra:
        payload.update(dict(extra))
    return payload


def observe_request(*, method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record request metrics for the handled route."""
    status = str(status_code)
    REQUEST_COUNT.labels(method=method, path=path, status_code=status).inc()
    REQUEST_LATENCY_SECONDS.labels(method=method, path=path).observe(duration_seconds)


class InProgressRequestTracker:
    """Context manager for in-flight request metrics."""

    def __enter__(self) -> "InProgressRequestTracker":
        IN_PROGRESS_REQUESTS.inc()
        return self

    def __exit__(self, exc_type: Any, exc: Any, exc_tb: Any) -> None:
        IN_PROGRESS_REQUESTS.dec()


def monotonic_now() -> float:
    """Wrapper used to simplify request timing and testing."""
    return time.perf_counter()
