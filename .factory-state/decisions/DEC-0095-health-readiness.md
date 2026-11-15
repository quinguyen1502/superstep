# Decision

- Decision ID: DEC-0095
- Project: superstep
- Status: Accepted 2026-11-09 (Asia/Saigon) by the owner (pt275u, accepting the plan), with REQ-0094; deploy templates stay on `/api/health` for now
- Created/Updated: 2026-11-09
- Related: REQ-0094, PLAN-0013, TASK-0284

## Context

`GET /api/health` returns `ok: true` unconditionally, with `database` set to the dialect name (no query), `run_bus_ok` from `bus.ping()` (always true for the in-memory bus), tracing, import and attachment storage status. `Dockerfile`, `backend/Dockerfile`, `render.yaml`, `deploy/render/*.yaml`, `.do/deploy.template.yaml` and the image CI job all probe `/api/health`. A dead database therefore never fails a health check.

## Decision

- `/api/health` is **liveness**: it answers 200 while the process serves HTTP. Its fields stay for backward compatibility. This is called out in the handbook: it does not check the database.
- `/api/ready` is **readiness**: database `SELECT 1` with latency (short timeout), Redis ping with latency when `REDIS_URL` is set, queue depth (`studio:run-jobs`, `studio:run-jobs:delayed`, processing lists), oldest queued run age from the `runs` table, worker heartbeat age (a new TTL key written by each worker loop; with the in-memory queue, the in-process worker state), `run_bus` kind and `in_memory_in_production` when the in-memory bus runs with production settings. HTTP 503 when the database fails, or Redis is configured and fails; queue and worker values are reported but do not fail readiness in the MVP (alerts cover them), so a backlog does not take the API out of rotation.
- Deploy templates keep `/api/health` in the MVP. The handbook explains when to point a platform at `/api/ready` (rolling deploys behind a load balancer) and why Docker `HEALTHCHECK` should stay on liveness (a restart does not fix a dead database).
- The readiness probes are shared functions reused by the metric gauges (TASK-0285) so both report the same numbers.
