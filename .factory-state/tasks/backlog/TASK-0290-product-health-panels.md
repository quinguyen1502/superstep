# Task

## Metadata

- Project: superstep
- Task ID: TASK-0290
- Title: Product health counts: approvals, webhooks, schedules
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
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
