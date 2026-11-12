# Task

## Metadata

- Project: superstep
- Task ID: TASK-0306
- Title: Per-user and per-team budgets
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-12
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095, DEC-0096
- Plan: PLAN-0014
- Phase: 3
- Size: L
- Review: `.factory-state/artifacts/REV-0291-TASK-0306-usage-budgets.md`
- QA: `.factory-state/artifacts/QA-0291-TASK-0306-usage-budgets.md`

## Objective

Let studio admins set monthly cost budgets per user and per team and see who is close to or over them.

## Owner-Facing Outcome

In Settings, Usage an admin sets a monthly budget in USD for a user or a team; the page shows spend against budget, and users and teams receive warnings at 80 and 100 percent. Runs can start and continue at every spend level.

## Scope

### In Scope

- Budget model and migration (scope user or team, monthly amount, alert thresholds, created by); CRUD API under the admin usage routes with `users.manage`; audit events.
- Spend computed in SQL from the usage table for the calendar month in the studio time zone; unpriced usage shown next to spend and never counted as zero cost silently.
- Notifications through the existing notification service at thresholds, once per month and threshold.
- Advisory budgets under DEC-0096; delete actions use `ConfirmDeleteDialog`.
- en and vi strings; handbook section on budgets.

### Out Of Scope

- Per-workflow budgets and provider-side spend caps.
- Metric labels per user or team.

## Dependencies

- TASK-0301 and TASK-0303 merged.
- [DEC-0096](../../decisions/DEC-0096-usage-budget-warnings.md) accepted by the owner.

## Acceptance Criteria

- Spend for a user and a team matches the usage table for the month.
- New and existing runs continue after spend reaches 100 percent. A threshold warning is sent at most once per budget per calendar month.
- API returns 403 without `users.manage`; deleting a budget requires typing its name.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- Should a user see their own budget? Recommended: later, separate decision.

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-12: Moved from backlog to todo after the Phase 2 stack merged. Owner approved starting Phase 3 on 2026-11-11.
- 2026-11-12: Owner selected warnings at 80 and 100 percent. Recorded DEC-0096 and started the task on factory/task-0306-usage-budgets.

- 2026-11-12: Implemented administrator budget CRUD, monthly spend and warning deduplication, in-app and external delivery through the existing notifier, and the localized Usage card. Month boundaries use STUDIO_TIMEZONE with UTC as the default.

- 2026-11-12: Targeted budget regression passed for permissions, CRUD, user and team spend, month boundaries, unpriced rows, and concurrent warning deduplication.

- 2026-11-12: Playwright verified creating a budget and typing the exact target name before deletion. Fixed an import-time annotation collision on Python 3.12.

- 2026-11-12: Owner approved merge. Moved to done on PR #362.

## Handoff Notes

- Use branch `factory/task-0306-usage-budgets` from `develop` when implementation begins.
