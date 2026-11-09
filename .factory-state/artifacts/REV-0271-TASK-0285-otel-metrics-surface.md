# Review

## Metadata

- Project: superstep
- Review ID: REV-0271
- Task ID: TASK-0285
- Reviewer: Grok (advisory; owner authorised the implementation, pt275u)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: approved for QA

## Review Scope

`services/telemetry.py` label rules, observable gauges and job counters; worker telemetry wiring; gauge registration in the API lifespan and the worker entrypoint.

## Findings

### Blocking

- None.

### Non-Blocking

- Probe gauges are reported by every process (API and workers); dashboards should aggregate them with `max`. `service.instance.id` keeps the series apart.
- Labels outside `LABELS` are dropped silently rather than raising, so a coding mistake cannot fail a run; `test_labels_keep_only_the_allowed_set` and the bounded-label assertions in every metrics test catch it.
- `studio.run_bus.in_memory` does not know about production; the readiness report has `in_memory_in_production`.

## Review Decision

Approved for QA.
