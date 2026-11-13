# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0321
- Task ID: TASK-0336
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0336 on `factory/task-0336-dataset-unique-later`. Backend tests used `backend/.venv` on SQLite; PostgreSQL cases skip without a test database URL and run in CI. Playwright ran against an isolated local stack with the system Chrome.

## Acceptance Criteria Coverage

- Criterion: Importing a CSV without a key, then marking `ticket_id` unique, allows upsert by `ticket_id`.
  - Result: pass
  - Evidence: `tests/test_dataset_schema_changes.py::test_csv_import_then_unique_allows_upsert` imports `Ticket ID,Subject` through the CSV API, sees upsert rejected, marks the column Unique, then upserts `T-2` with `inserted: false`. A blank key row stays allowed. `e2e/dataset-unique-later.spec.ts` turns Unique on from Edit column and upserts by `ticket_id`.
- Criterion: A column with duplicates cannot become unique and the error shows the count and sample rows.
  - Result: pass
  - Evidence: `test_duplicates_block_unique_with_count_and_samples` returns `DATASET_UNIQUE_DUPLICATES` with `count: 5`, `values: 2`, five sample row ids in row order, and no keys or revision change. The Playwright spec shows the count, the sample row ids, and "Show rows with T-1", which opens the grid filtered to the two rows.
- Criterion: A bound upsert key cannot lose unique.
  - Result: pass
  - Evidence: `test_bound_key_keeps_unique_and_unique_off_drops_keys` blocks Unique off while an Upsert workflow or a Delete-by-key workflow uses the field and names the workflow. With only a Find workflow, Unique off succeeds, removes the keys, and allows a repeated value.

## UX And Accessibility Coverage

- Criterion: Explain locked and changeable constraints in place, en and vi.
  - Result: pass
  - Evidence: Required is disabled with "Required is set when the column is created." and Unique has help text, both linked with `aria-describedby`. The duplicate alert icon is top-aligned with its title (checked in the spec). Locale parity passed.

## Checks Performed

- `pytest tests/test_dataset_schema_changes.py` — 4 passed, 4 PostgreSQL cases skipped.
- `npx playwright test e2e/dataset-unique-later.spec.ts e2e/datasets.spec.ts` with `PW_CHROME=/usr/bin/google-chrome` — 3 passed.
- `factory verify run --profile full` — passed: frontend build, lint, and test; backend pytest; Python SDK tests; TypeScript SDK build, test, and typecheck.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL and the other E2E shards run in CI.

## Residual Risk

- Exported projects that call the connected API with an upsert key are not visible to the binding check. Their upserts fail with `DATASET_UPSERT_KEY_INVALID` after Unique is turned off.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0336.

## QA Decision

Passed to done.
