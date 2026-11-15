# Task

## Metadata

- Project: superstep
- Task ID: TASK-0338
- Title: Fix removed-column limits and required columns on existing rows
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P2
- Size: S

## Objective

Removed columns stop counting toward the column limit and stop holding data, and a required column with a default can be added to a dataset that has rows.

## Scope

### In Scope

- Limit counts active columns; removed column metadata stays (key not reusable) with a separate hard cap of 200 total definitions.
- Removing a column clears its values from rows in batches inside the writer lock; audit records the field and row count only.
- Adding a required column with a default backfills the default into existing rows in one transaction; without a default it keeps `require_empty`.

### Out Of Scope

- Restoring a removed column.

## Inputs

- `dataset_service.py` `add_column`, `remove_column`; `MAX_COLUMNS`; CSV import column count.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)
- Review: [REV-0325](../../artifacts/REV-0325-TASK-0338-dataset-schema-limits.md)
- QA: [QA-0325](../../artifacts/QA-0325-TASK-0338-dataset-schema-limits.md)

## Dependencies

- None. Branch from `develop`.

## Acceptance Criteria

- A dataset at 100 active columns can add one after removing one.
- After removal no row contains the removed key.
- A required column with a default appears with the default in every existing row; the row byte limit is checked first.

## Tests

- Schema service tests on both databases; large-dataset backfill within the query budget; export snapshot excludes removed keys.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.
- 2026-11-13: Owner accepted REQ-0100 and PLAN-0018. Started on `factory/task-0338-dataset-schema-limits` after TASK-0336, then merged `develop` once TASK-0336 landed. The column limit counts active columns with a 200-definition cap, removing a column clears its values and keys in batches under the writer lock, and a required column with a default backfills existing rows after the row byte check. Review REV-0325. QA QA-0325. Moved to done.

## Handoff Notes

- Branch `factory/task-0338-dataset-schema-limits`. Ready PR into `develop`; merge when every required check is green.
- A required unique column with a default can be added only while the dataset has at most one row; with more rows the default would repeat and the request fails with `DATASET_UNIQUE_DUPLICATES`.
