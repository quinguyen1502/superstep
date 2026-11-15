# Review

## Metadata

- Project: superstep
- Review ID: REV-0325
- Task ID: TASK-0338
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for removed-column limits, clearing removed values, and required-with-default backfill against REQ-0100, PLAN-0018, DES-0007, ARCH-0003, and the TASK-0338 acceptance criteria. Row writes, CSV import limits, grants, and export generators were checked to stay unchanged.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md

## Findings

### Blocking

- None.

### Non-Blocking

- Clearing and filling use one dialect-specific `UPDATE` each (`jsonb` operators on PostgreSQL, `json_remove` and `json_set` on SQLite). The SQLite path runs locally; the PostgreSQL path runs in the CI PostgreSQL job.
- Clearing and filling do not change row revisions. A row edit that read the old definition already fails with `DATASET_SCHEMA_CONFLICT` because the definition revision advances.
- `DATASET_COLUMN_LIMIT` is reused for both limits; `details.max` is 100 for active columns and 200 for all definitions.

## Standards And Architecture Alignment

- `add_column` counts active columns against 100 and all definitions, removed included, against 200. A removed key stays reserved (`DATASET_COLUMN_KEY_TAKEN`).
- `remove_column` clears the field from rows in batches of 500 inside the writer lock and the transaction that advances the revision, and drops its row keys when the column was unique. The audit event records the field and the number of rows cleared, never values.
- A required column with a default first checks every row against the 64 KiB row limit (`DATASET_ROW_TOO_LARGE`, nothing written), then writes the default into every row in the same transaction. A required unique column with a default also builds its row keys, so a repeated default fails with `DATASET_UNIQUE_DUPLICATES`. Without a default, `DATASET_SCHEMA_HAS_ROWS` stays, with a clearer message.

## Design Alignment

- The Schema dialog shows the active column count against 100 and says removed columns do not count.
- Add column explains that existing rows get the default when Required is checked.
- The Remove column confirmation says values are cleared and the key stays reserved.
- English and Vietnamese catalogs, the handbook pages, and `docs/api-errors.md` changed together.

## Validation Review

- Backend tests cover the active limit and the definition cap, reserved keys, batched clearing with audit counts, the CSV export and project snapshot after removal, the default backfill, the unique default, the row byte check, and a 1,600-row query budget for remove and backfill.
- The new Playwright spec adds a required column with a default to a dataset with rows and removes a column.

## Assumptions

- Restoring a removed column stays out of scope, so clearing its values is final.

## Required Follow-Up

- None for this task.

## Review Decision

Approved for QA. No blocking findings.
