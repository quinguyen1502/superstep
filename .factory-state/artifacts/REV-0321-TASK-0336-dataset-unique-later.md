# Review

## Metadata

- Project: superstep
- Review ID: REV-0321
- Task ID: TASK-0336
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for turning Unique on and off on an existing Dataset column against REQ-0100, PLAN-0018, DES-0007, ARCH-0003, and the TASK-0336 acceptance criteria. Row writes, CSV import, grants, tokens, and export generators were checked to stay unchanged.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md

## Findings

### Blocking

- None.

### Non-Blocking

- The binding check reads saved workflow graphs before the writer lock is taken. A workflow saved in the same instant could still bind the field as its key. Execution stays safe because the row service rejects upsert and delete-by-key on a column that is not unique (`DATASET_UPSERT_KEY_INVALID`).
- Exported projects that use the connected API cannot be seen by the check. They get the same `DATASET_UPSERT_KEY_INVALID` after Unique is turned off. Recorded in the task handoff notes.
- `DATASET_SCHEMA_INCOMPATIBLE` keeps its generic message. The workflow is named in `details.workflow` and `details.workflow_id`, and Studio shows the name with a link. A workflow the caller cannot open is reported without its name or id.

## Standards And Architecture Alignment

- Turning Unique on reads only the column value of each row in batches, checks for repeats, and inserts `dataset_row_keys` in the same transaction that advances the dataset revision under the writer lock. A row write that read the old definition fails with `DATASET_SCHEMA_CONFLICT`, so no duplicate can slip in during the backfill.
- Duplicates return the new `DATASET_UNIQUE_DUPLICATES` code (409) with `count` (rows that share a value), `values` (distinct repeated values), up to 5 sample row ids, and the first repeated value for the grid filter. Nothing is written.
- Turning Unique off deletes that column's row keys in the same transaction. Key, kind, Required, and removed options stay incompatible changes, as before.
- The audit event records the field and the new unique flag only.
- The error code is in `core/errors.py`, `docs/api-errors.md`, and both locale catalogs.

## Design Alignment

- Edit column shows Required disabled with the reason in place, and Unique enabled with help text that explains the duplicate check and the binding rule.
- The duplicate alert uses the shared Alert with a top-aligned icon, states the count, lists sample row ids, and offers "Show rows with <value>", which closes the dialogs and opens the grid filtered to that value.
- The in-use alert names the workflow and links to it.
- English and Vietnamese catalogs and the handbook pages changed together.

## Validation Review

- New backend tests cover CSV import then Unique on then upsert, duplicates with count and samples, number values `1` and `1.0` counted as the same key, the upsert and delete-by-key binding checks, Unique off dropping keys, and a concurrent insert during the backfill.
- The new Playwright spec walks the schema flow, and the existing Datasets spec now expects the Required and Unique checkboxes.

## Assumptions

- "Allowed kinds follow the existing unique rules": every kind can be unique today, so no kind is excluded.

## Required Follow-Up

- None for this task.

## Review Decision

Approved for QA. No blocking findings.
