# Task

## Metadata

- Project: superstep
- Task ID: TASK-0296
- Title: Database and Redis server metrics in the observability profile
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-11
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Give operators database and Redis internals that the MVP probe gauges do not cover.

## Owner-Facing Outcome

The Grafana dashboard gains Postgres (connections by state, transactions, deadlocks, cache hit ratio, database size) and Redis (memory, clients, ops per second, evictions, keyspace) panels, plus the app's own SQLAlchemy pool usage, with alerts for connection saturation and Redis memory pressure.

## Scope

### In Scope

- MVP already emits `studio.ready.db`, `studio.ready.db.latency`, `studio.ready.redis`, `studio.ready.redis.latency` (TASK-0285); this task does not duplicate those probes.
- Recommended per DEC-0094: the collector (already `otel/opentelemetry-collector-contrib`) scrapes Postgres and Redis with its `postgresql` and `redis` receivers, so Prometheus keeps scraping only the collector. Alternative if the receivers fall short: `postgres_exporter` and `redis_exporter` containers in the `observability` profile, scraped by Prometheus.
- A read-only monitoring role for Postgres in the Compose setup (documented SQL for managed databases).
- SQLAlchemy pool gauges from the app: `studio.db.pool.in_use`, `studio.db.pool.idle`, `studio.db.pool.overflow` (no labels beyond the bounded set).
- Dashboard panels and two alert rules (Postgres connections above 80 percent of `max_connections`, Redis memory above 90 percent of `maxmemory` when set). New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Managed-database vendor dashboards.
- Changing `/api/ready` or the MVP probe gauges.

## Dependencies

- None (TASK-0291 profile merged).

## Acceptance Criteria

- `docker compose --profile observability up` shows non-empty Postgres and Redis panels against the Compose database and Redis; with Redis not configured the Redis panels show no data, not errors.
- Pool gauges appear with `STUDIO_OTEL_METRICS=1` and are no-ops without a reader.
- Monitoring credentials come from environment variables; none are committed.
- Alert rules load in Grafana provisioning without errors (CI or a scripted check).

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.
- 2026-11-10: Collector receivers `postgresql`, `sqlquery/postgres` (connections by state, cache hit ratio) and `redis` added to the metrics pipeline; credentials come from `POSTGRES_MONITOR_USER` and `POSTGRES_MONITOR_PASSWORD`. A one-shot `postgres-monitor` service creates a `pg_monitor` role when a password is set.
- 2026-11-10: App pool gauges `studio.db.pool.in_use`, `studio.db.pool.idle`, `studio.db.pool.overflow`. Dashboard panels in the Database and Redis row; alerts Postgres connections near limit (80%) and Redis memory pressure (90%, only with `maxmemory`). Handbook en and vi, including the monitor role SQL for a managed database.
- 2026-11-10: Deviation: per-state connections and cache ratio use the `sqlquery` receiver; the receivers were not run against live services in this environment.
- 2026-11-10: Review REV-0281 and QA-0281. Moved to review.
- 2026-11-11: Owner approved merging the Phase 2 stack. Moved to done on PR #356.

## Handoff Notes

- Use branch `factory/task-0296-db-redis-metrics` from `develop` when implementation begins.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0281-TASK-0296-db-redis-metrics.md`
- QA: `.factory-state/artifacts/QA-0281-TASK-0296-db-redis-metrics.md`
