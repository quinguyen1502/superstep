# Task

## Metadata

- Project: superstep
- Task ID: TASK-0301
- Title: Usage rows written at run end
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-11
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Store per-call usage so the app can break usage down by model, user and team in SQL.

## Owner-Facing Outcome

Every finished run leaves one row per model or embedding call group (model, provider, tokens, cost, priced flag), so the Usage page can show per-model and per-person figures without parsing run events.

## Scope

### In Scope

- Verified on `develop` 6047c732: there is no usage table; the MVP Usage API aggregates `runs` columns (`tokens_in`, `tokens_out`, `cost_usd`, `owner`, `workflow_id`, `status`, `started`), and per-call usage lives only in `runs.events` JSON.
- New model and Alembic migration, for example `run_usage`: `id`, `run_id`, `workflow_id`, `owner`, `node_id`, `kind` (`llm`, `embedding`, `review`), `model`, `provider`, `tokens_in`, `tokens_out`, `cost_usd` (NULL when unpriced), `calls`, `errors`, `duration_ms`, `created`; indexes on `created` and (`owner`, `created`).
- Written once at run end (all terminal statuses) in the run service through a repository, aggregated per node and model; idempotent on run recovery or re-finish; parent and child runs each write their own rows.
- Rows follow run deletion and retention (deleted with the run).
- A one-off admin command to backfill recent runs from `runs.events`, optional and documented; the Usage page states that per-model data starts at the migration or backfill date.

### Out Of Scope

- UI (TASK-0302, TASK-0303).
- Retention policy for `runs.events` (later).

## Dependencies

- TASK-0298 merged, so embedding usage events exist when the writer is built (the writer must still accept runs without them).

## Acceptance Criteria

- A run with two LLM nodes on different models and one RAG node writes three rows whose sums equal the run's `tokens_in`, `tokens_out` and `cost_usd` (unpriced rows keep cost NULL).
- Re-finishing or recovering a run does not duplicate rows (unique key on run, node, kind, model, provider).
- Migration upgrades and downgrades on SQLite and Postgres; `tests/test_layers.py` passes; no raw SQL.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.
- 2026-11-10: `run_usage` table (run, workflow, owner, node, kind, model, provider, tokens, cost, calls, errors, duration) with unique key on run, node, kind, model, provider; written once when a run reaches a terminal status; deleted with its workflow or owner data. `python -m app.admin_cmd usage-backfill --days N` fills it from stored run events.
- 2026-11-10: Deviation: child runs write their own rows; SQLite-only migration test locally.
- 2026-11-10: Review REV-0286 and QA-0286. Moved to review.
- 2026-11-11: Owner approved merging the Phase 2 stack. Moved to done on PR #359.

## Handoff Notes

- Use branch `factory/task-0301-run-usage-table` from `develop` when implementation begins.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0286-TASK-0301-run-usage-table.md`
- QA: `.factory-state/artifacts/QA-0286-TASK-0301-run-usage-table.md`
