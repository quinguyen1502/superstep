# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0335
- Task ID: TASK-0344
- Created: 2026-11-14
- Outcome: pass with follow-up

## Evidence

The integrated Dataset regression, layers and envelope suite passed with 102 passed and 94 skipped on the local SQLite environment with Deno. Six Playwright cases passed, including the bilingual handbook capture. Frontend build, unit suite (319 tests), lint, both strict handbook builds, image link checking and the five matching handbook section anchors passed.

## Required Follow-Up

Confirm the GitHub checks on the proposed merge head. This PR contains the implementation stack for verification. Final admission to develop requires the dependency PRs and fresh integration CI.

## Finding Coverage

| Finding in REQ-0100 | Regression evidence |
| --- | --- |
| Write-only frames and needless revisions | `test_dataset_write_only.py::test_write_only_token_reproduces_review_probe`, `test_noop_upsert_keeps_revision_updated_and_audit` |
| Receipt data, replay and expiry | `test_dataset_receipts.py::test_receipt_migration_minimizes_all_cells_and_supports_downgrade`, `test_deleted_row_replay_and_worker_retention` |
| Null-safe inequality and case-insensitive Find | `test_dataset_rows.py::test_ne_matches_empty_cells_and_text_matching_ignores_case`, `test_text_sort_ignores_case_with_an_exact_tiebreak` |
| Team management and token issuer | `test_dataset_team_authority.py::test_team_editors_edit_rows_and_managers_manage`, `test_rotation_keeps_the_issuer_and_the_token_still_authorizes` |
| Turn on Unique after import | `test_dataset_schema_changes.py::test_csv_import_then_unique_allows_upsert` |
| Membership, sharing and mapped filter errors | `test_datasets.py`, `test_dataset_access.py::test_grants_require_saved_workflow_and_explicit_team_scope`, `test_dataset_runtime.py::test_dataset_node_names_invalid_filter_and_empty_state_key` |
| Scope error versus invalid credentials | `test_dataset_connected.py::test_connected_schema_and_scope_fail_explicitly` |
| Removed columns and required defaults | `test_dataset_schema_changes.py::test_removed_columns_free_the_active_limit_and_keep_keys_reserved`, `test_required_column_with_default_backfills_existing_rows` |
| CSV round trip and mandatory revisions | `test_dataset_csv.py::test_csv_round_trip_keeps_leading_zeros_plus_signs_and_formulas`, `test_studio_deletes_require_the_revision` |
| Viewer, empty, not-found, delete naming and CSV issues | `dataset-studio-states.spec.ts`, all three scenarios passed |
| Dataset tab URLs, grid persistence and pagination | `dataset-grid-usability.spec.ts`, with refreshed English and Vietnamese light and dark grid captures |
| Run trace, write warning and grant shortcut | `dataset-trace.test.ts`, `dataset-run-feedback.spec.ts` |
| Python and TypeScript export parity | `test_dataset_python_standalone.py`, `test_dataset_typescript_standalone.py` with Deno |
