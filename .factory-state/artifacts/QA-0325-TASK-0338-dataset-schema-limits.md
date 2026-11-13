# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0325
- Task ID: TASK-0338
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0338 on `factory/task-0338-dataset-schema-limits`. Backend tests used `backend/.venv` on SQLite; PostgreSQL cases skip without a test database URL and run in CI. Playwright ran against an isolated local stack with the system Chrome.

## Acceptance Criteria Coverage

- Criterion: A dataset at 100 active columns can add one after removing one.
  - Result: pass
  - Evidence: `tests/test_dataset_schema_changes.py::test_removed_columns_free_the_active_limit_and_keep_keys_reserved` gets `DATASET_COLUMN_LIMIT` with `max: 100` at 100 columns, removes `c0`, then adds `extra`. The removed key stays reserved (`DATASET_COLUMN_KEY_TAKEN`), and the definition cap returns `DATASET_COLUMN_LIMIT` with its own `max`.
- Criterion: After removal no row contains the removed key.
  - Result: pass
  - Evidence: `test_removing_a_column_clears_its_values_in_batches` runs with a batch size of 2 over 5 rows. No row keeps `ticket` or `title`, unique keys for `ticket` are gone, the audit records only `{field, rows: 5}`, and the CSV export has no removed columns. `test_export_snapshot_excludes_removed_keys` checks the exported project snapshot. The Playwright spec reads the rows back through the API after removing Note.
- Criterion: A required column with a default appears with the default in every existing row; the row byte limit is checked first.
  - Result: pass
  - Evidence: `test_required_column_with_default_backfills_existing_rows` rejects a required column without a default (`DATASET_SCHEMA_HAS_ROWS`), backfills a select default and a boolean `False`, and leaves rows and revision untouched when Unique plus a shared default would duplicate values. `test_required_default_checks_the_row_byte_limit_first` returns `DATASET_ROW_TOO_LARGE` and leaves rows and revision unchanged. `test_schema_row_changes_stay_within_the_query_budget` backfills and clears 1,600 rows within 30 statements.

## UX And Accessibility Coverage

- Criterion: Explain the limit and the default requirement in place, en and vi.
  - Result: pass
  - Evidence: the Schema dialog shows "N of 100 columns. Removed columns do not count.", a new required column shows the default help, and the remove-column confirmation says values are cleared and the key stays reserved. `e2e/dataset-schema-limits.spec.ts` checks these texts. Locale parity passed.

## Checks Performed

- `pytest tests/test_dataset_schema_changes.py` — 10 passed, PostgreSQL cases skipped.
- `npx playwright test e2e/dataset-schema-limits.spec.ts e2e/dataset-unique-later.spec.ts e2e/datasets.spec.ts` with `PW_CHROME=/usr/bin/google-chrome` — passed.
- `factory verify run --profile full` — passed: frontend build, lint, and test; backend pytest; Python SDK tests; TypeScript SDK build, test, and typecheck.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL and the other E2E shards run in CI.

## Residual Risk

- Clearing and backfilling do not bump row revisions, so a client that cached a row shows the old values until it reloads.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0338.

## QA Decision

Passed to done.
