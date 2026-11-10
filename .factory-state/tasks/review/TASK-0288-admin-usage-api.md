# Task

## Metadata

- Project: superstep
- Task ID: TASK-0288
- Title: Admin usage API from run columns
- Status: review
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
- 2026-11-09: `GET /api/admin/usage` (`users.manage`; `window` 24h, 7d or 30d, optional `bucket` hour or day, `sort` runs or cost) in `api/routes/usage.py`, `UsageService` and `UsageRepository`. Totals (runs by status, success rate, tokens in and out, cost of priced runs, unpriced runs and share), buckets by status, and the top 10 workflows with names joined from `workflows` (a deleted workflow keeps its id and no name). SQL aggregation on run columns only; `runs.events` is never read.
- 2026-11-09: Rule for child runs: only top-level runs (`parent_run_id IS NULL`) are counted; a subgraph or workflow-tool child run is part of its parent's run. Tokens and cost come from the top-level run's own columns.
- 2026-11-09: Migration `0059_usage_indexes`: `ix_runs_started`, `ix_runs_status_started`, `ix_approval_waits_status_created`, `ix_webhook_deliveries_status_updated`; models declare the same indexes. Response schemas in `schemas/usage.py`; TypeScript types in `frontend/src/lib/usage.ts`.
- 2026-11-09: Tests: `tests/test_usage_api.py` (exact totals, buckets and top workflows; unpriced runs excluded from cost; 403 for a member, 401 without a session; migration up and down). The Postgres case runs when `TEST_DATABASE_URL` is set (CI); it was skipped locally because no Postgres server could be installed on the box.
- 2026-11-09: Review REV-0274 and QA-0274. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0274-TASK-0288-admin-usage-api.md`
- QA: `.factory-state/artifacts/QA-0274-TASK-0288-admin-usage-api.md`
