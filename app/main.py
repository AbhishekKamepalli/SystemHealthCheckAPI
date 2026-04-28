"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.models import ErrorResponse, HealthEvaluationRequest
from app import services

logger = services.configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application readiness state and emit startup/shutdown logs."""
    app.state.started_at = services.monotonic_now()
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
async def log_requests(request: Request, call_next):
    """Log each HTTP request with status code and response time."""
    request_id = request.headers.get("x-request-id", services.new_request_id())
    request.state.request_id = request_id

    start_time = services.monotonic_now()
    client_ip = request.client.host if request.client else None

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (services.monotonic_now() - start_time) * 1000
        logger.exception(
            "request_failed",
            extra=services.request_log_extra(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                client_ip=client_ip,
            ),
        )
        raise

    duration_ms = (services.monotonic_now() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete",
        extra=services.request_log_extra(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        ),
    )
    return response


@app.exception_handler(services.ValidationError400)
async def handle_validation_error(
    _: Request, exc: services.ValidationError400
) -> JSONResponse:
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
    graph = services.build_graph(payload.components, payload.dependency_pairs())
    response = await services.evaluate_system_health(payload.components, graph)
    return response.model_dump()


@app.get("/health/live")
async def health_live() -> dict[str, object]:
    """Return a liveness signal showing the process is serving requests."""
    return services.build_liveness_payload()


@app.get("/health/ready")
async def health_ready(request: Request) -> JSONResponse:
    """Return readiness based on application startup state."""
    is_ready = getattr(request.app.state, "ready", True)
    checks = [
        services.ReadinessCheck(
            name="application_startup",
            status="pass" if is_ready else "fail",
            detail="Application startup lifecycle completed."
            if is_ready
            else "Application has not completed startup.",
        )
    ]
    status_code, payload = services.build_readiness_payload(checks)
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/health-report", response_class=HTMLResponse)
async def health_report_page() -> HTMLResponse:
    """Serve a browser-friendly page for submitting JSON and viewing the HTML table."""
    return HTMLResponse(content=services.render_health_report_page())


@app.post("/health-report/render", response_class=HTMLResponse)
async def render_health_report(payload: HealthEvaluationRequest) -> HTMLResponse:
    """Render the submitted DAG evaluation as an HTML table."""
    graph = services.build_graph(payload.components, payload.dependency_pairs())
    response = await services.evaluate_system_health(payload.components, graph)
    return HTMLResponse(content=services.render_health_report_html(response))
