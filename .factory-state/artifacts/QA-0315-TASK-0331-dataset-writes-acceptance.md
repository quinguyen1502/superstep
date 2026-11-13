# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0315
- Task ID: TASK-0331
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0331 on `factory/task-0331-dataset-writes-acceptance`, stacked on TASK-0326 through TASK-0330. Backend tests used `backend/.venv` on SQLite. PostgreSQL cases skipped locally without a test database URL and run in CI. Handbook builds used `handbook/.venv`.

## Acceptance Criteria Coverage

- Criterion: The support-ticket path passes: Agent upsert, public find, denied public delete, Studio delete, and a repeated standalone setup that keeps the remaining rows.
  - Result: pass
  - Evidence: `tests/test_dataset_writes_acceptance.py`. An Agent with write access and no delete upserts from chat. A read-only Agent tool fails when asked to write. Chat and API runs find the ticket. Studio Run delete fails without the capability. Chat and API delete fail with it. Demo mode denies. Studio Run then deletes. A connected delete fails with a token without the capability and succeeds with one. The exported project deletes from SQLite, and a second setup keeps the remaining row.
- Criterion: Python and TypeScript coverage from the export tasks still passes against this path's contract.
  - Result: pass
  - Evidence: `tests/test_dataset_python_standalone.py`, `tests/test_dataset_typescript_standalone.py`, and `tests/test_dataset_project_export.py` pass on this branch.
- Criterion: Both handbook languages describe delete, Agent writes, and the entries that cannot delete. Both handbook builds succeed.
  - Result: pass
  - Evidence: `handbook/docs/en/guide/datasets.md` and `handbook/docs/vi/guide/datasets.md` have the access table, Allow row deletion, Delete row, and Agent insert and upsert. `zensical build`, `zensical build -f mkdocs.vi.yml`, and `python3 check_images.py site` pass.

## UX And Accessibility Coverage

- Not applicable. Documentation only.

## Checks Performed

- `pytest -q tests/test_dataset_writes_acceptance.py tests/test_dataset_python_standalone.py tests/test_dataset_typescript_standalone.py tests/test_dataset_project_export.py tests/test_dataset_public_entry.py` — passed, PostgreSQL skipped.
- Handbook builds as above.
- `factory verify run --profile full` — passed.
- `factory validate` and `factory validate --only hygiene` — passed.

- After merging TASK-0330 and `develop` (TASK-0332): `pytest -q tests/test_dataset_writes_acceptance.py tests/test_dataset_public_entry.py tests/test_dataset_write_only.py tests/test_dataset_agent_tool.py` — 23 passed. Both handbook builds pass.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL runs in CI.

## Residual Risk

- Low.

## Assumptions

- None.

## Required Follow-Up

- None.

## QA Decision

Passed to done.
