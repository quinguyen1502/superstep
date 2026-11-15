# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0308
- Task ID: TASK-0324
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0324 on `factory/task-0324-dataset-delete-capability`. Backend tests used `backend/.venv` on SQLite. Frontend locale tests, lint, and Playwright used system Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.

## Acceptance Criteria Coverage

- Criterion: A manager can enable and disable delete on a workflow grant and on a new token. Existing grants and tokens remain false.
  - Result: pass
  - Evidence: `tests/test_dataset_access.py::test_delete_capability_is_separate_from_permission` turns the flag on and off for a grant, issues one token without it and one with it, and checks rotation keeps it. `test_existing_access_rows_default_non_deleting` upgrades a `0066` grant and token to head and reads false.
- Criterion: Read, write, and read-and-write behavior is unchanged.
  - Result: pass
  - Evidence: The same test keeps a write grant from reading and a read grant from writing. Existing grant and token tests in `tests/test_dataset_access.py` passed. Connected, runtime, and receipt tests passed.
- Criterion: The control is keyboard reachable in both languages. Revoke still requires the typed name and sends no confirm field.
  - Result: pass
  - Evidence: `frontend/e2e/dataset-access.spec.ts` focuses both checkboxes and presses Space, then revokes with the typed workflow and token names. `src/lib/__tests__/locales.test.ts` passed for the new key. The revoke route is still DELETE with no confirm field.

## UX And Accessibility Coverage

- Criterion: Checkbox is off until enabled and is keyboard reachable.
  - Result: pass
  - Evidence: Playwright expects the grant checkbox to be disabled before a workflow is chosen, unchecked after it is chosen, and checked after Space. The token checkbox starts unchecked.

## Checks Performed

- `backend/.venv/bin/python -m pytest -q tests/test_dataset_access.py tests/test_db_migrations.py tests/test_layers.py` — 8 passed, 4 skipped (PostgreSQL).
- `pytest -q tests/test_dataset_connected.py tests/test_dataset_runtime.py tests/test_dataset_receipts.py tests/test_api_envelope.py` — passed, PostgreSQL skipped.
- `npm test --workspace=frontend -- src/lib/__tests__/locales.test.ts` — 5 passed.
- `npm run lint --workspace=frontend` — 0 errors, existing warnings.
- `PW_CHROME` Playwright `e2e/dataset-access.spec.ts` — 1 passed.
- `git diff --check` — clean.
- A full `pytest -q` later filled the disk (`database or disk is full`, `No space left on device`). Those failures started after the targeted Dataset tests had passed and are not treated as product defects.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL was not running locally. The new column is a non-null boolean with `server_default` false, and the SQLite Alembic upgrade covered an existing row.

## Residual Risk

- CI must run the Postgres pytest job before merge. This QA does not claim that job has finished.

## Assumptions

- Omitting `allow_delete` is the off state. The UI sends the boolean explicitly.

## Required Follow-Up

- None inside TASK-0324. Do not treat the flag as permission to delete a row until TASK-0325.

## QA Decision

Passed to done. Local PostgreSQL coverage remains a CI check, not an open product defect.
