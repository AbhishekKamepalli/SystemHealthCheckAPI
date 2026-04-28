# DAG Health Evaluation API

Small FastAPI service that evaluates the health of a system modeled as a Directed Acyclic Graph (DAG).

## What It Does

- accepts a full system graph in each request
- checks component health asynchronously
- propagates dependency health through the DAG
- returns structured JSON and a browser-friendly report
- exposes liveness, readiness, and structured request logs for operations

## Project Structure

- `app/`
  - FastAPI application code
  - `main.py` for routes
  - `models.py` for request/response models
  - `services.py` for graph logic, health checks, reporting, and logging helpers
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
- network access is optional for local testing, but real `health_check_url` values must be reachable from the machine running the app

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

If the app starts but `POST /evaluate-health` fails with `ModuleNotFoundError: No module named 'httpcore'`, the dependencies were only partially installed. Re-run:

```bash
python -m pip install --upgrade pip
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
- health endpoints and request logging

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
- The app emits structured JSON logs with request path, method, status code, duration, and request ID.
- `GET /health/live` is a liveness probe.
- `GET /health/ready` is a readiness probe for platform/load-balancer checks.
- sample URLs such as `http://frontend/health` are useful for shape examples, but they will return `unhealthy` locally unless those hostnames actually exist and respond
- More detailed design notes are in `ARCHITECTURE.md`.
- Engineering process and AI-assistance notes are in `ENGINEERING_NOTES.md`.

## Assumptions and Tradeoffs

- The API is stateless, so the full graph is supplied on every request.
- Health checks use a simple timeout-based strategy with no retries or persistence.
- The app supports both structured JSON output and a browser-friendly HTML report because both machine and human consumers are useful for this service.
- Logging is intentionally simple: stdout JSON logs plus health probes are enough for this service and fit well with container platforms such as Cloud Run.

## Current Implementation vs Future Scope

Implemented today:

- DAG validation and cycle detection
- async health checks
- dependency-aware health aggregation
- structured request logging and liveness/readiness endpoints
- browser report rendering
- unit and API tests

Not implemented yet:

- authentication and authorization
- persistence or history
- retries and backoff policies
- distributed tracing export
- optional or weighted dependencies
