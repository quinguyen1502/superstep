# Task

## Metadata

- Project: superstep
- Task ID: TASK-0284
- Title: Readiness endpoint and honest health
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: M

## Objective

Add `GET /api/ready` beside `/api/health` that really checks the database, Redis, the queue and the worker, and document `/api/health` as liveness.

## Scope

### In Scope

- Shared probe functions (new module under `backend/app/services/`) returning status and latency: database `SELECT 1` with a short timeout; Redis ping when `REDIS_URL` is set; queue depth of `studio:run-jobs`, `studio:run-jobs:delayed` and the processing lists; oldest queued run age from `runs` (status `queued`); worker heartbeat age.
- Worker heartbeat: each worker loop writes a TTL key (Redis) or in-process timestamp (in-memory queue) with its busy slots and `STUDIO_WORKER_CONCURRENCY`.
- `GET /api/ready` in `api/routes/meta.py`: no auth, 200 or 503 per DEC-0095, body with per-component `ok`, latency, counts, `run_bus` kind and `in_memory_in_production`; no secrets, URLs or hostnames.
- `/api/health` unchanged (fields and 200), with a docstring stating it is liveness only.
- `.env.example` note and a short handbook paragraph (en, vi) so the change is documented in the same PR.

### Out Of Scope

- Metrics export (TASK-0285); changing deploy template health check paths; failing readiness on queue backlog.

## Dependencies

- Owner acceptance of REQ-0094 and DEC-0095.

## Acceptance Criteria

- Database down gives 503 from `/api/ready` within the probe timeout while `/api/health` still answers 200.
- Redis configured and down gives 503; Redis unset reports the in-memory bus and does not fail.
- Queue depth, delayed, processing and oldest queued age match the Redis and database state in tests (fake Redis).
- Worker heartbeat age is reported and becomes stale when the worker stops.
- No secret, URL or host appears in either response.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
- 2026-11-09: Owner accepted REQ-0094, DEC-0094 and DEC-0095 (pt275u). Branch `factory/task-0284-readiness-tzdata` from the plan commit `dfb3177b`, shipped together with TASK-0293.
- 2026-11-09: Shared probes in a new services module (database `SELECT 1`, Redis ping when configured, queue depth, oldest queued run, worker heartbeats), each on a small thread pool with a 2 s timeout. Job queues gained `depth`, `heartbeat` and `heartbeats`; the worker writes a heartbeat every 5 s with busy slots and capacity (Redis key with a TTL of three reap intervals, at least 60 s; in-process for the in-memory queue). `GET /api/ready` returns the report, or 503 `SERVICE_NOT_READY` with the report in `details` (new catalog code, docs and en/vi locale entries). `/api/health` unchanged apart from a liveness docstring. Handbook en/vi health section, API route list and `.env.example` note. Deploy templates untouched.
- 2026-11-09: Deviation: the 503 body is the standard error envelope (`SERVICE_NOT_READY`, report in `details`) rather than a success envelope with a 503 status, so the envelope contract stays intact. No new environment variable: the probe timeout is a constant (2 s).
- 2026-11-09: Full backend suite: 1590 passed, 30 skipped. `factory validate --only hygiene` passed. Unreleased changelog entries for readiness and `tzdata`.
- 2026-11-09: Review REV-0269 and QA-0269. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0269-TASK-0284-readiness-endpoint.md`
- QA: `.factory-state/artifacts/QA-0269-TASK-0284-readiness-endpoint.md`
