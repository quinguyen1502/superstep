# Task

## Metadata

- Project: superstep
- Task ID: TASK-0306
- Title: Per-user and per-team budgets
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 3
- Size: L

## Objective

Let studio admins set monthly cost budgets per user and per team and see who is close to or over them.

## Owner-Facing Outcome

In Settings, Usage an admin sets a monthly budget in USD for a user or a team; the page shows spend against budget, users and teams get a notification at 80 and 100 percent, and, only if the owner chooses blocking, new runs are refused once a budget is spent.

## Scope

### In Scope

- Budget model and migration (scope user or team, monthly amount, alert thresholds, created by); CRUD API under the admin usage routes with `users.manage`; audit events.
- Spend computed in SQL from the usage table for the calendar month in the studio time zone; unpriced usage shown next to spend and never counted as zero cost silently.
- Notifications through the existing notification service at thresholds, once per month and threshold.
- Enforcement mode decided by the owner in a DEC before coding: warn only (recommended default) or block new runs with a new catalog error code; delete actions use `ConfirmDeleteDialog`.
- en and vi strings; handbook section on budgets.

### Out Of Scope

- Per-workflow budgets and provider-side spend caps.
- Metric labels per user or team.

## Dependencies

- TASK-0301 and TASK-0303 merged.
- A DEC for the enforcement mode accepted by the owner.

## Acceptance Criteria

- Spend for a user and a team matches the usage table for the month; threshold notifications fire once.
- With blocking off, runs never fail because of a budget; with blocking on (if chosen), a new run over budget fails with the new code and existing runs finish.
- API returns 403 without `users.manage`; deleting a budget requires typing its name.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- Warn only, or block new runs when a budget is spent? Recommended: warn only first.
- Should a user see their own budget? Recommended: later, separate decision.

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.

## Handoff Notes

- Use branch `factory/task-0306-usage-budgets` from `develop` when implementation begins.
