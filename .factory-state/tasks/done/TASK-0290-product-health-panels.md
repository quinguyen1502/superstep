# Task

## Metadata

- Project: superstep
- Task ID: TASK-0290
- Title: Product health counts: approvals, webhooks, schedules
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-14
- Requirement IDs: REQ-0094
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: S

## Objective

Show cheap product SLO counts on the Usage page and export them as gauges for alerts.

## Scope

### In Scope

- Extend the usage API (or a sibling `GET /api/admin/usage/health`) with: waiting human approvals (count, oldest age), approvals expired in the window, webhook deliveries `failed` in the window and currently `retrying`, overdue schedules (`enabled` and `next_run` older than a grace period), schedules disabled by the scheduler with `note`.
- Product health block on the Usage section with en/vi strings.
- Worker-side observable gauges `studio.approvals.waiting`, `studio.approvals.oldest_age`, `studio.webhooks.failed`, `studio.webhooks.retrying`, `studio.schedules.overdue`, `studio.schedules.disabled`, refreshed on an interval with bounded queries.

### Out Of Scope

- Channel refusal codes (phase 2, see DES-0006); chat thumbs-down (phase 4).

## Dependencies

- TASK-0289 and TASK-0285 merged.

## Acceptance Criteria

- Seeded approvals, deliveries and schedules give exact counts in API tests; gauges report the same values.
- A schedule disabled because of an unknown time zone appears with its note.
- Queries use existing indexes or add one in a migration; no full scan of `runs.events`.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
- 2026-11-09: `GET /api/admin/usage/health` (`users.manage`, same `window`): waiting approvals and the oldest wait age, approvals expired in the window, webhook deliveries failed in the window and currently retrying, overdue schedules (enabled and `next_run` more than 5 minutes ago) and schedules disabled with a note (listed with the note). Product health block on the Usage section with en/vi strings.
- 2026-11-09: Worker gauges `studio.approvals.waiting`, `studio.approvals.oldest_age`, `studio.webhooks.failed`, `studio.webhooks.retrying`, `studio.schedules.overdue`, `studio.schedules.disabled`, read through `UsageService.gauges()` and cached for 30 seconds. They are registered only in processes that run a worker (the standalone worker, or the API with the embedded worker).
- 2026-11-09: Deviation: the `studio.webhooks.failed` gauge counts deliveries that failed in the last hour, because a gauge has no window parameter.
- 2026-11-09: Tests: `test_health_counts_are_exact` seeds approvals, deliveries and schedules (including one disabled with an unknown time zone note) and checks the API counts and that the gauges report the same values. Queries use the new indexes; no `runs.events` scan.
- 2026-11-09: Review REV-0276 and QA-0276. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0276-TASK-0290-product-health-panels.md`
- QA: `.factory-state/artifacts/QA-0276-TASK-0290-product-health-panels.md`

## Integration

- Delivered in the bundled implementation merged into develop via PR #351 at `73dbf52d`. The lifecycle was reconciled on 2026-11-14.
