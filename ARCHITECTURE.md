# DAG Health Evaluation API

## Overview

`dag-health-api` is a stateless FastAPI service that evaluates the health of system components arranged as a Directed Acyclic Graph (DAG).

Each request contains:

- a list of components
- a list of dependency edges in the form `["dependent", "dependency"]`

The API:

- checks each component's own health
- propagates dependency health through the graph
- calculates an overall system health status
- returns both structured JSON and human-readable output

Because the full graph is provided in every request, the service does not require a database or any persistent storage.

## Core Design

The implementation is intentionally small and split into three main modules:

- `app/main.py`
  - FastAPI app setup
  - routes
  - exception handlers
  - request logging middleware
- `app/models.py`
  - request and response models
  - validation rules
- `app/services.py`
  - DAG construction and validation
  - cycle detection and BFS traversal
  - async health check execution with `httpx`
  - effective health propagation
  - summary generation
  - browser-friendly HTML rendering
  - structured logging and liveness/readiness support

This keeps the project compact while still separating HTTP routing, data models, and business logic.

## Health Model

Supported statuses:

- `healthy`
- `unknown`
- `degraded`
- `unhealthy`

Severity order:

```text
unhealthy > degraded > unknown > healthy
```

Each component has:

- `own_status`
  - derived from its `health_check_url`
- `effective_status`
  - the worst status between the component and all of its dependencies

Overall system health is the worst effective status across all components.

## Request Processing

Main flow for `POST /evaluate-health`:

1. Validate request shape with Pydantic.
2. Build the DAG and validate dependency references.
3. Reject cycles.
4. Run component health checks asynchronously.
5. Evaluate effective health in dependency-first order.
6. Return:
   - `overall_status`
   - `bfs_traversal_order`
   - `summary_table`
   - `summary_table_markdown`

The API exposes BFS order for visibility, but dependency propagation uses reverse topological processing so dependencies are evaluated before dependents.

## Validation and Error Handling

Validation covers:

- non-empty component names
- unique component names
- dependency edges with exactly two values
- valid dependency references
- acyclic graphs

Error responses use a consistent shape:

```json
{
  "message": "Validation failed.",
  "errors": [
    "Invalid dependency reference: frontend -> missing-service."
  ]
}
```

## Endpoints

### API endpoints

- `POST /evaluate-health`
  - returns structured JSON health evaluation

### Browser/reporting endpoints

- `GET /health-report`
  - serves a browser page for manual input
- `POST /health-report/render`
  - returns an HTML table view of the evaluation

### Operational endpoints

- `GET /health/live`
  - liveness probe
- `GET /health/ready`
  - readiness probe

## Observability

The app includes built-in observability features:

- structured JSON logs to stdout
- request IDs for correlation
- request method, path, status code, and duration in each request log
- dedicated liveness and readiness endpoints

This design works well in Cloud Run because:

- stdout/stderr flow into Cloud Logging automatically
- Cloud Run also emits request, latency, CPU, memory, and instance metrics to Cloud Monitoring

## Assumptions and Tradeoffs

- The service is stateless and expects the full graph in every request.
- Health checks use direct HTTP status mapping and timeout handling instead of custom payload parsing or retry orchestration.
- BFS is exposed as part of the response for clarity, while effective health evaluation uses dependency-safe ordering for correctness.
- The app supports both API responses and browser reporting to cover operational and human troubleshooting use cases without adding a separate UI service.

## Testing

The test suite covers:

- graph behavior
- evaluator behavior
- API validation and responses
- observability helpers
- liveness/readiness endpoints

This keeps the core logic and operational behavior verifiable without depending on external services.

What is not covered by automated tests:

- live external health-check integrations
- Docker execution in CI
- real GCP deployment behavior

Those areas are documented and partially validated separately, but they still require environment-level verification.

## Limitations

Current scope intentionally excludes:

- authentication
- persistence
- retries and backoff
- optional or weighted dependencies
- historical analysis
- custom health payload parsing

These can be added later without changing the overall structure of the service.

## Current Implementation vs Future Scope

Current implementation includes:

- FastAPI API endpoints
- DAG construction and validation
- async health checking
- effective health propagation
- browser reporting
- structured request logging
- liveness and readiness endpoints
- unit and API tests

Future scope could include:

- authentication
- persistence and historical trend analysis
- richer tracing export
- retry and backoff policies
- optional or weighted dependency models
