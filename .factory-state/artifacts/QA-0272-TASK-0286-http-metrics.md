# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0272
- Task ID: TASK-0286
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- One counter increment and one histogram record per request with the route template, never the raw path or query: pass (`test_http_requests_by_route_template`, `test_studio_app_labels_routes_through_its_middleware`).
- A 500 counts under `5xx`; streaming and WebSocket routes work: pass.
- Metrics off: the middleware passes through: pass (`test_http_middleware_passes_through_when_metrics_are_off`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_metrics.py tests/test_model_fallback.py tests/test_telemetry.py tests/test_deferred.py tests/test_readiness.py tests/test_layers.py tests/test_api_envelope.py`.
- Full backend suite and frontend locale tests (see the PR), `factory validate --only hygiene`.

## QA Decision

Pass.
