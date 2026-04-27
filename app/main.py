"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import evaluator
from app.exceptions import ValidationError400
from app.graph import build_graph
from app.models import ErrorResponse, HealthEvaluationRequest
from app.observability import (
    InProgressRequestTracker,
    ReadinessCheck,
    build_liveness_payload,
    build_readiness_payload,
    configure_logging,
    extract_trace_id,
    get_metrics_content_type,
    get_metrics_payload,
    monotonic_now,
    new_request_id,
    observe_request,
    request_log_extra,
)
from app.reporting import render_health_report_html, render_health_report_page

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application readiness state and emit startup/shutdown logs."""
    app.state.started_at = monotonic_now()
    app.state.ready = True
    logger.info(
        "application_started",
        extra={"event": "application_started", "service": "dag-health-api"},
    )
    yield
    app.state.ready = False
    logger.info(
        "application_stopped",
        extra={"event": "application_stopped", "service": "dag-health-api"},
    )


app = FastAPI(title="DAG Health Evaluation API", lifespan=lifespan)


@app.middleware("http")
async def add_observability(request: Request, call_next):
    """Attach request correlation, emit structured logs, and record metrics."""
    request_id = request.headers.get("x-request-id", new_request_id())
    trace_id = extract_trace_id(request.headers.get("traceparent"))
    request.state.request_id = request_id
    request.state.trace_id = trace_id

    start_time = monotonic_now()
    client_ip = request.client.host if request.client else None

    logger.info(
        "request_started",
        extra=request_log_extra(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=0,
            duration_ms=0.0,
            client_ip=client_ip,
            trace_id=trace_id,
            event="request_started",
        ),
    )

    with InProgressRequestTracker():
        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = monotonic_now() - start_time
            duration_ms = duration_seconds * 1000
            observe_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_seconds=duration_seconds,
            )
            logger.exception(
                "request_failed",
                extra=request_log_extra(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    trace_id=trace_id,
                    event="request_failed",
                ),
            )
            raise

    duration_seconds = monotonic_now() - start_time
    duration_ms = duration_seconds * 1000
    observe_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration_seconds,
    )
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete",
        extra=request_log_extra(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            trace_id=trace_id,
            event="request_complete",
        ),
    )
    return response


@app.exception_handler(ValidationError400)
async def handle_validation_error(_: Request, exc: ValidationError400) -> JSONResponse:
    """Return domain validation errors as HTTP 400."""
    error = ErrorResponse(message="Validation failed.", errors=[exc.message])
    return JSONResponse(status_code=400, content=error.model_dump())


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return Pydantic validation errors as HTTP 400 with readable messages."""
    messages = []
    for error in exc.errors():
        location = " -> ".join(str(part) for part in error["loc"] if part != "body")
        if location:
            messages.append(f"{location}: {error['msg']}")
        else:
            messages.append(error["msg"])
    response = ErrorResponse(message="Validation failed.", errors=messages)
    return JSONResponse(status_code=400, content=response.model_dump())


@app.post("/evaluate-health")
async def evaluate_health(payload: HealthEvaluationRequest):
    """Evaluate health for the full dependency graph provided in the request."""
    graph = build_graph(payload.components, payload.dependency_pairs())
    response = await evaluator.evaluate_system_health(payload.components, graph)
    return response.model_dump()


@app.get("/health/live")
async def health_live() -> dict[str, object]:
    """Return a liveness signal showing the process is serving requests."""
    return build_liveness_payload()


@app.get("/health/ready")
async def health_ready(request: Request) -> JSONResponse:
    """Return readiness based on app startup state and observability wiring."""
    is_ready = getattr(request.app.state, "ready", True)
    checks = [
        ReadinessCheck(
            name="application_startup",
            status="pass" if is_ready else "fail",
            detail="Application startup lifecycle completed."
            if is_ready
            else "Application has not completed startup.",
        ),
        ReadinessCheck(
            name="metrics_registry",
            status="pass",
            detail="Prometheus metrics registry is initialized.",
        ),
    ]
    status_code, payload = build_readiness_payload(checks)
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus-compatible metrics for scraping or ad hoc debugging."""
    return Response(
        content=get_metrics_payload(),
        media_type=get_metrics_content_type(),
    )


@app.get("/health-report", response_class=HTMLResponse)
async def health_report_page() -> HTMLResponse:
    """Serve a browser-friendly page for submitting JSON and viewing the HTML table."""
    return HTMLResponse(content=render_health_report_page())


@app.post("/health-report/render", response_class=HTMLResponse)
async def render_health_report(payload: HealthEvaluationRequest) -> HTMLResponse:
    """Render the submitted DAG evaluation as an HTML table."""
    graph = build_graph(payload.components, payload.dependency_pairs())
    response = await evaluator.evaluate_system_health(payload.components, graph)
    return HTMLResponse(content=render_health_report_html(response))
