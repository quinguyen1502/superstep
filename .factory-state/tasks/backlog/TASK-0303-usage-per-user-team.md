# Task

## Metadata

- Project: superstep
- Task ID: TASK-0303
- Title: Per-user and per-team usage on the Usage page
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Let studio admins see who and which team uses the most runs, tokens and cost.

## Owner-Facing Outcome

Settings, Usage shows People and Teams tables for the window: runs, success rate, tokens, estimated cost and unpriced share per user and per team, with the user's display name and the team name.

## Scope

### In Scope

- SQL aggregation only: per user from `runs.owner` (and the usage table for per-model cost when present); per team by joining `team_members`. A user in several teams counts toward each team; the page says so.
- `GET /api/admin/usage` gains `users` and `teams` blocks (top 20 by cost or runs, with a total row), permission `users.manage`; deleted users show a placeholder.
- Never as metric labels: no `user_id` or team id is added to any OTel metric (business rule of REQ-0094 and REQ-0095).
- UI tables with en and vi strings.

### Out Of Scope

- Budgets (TASK-0306).
- Usage visible to non-admin users about themselves (separate decision).

## Dependencies

- None beyond the merged MVP Usage page; uses the usage table from TASK-0301 for model columns when it has merged.

## Acceptance Criteria

- API test with two users in two teams (one shared member) returns correct per-user and per-team sums and the double-count note flag.
- A test proves no telemetry call receives a user or team id.
- Playwright: tables render for an admin and are absent without `users.manage`.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.

## Handoff Notes

- Use branch `factory/task-0303-usage-per-user-team` from `develop` when implementation begins.
