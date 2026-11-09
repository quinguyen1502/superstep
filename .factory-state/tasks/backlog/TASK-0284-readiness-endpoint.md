# Task

## Metadata

- Project: superstep
- Task ID: TASK-0284
- Title: Readiness endpoint and honest health
- Status: backlog
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
