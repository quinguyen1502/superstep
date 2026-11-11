# Review

## Metadata

- Project: superstep
- Review ID: REV-0280
- Task ID: TASK-0295
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`backend/app/services/telemetry.py` (`instrumented`, `instrument`, `open_http`/`close_http`, `RunScope`, sampler, LangSmith scope filter, request links), `backend/app/api/http_spans.py`, `backend/app/main.py`, `backend/app/worker.py`, `backend/app/services/run_service.py`, `run_worker.py`, `job_queue.py`, dependency pins, `docker-compose.yml`, `deploy/observability/observability.env`, `.env.example`, configuration reference (en and vi), `backend/tests/test_spans.py`.

## Findings

### Blocking

- None.

### Non-Blocking

- SQL and Redis spans of a run are children of the run segment's root span, not of a node span: node spans are exported when a node finishes, so there is no live node span to parent them.
- Client spans with no request or run parent are dropped by the sampler (queue polling, heartbeats, schedulers), which keeps Jaeger readable; an operator who wants them would need a different sampler.
- The SQLAlchemy instrumentation's `EngineTracer` is used directly on the app engine because the instrumentor declares SQLAlchemy below 2.1 and patches `create_engine` globally (and needs greenlet for its asyncio hook).

## Review Decision

Approved for QA.
