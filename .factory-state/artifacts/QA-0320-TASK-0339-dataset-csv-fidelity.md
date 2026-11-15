# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0320
- Task ID: TASK-0339
- QA Owner: implementation QA
- Created: 2026-11-14
- Updated: 2026-11-14
- Outcome: pass

## Validation Scope

TASK-0339 on `factory/task-0339-dataset-csv-fidelity`. Backend tests ran on SQLite and on a local PostgreSQL 16 server. Playwright ran the CSV spec with system Chrome.

## Acceptance Criteria Coverage

- Criterion: Export then import of a dataset with `00123`, `+84901234567`, and `=SUM(A1)` gives identical values.
  - Result: pass
  - Evidence: `tests/test_dataset_csv.py::test_csv_round_trip_keeps_leading_zeros_plus_signs_and_formulas` compares the source and the re-imported rows on both databases; `e2e/dataset-csv.spec.ts` compares the exported file with the source.
- Criterion: DELETE without `revision` is rejected; a stale revision returns the conflict code.
  - Result: pass
  - Evidence: `tests/test_dataset_csv.py::test_studio_deletes_require_the_revision` for row, column, and dataset DELETE.

## UX And Accessibility Coverage

- Criterion: The preview shows the inferred type and lets the user change it.
  - Result: pass
  - Evidence: `e2e/dataset-csv.spec.ts` checks the hint, the Text type on a code column, and an import after changing it to Number. Locale parity passes.

## Checks Performed

- `pytest -q tests -k "dataset or layers or envelope"` on SQLite and with `TEST_DATABASE_URL` set to the local PostgreSQL — passed.
- `npm run lint` and `npm test` — passed.
- `npx playwright test e2e/dataset-csv.spec.ts` — 2 passed.
- `factory verify run --profile full`, `factory validate`, and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- Files saved by a spreadsheet that drops the apostrophe are read as typed; that is outside the export round trip.

## Residual Risk

- PAT clients that delete without `revision` must update.

## Assumptions

- Numbers longer than 15 digits count digits only, so exponents and signs do not count.

## Required Follow-Up

- None.

## QA Decision

Passed to done.
