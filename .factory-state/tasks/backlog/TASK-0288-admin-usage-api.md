# Task

## Metadata

- Project: superstep
- Task ID: TASK-0288
- Title: Admin usage API from run columns
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: M

## Objective

Add `GET /api/admin/usage` that aggregates existing `runs` columns for a time window, for the Usage page.

## Scope

### In Scope

- Route requiring `users.manage` (403 otherwise), query `window` (24h, 7d, 30d) and optional `bucket`.
- Response: totals (runs by status, success rate, tokens in/out, cost of priced runs, unpriced run count and share), time series by bucket and status, top 10 workflows (runs, error rate, tokens, cost, unpriced runs) with names joined from `workflows`.
- SQL aggregation only (SQLite and Postgres); no parsing of `runs.events`; child runs counted once (document the rule for `parent_run_id`).
- Alembic migration adding an index on `runs.started` (and `workflow_id` if the query plan needs it).
- Response schema in `backend/app/schemas/` and the TypeScript client type.

### Out Of Scope

- UI (TASK-0289); product health counts (TASK-0290); per-model, per-user, per-team breakdowns (phase 3).

## Dependencies

- Owner acceptance of REQ-0094 and DES-0006 (can run in parallel with TASK-0285 to TASK-0287).

## Acceptance Criteria

- Seeded runs produce exact totals, buckets and top workflows on SQLite and Postgres test runs.
- `cost_usd` NULL runs count as unpriced and are excluded from the cost sum.
- Non-admin gets 403; the migration upgrades and downgrades cleanly.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
