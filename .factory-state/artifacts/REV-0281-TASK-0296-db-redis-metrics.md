# Review

## Metadata

- Project: superstep
- Review ID: REV-0281
- Task ID: TASK-0296
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`deploy/observability/otel-collector.yaml` (`postgresql`, `sqlquery/postgres`, `redis` receivers), `deploy/observability/postgres-monitor.sh`, `docker-compose.yml` (`postgres-monitor` one-shot service, collector environment), `.env.example`, `backend/app/services/telemetry.py` and `backend/app/core/db.py` pool gauges, dashboard and alert rules, handbook (en and vi), `backend/tests/test_metrics.py`, `backend/tests/test_observability_stack.py`.

## Findings

### Blocking

- None.

### Non-Blocking

- The receivers were not smoke-tested against a live Compose stack: Docker, Postgres and Redis are not available in the implementation environment. Metric names were checked by validating the collector config with the matching `otelcol-contrib` binary, and every PromQL expression parses with `promtool`. The first `docker compose --profile observability up` after merge should confirm the panels fill.
- Connections by state and the cache hit ratio come from the `sqlquery` receiver, because the `postgresql` receiver has no per-state connection metric and its block metrics are not enabled in this collector version.
- The monitor role is created by a one-shot service on each `up`; with an empty `POSTGRES_MONITOR_PASSWORD` it exits without creating anything and the Postgres panels stay empty.

## Review Decision

Approved for QA.
