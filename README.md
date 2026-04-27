# DAG Health Evaluation API

Small FastAPI service that evaluates the health of a system modeled as a Directed Acyclic Graph (DAG).

## What It Does

- accepts a full system graph in each request
- checks component health asynchronously
- propagates dependency health through the DAG
- returns structured JSON and a browser-friendly report
- exposes liveness, readiness, metrics, and structured logs for operations

## Project Structure

- `app/`
  - FastAPI application code
  - graph evaluation, health checking, reporting, and observability
- `tests/`
  - unit and API tests
- `terraform/`
  - GCP infrastructure for Artifact Registry, Cloud Run, monitoring, and workflows
- `ARCHITECTURE.md`
  - application architecture and implementation notes
- `ENGINEERING_NOTES.md`
  - AI usage disclosure, validation notes, and integration/refinement summary

## Run Locally

Requirements:

- Python 3.11+

From the project root, create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -e .[dev]
```

Start the app:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open in the browser:

- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Browser health report page: [http://127.0.0.1:8000/health-report](http://127.0.0.1:8000/health-report)
- Liveness endpoint: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- Readiness endpoint: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)
- Metrics endpoint: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)

## Run Tests

```bash
python -m pytest -q
```

## Architecture Summary

The service is organized around a few focused concerns:

- graph construction and validation
- async component health checking
- dependency-aware health aggregation
- browser/report rendering
- observability and operational endpoints

The API uses BFS for traversal visibility and response output, while effective health propagation is computed in dependency-safe order so dependents reflect the worst status of their upstream services.

## Example Request

```powershell
$body = @'
{
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
}
'@

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/evaluate-health" `
  -ContentType "application/json" `
  -Body $body
```

## Notes

- `POST /evaluate-health` returns JSON.
- `GET /health-report` provides a browser page that renders the result as a human-readable table.
- The app emits structured JSON logs with request IDs and optional `traceparent` trace IDs.
- `GET /health/live` is a liveness probe.
- `GET /health/ready` is a readiness probe for platform/load-balancer checks.
- `GET /metrics` exposes Prometheus-style metrics for request count, latency, and in-flight requests.
- More detailed design notes are in `ARCHITECTURE.md`.
- Engineering process and AI-assistance notes are in `ENGINEERING_NOTES.md`.

## Assumptions and Tradeoffs

- The API is stateless, so the full graph is supplied on every request.
- Health checks use a simple timeout-based strategy with no retries or persistence.
- The app supports both structured JSON output and a browser-friendly HTML report because both machine and human consumers are useful for this service.
- Observability is built around stdout JSON logs, health probes, and Prometheus-style metrics because those fit well with container platforms such as Cloud Run.

## Current Implementation vs Future Scope

Implemented today:

- DAG validation and cycle detection
- async health checks
- dependency-aware health aggregation
- structured logging, liveness/readiness endpoints, and metrics
- browser report rendering
- unit and API tests

Not implemented yet:

- authentication and authorization
- persistence or history
- retries and backoff policies
- distributed tracing export
- optional or weighted dependencies
