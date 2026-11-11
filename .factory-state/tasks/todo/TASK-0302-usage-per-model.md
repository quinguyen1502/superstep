# Task

## Metadata

- Project: superstep
- Task ID: TASK-0302
- Title: Per-model breakdown on the Usage page
- Status: todo
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

Close the MVP gap where per-model usage was only in Grafana.

## Owner-Facing Outcome

Settings, Usage shows a Models table for the chosen window: model, provider, calls, tokens in and out, estimated cost, unpriced calls and errors, sortable by cost or tokens.

## Scope

### In Scope

- `GET /api/admin/usage` gains a `models` block aggregated in SQL from the usage table; same window and permission (`users.manage`) as today.
- Models table in `UsageSection.tsx` with existing Card and Table patterns, en and vi strings under `settings.usage.*`, empty state when no rows exist yet, and the note on when per-model data starts.
- Unpriced rows shown as such; cost keeps the "at least" prefix when any row is unpriced (DES-0006).

### Out Of Scope

- Charts per model over time (Grafana keeps those).
- Per-user views (TASK-0303).

## Dependencies

- TASK-0301 merged.

## Acceptance Criteria

- API test: two models in the window return two rows with correct sums; a user without `users.manage` gets 403.
- Playwright: the Models table renders and sorts; the empty state shows on a fresh database.
- en/vi locale parity passes; DES-0006 UI rules respected.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.

## Handoff Notes

- Use branch `factory/task-0302-usage-per-model` from `develop` when implementation begins.
