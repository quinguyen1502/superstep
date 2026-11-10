# Task

## Metadata

- Project: superstep
- Task ID: TASK-0304
- Title: Channel refusal codes on the Usage page
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: S

## Objective

Show why chat channel messages were refused, which PLAN-0013 deferred.

## Owner-Facing Outcome

The Product health block on Settings, Usage lists chat trigger messages refused in the window grouped by reason (for example not allowed, rate limited, trigger disabled), and Grafana can alert on a spike.

## Scope

### In Scope

- Verified on `develop` 6047c732: `chat_messages` has `status` (queued, checking, started, refused), `code` and `created`, and indexes only on (`channel_id`, `key`), `trigger_id` and `run_id`.
- Alembic migration adding an index on (`status`, `created`) to `chat_messages`.
- `UsageService` health gains `channels`: refused count by `code` and by platform `kind` in the window, plus started count for a refusal share; codes shown with their catalog message in en and vi.
- Gauge `studio.chat.refused` (labels `code`, `kind`) in the product gauges next to the TASK-0290 ones; a warning alert rule. New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Approval callback refusals beyond what the approval audit log already exposes (follow-up if the owner wants it).

## Dependencies

- None (TASK-0290 merged).

## Acceptance Criteria

- Seeded refused messages with two codes show as two rows with counts; started messages are not counted as refusals.
- The query uses the new index (checked with an explain test on SQLite or documented on Postgres).
- Migration upgrades and downgrades; en/vi parity passes.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.
- 2026-11-10: Chat trigger refusals by code and platform on the Usage page health block and gauge `studio.chat.refused`; Channel refusals alert (above 20 in the last hour for 10 minutes); index `ix_chat_messages_status_created`.
- 2026-11-10: Deviation: a separate migration for the index.
- 2026-11-10: Review REV-0289 and QA-0289. Moved to review.

## Handoff Notes

- Use branch `factory/task-0304-channel-refusal-codes` from `develop` when implementation begins.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0289-TASK-0304-channel-refusal-codes.md`
- QA: `.factory-state/artifacts/QA-0289-TASK-0304-channel-refusal-codes.md`
