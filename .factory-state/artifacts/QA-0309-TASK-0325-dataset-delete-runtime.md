# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0309
- Task ID: TASK-0325
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0325 on `factory/task-0325-dataset-delete-runtime`. Backend tests used `backend/.venv` on SQLite. PostgreSQL cases skipped without a test database URL.

## Acceptance Criteria Coverage

- Criterion: A workflow with delete enabled removes one row by id and one row by unique key. A workflow or token without delete enabled cannot.
  - Result: pass
  - Evidence: `tests/test_dataset_runtime.py::test_workflow_delete_requires_the_separate_capability` denies a write grant, then deletes by id and by key with a read grant plus `allow_delete`. `tests/test_dataset_connected.py::test_connected_delete_replays_and_ignores_write_permission` denies a read-write token and allows a read token with `allow_delete`.
- Criterion: Replaying a completed delete returns the first result after the row is gone. A different payload for that identity conflicts.
  - Result: pass
  - Evidence: The connected test replays `job:delete` and conflicts when the same identity targets another row. `tests/test_dataset_receipts.py::test_delete_receipt_miss_does_not_stick_and_upsert_stays_serialized` replays a key delete and conflicts on a different payload.
- Criterion: A test or dry-run deletes nothing. Concurrent delete and upsert leave one committed result.
  - Result: pass
  - Evidence: The runtime test's mocked run returns `dry_run: true` and the row remains. The receipt test runs delete and upsert together and records both receipts.
- Criterion: A key that is no longer unique, or a field the schema no longer has, fails and leaves rows in place.
  - Result: pass
  - Evidence: Saving a workflow delete on the non-unique `score` field returns `DATASET_UPSERT_KEY_INVALID` and the row remains. A connected delete on `score` returns the same code. A missing connected row returns `DATASET_ROW_NOT_FOUND` and does not store a receipt.
- Criterion: Audit records the dataset, row id, workflow or credential, and run, and does not record cell values.
  - Result: pass
  - Evidence: Both runtime and connected tests read `dataset.row_delete` events and assert the ticket text and token secret are absent.

## UX And Accessibility Coverage

- Criterion: No new Studio control.
  - Result: pass
  - Evidence: The diff does not change frontend files. The existing grid delete route is untouched.

## Checks Performed

- `pytest -q tests/test_dataset_runtime.py tests/test_dataset_connected.py tests/test_dataset_receipts.py tests/test_dataset_access.py tests/test_layers.py` — passed, PostgreSQL skipped.
- `pytest -q tests/test_dataset_project_export.py tests/test_dataset_rows.py tests/test_api_envelope.py` — passed, PostgreSQL and TypeScript export skipped where Deno or Postgres was absent.
- `git diff --check` — clean.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL was not running locally. CI runs that job.

## Residual Risk

- Standalone Python and TypeScript projects do not execute `delete_row` yet. That is TASK-0329 and TASK-0330.

## Assumptions

- Public runs remain fully denied until TASK-0328. The runtime test covers an API-sourced run.

## Required Follow-Up

- None inside TASK-0325.

## QA Decision

Passed to done. Local PostgreSQL coverage remains a CI check.
