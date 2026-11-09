# Task

## Metadata

- Project: superstep
- Task ID: TASK-0285
- Title: OTel metrics surface with queue, worker and process gauges
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

Make `services/telemetry.py` the single metrics surface per DEC-0094: bounded label rules, observable gauges for queue, worker, probes and process, and a flag for the in-memory bus in production.

## Scope

### In Scope

- A small helper that enforces the allowed label set (no `user_id`, `run_id`, raw path) used by every instrument.
- Observable gauges: `studio.queue.depth` (`state`: ready, delayed, processing), `studio.queue.oldest_age`, `studio.worker.busy`, `studio.worker.capacity`, `studio.worker.heartbeat_age`, `studio.ready.db` and `studio.ready.redis` (1 ok / 0 failing) with latency gauges, `studio.run_bus.in_memory`, process CPU seconds and RSS from the standard library.
- Counters for reaped and recovered jobs (today only a log warning).
- Gauges registered in the process that owns the data (worker for slots and reap; API and worker both for probes), with short callback timeouts and no event-loop blocking.
- Keep `STUDIO_OTEL_METRICS` opt-in; keep the lazy SDK import and the no-op path; existing five run metrics unchanged except that `workflow_id` is added as a label.

### Out Of Scope

- HTTP metrics (TASK-0286), model metrics (TASK-0287), Grafana (TASK-0291), a `/metrics` route.

## Dependencies

- TASK-0284 merged (shared probes).

## Acceptance Criteria

- With an in-memory metric reader in tests, all gauges and counters appear with only allowed labels.
- With metrics off, the OTel metrics SDK is not imported (existing test pattern).
- Reaped and recovered jobs increment their counters.
- `studio.run_bus.in_memory` is 1 only with the in-memory bus.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
