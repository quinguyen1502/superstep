# Task

## Metadata

- Project: superstep
- Task ID: TASK-0285
- Title: OTel metrics surface with queue, worker and process gauges
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-14
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
- 2026-11-09: Branch `factory/task-0285-otel-metrics` stacked on `factory/task-0284-readiness-tzdata`; one PR with TASK-0286 and TASK-0287.
- 2026-11-09: `services/telemetry.py` gained `labels` (allowed set `LABELS`; anything else, such as a user or run id, is dropped), `watch(probes, worker)` with observable gauges `studio.ready.db`, `studio.ready.db.latency`, `studio.ready.redis`, `studio.ready.redis.latency`, `studio.queue.depth` (`state`), `studio.queue.oldest_age`, `studio.worker.heartbeat_age`, `studio.worker.busy`, `studio.worker.capacity` (only where a worker runs), `studio.run_bus.in_memory`, `studio.process.rss` and the observable counter `studio.process.cpu_time`; counters `studio.jobs.reaped` and `studio.jobs.recovered`. One probe snapshot (5 s cache) feeds all gauges of a collection; callbacks run on the exporter thread. The resource gets a random `service.instance.id` so API and worker series stay apart. Run metrics gained `workflow_id`. Gauges are registered in the API lifespan and in `python -m app.worker`. `STUDIO_OTEL_METRICS` stays opt-in; with it off the metrics SDK is not imported (subprocess test).
- 2026-11-09: Deviation: `studio.run_bus.in_memory` is 1 whenever the bus is in-memory; production is not a label. `/api/ready` reports `in_memory_in_production` for the production case, and the alert rule is documented as a production alert.
- 2026-11-09: Full backend suite: 1604 passed, 30 skipped. Frontend locale tests passed. `factory validate --only hygiene` passed.
- 2026-11-09: Review REV-0271 and QA-0271. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0271-TASK-0285-otel-metrics-surface.md`
- QA: `.factory-state/artifacts/QA-0271-TASK-0285-otel-metrics-surface.md`

## Integration

- Merged into develop via PR #350 at `f4f407a8`. The lifecycle was reconciled on 2026-11-14.
