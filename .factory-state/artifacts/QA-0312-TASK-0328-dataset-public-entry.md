# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0312
- Task ID: TASK-0328
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0328 on `factory/task-0328-dataset-public-entry`. Backend tests used `backend/.venv` on SQLite. PostgreSQL cases skipped locally without a test database URL and run in CI.

## Acceptance Criteria Coverage

- Criterion: Studio chat, public chat, and an API trigger can find and upsert when granted, and cannot delete.
  - Result: pass
  - Evidence: `test_public_entries_find_and_upsert_under_the_grant_but_never_delete` runs chat and API sources with `allow_delete` on. Find and upsert succeed and delete returns `DATASET_GRANT_DENIED`. `test_api_trigger_upserts_and_finds_but_cannot_delete` posts to the workflow API trigger in synchronous mode.
- Criterion: Studio Run and a schedule can delete when delete is enabled.
  - Result: pass
  - Evidence: The same test deletes from `ui` and `schedule` runs.
- Criterion: Demo mode cannot use Dataset operations. A nested tool follows its top run.
  - Result: pass
  - Evidence: `test_demo_mode_denies_every_dataset_operation` sets `STUDIO_DEMO_MODE` and every operation is denied, including from Studio Run. `test_workflow_tool_child_follows_its_top_run_entry` denies a child delete under a chat parent and allows it under a Studio parent.
- Criterion: A grant removed during a wait is denied when the run resumes.
  - Result: pass
  - Evidence: `test_public_run_resumes_without_a_grant_removed_while_it_waited`.
- Criterion: Write-only public-entry writes reveal no stored values (added after merging TASK-0332 from `develop`).
  - Result: pass
  - Evidence: The write-only upserts in `tests/test_dataset_public_entry.py` save no fields and get `{row: {id, revision}, inserted}` from chat, the API source, the waiting run, and the synchronous API trigger. The new regression test covers an upsert that matches an existing row.
- Criterion: An Agent write follows the same entry rule as the Dataset node.
  - Result: pass
  - Evidence: `test_agent_write_follows_the_same_entry_rule` upserts from a chat run with a write grant and fails without it.

## UX And Accessibility Coverage

- Not applicable. No UI change.

## Checks Performed

- `pytest -q tests/test_dataset_public_entry.py tests/test_dataset_access.py tests/test_dataset_runtime.py tests/test_dataset_agent_tool.py tests/test_dataset_receipts.py tests/test_datasets.py tests/test_layers.py` — 31 passed, PostgreSQL skipped. After merging `develop` (TASK-0332): `pytest -q tests/test_dataset_public_entry.py tests/test_dataset_access.py tests/test_dataset_runtime.py tests/test_dataset_agent_tool.py tests/test_dataset_write_only.py tests/test_dataset_receipts.py` — 35 passed.
- `factory verify run --profile full` — passed.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL runs in CI.

## Residual Risk

- Low for the entry rule. The check runs on each call, and the classification code did not change apart from passing demo mode.
- Resolved after merging `develop` with TASK-0332: write-only public-entry writes return identifiers only. Before that merge, a chat or API-trigger Dataset node upsert that matched an existing row put that row's values for the node's returned fields in the run state, and a synchronous API trigger sent them to the caller. `test_write_only_public_upsert_of_an_existing_row_reveals_no_values` now checks that such an upsert returns `{row: {id, revision}, inserted}` in the run state and in the synchronous trigger response, that the existing value appears in neither, and that a write-only node asking for fields is refused before anything is stored.

## Assumptions

- None.

## Required Follow-Up

- None inside TASK-0328.

## QA Decision

Passed to done.
