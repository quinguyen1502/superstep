# Task

## Metadata

- Project: superstep
- Task ID: TASK-0336
- Title: Make an existing Dataset column unique
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P1
- Size: S

## Objective

A manager can turn on (and off) unique for an existing column after a duplicate check, so imported datasets can be upserted.

## Scope

### In Scope

- Schema update allows `unique` false to true when no two rows share a non-empty value; it backfills `dataset_row_keys` inside the writer lock and the same transaction.
- Duplicates return a new `DATASET_UNIQUE_DUPLICATES` code with the count and up to 5 sample row ids; the Schema view links to a filtered grid.
- Turning unique off removes keys, after checking bindings that use the column as an upsert key or delete key (`DATASET_SCHEMA_INCOMPATIBLE` naming the workflow).
- Allowed kinds follow the existing unique rules.

### Out Of Scope

- Composite unique keys.

## Inputs

- `services/dataset_service.py` `update_column`; `repositories/dataset_rows.py` key helpers.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- None. Branch from `develop`.

## Acceptance Criteria

- Importing a CSV without a key, then marking `ticket_id` unique, allows upsert by `ticket_id`.
- A column with duplicates cannot become unique and the error shows the count and sample rows.
- A bound upsert key cannot lose unique.

## Tests

- Schema service tests on SQLite and PostgreSQL, concurrent insert during the backfill, binding checks, Playwright schema flow.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0336-dataset-unique-later` from `develop` when implementation begins.
