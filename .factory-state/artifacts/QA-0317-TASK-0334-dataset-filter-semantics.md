# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0317
- Task ID: TASK-0334
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0334 on `factory/task-0334-dataset-filter-semantics`. Backend tests ran on SQLite and on a local PostgreSQL 16 server (`C.UTF-8`, no ICU). Playwright ran the Datasets and Dataset node specs with system Chrome.

## Acceptance Criteria Coverage

- Criterion: `csat ne 5` returns rows where csat is empty.
  - Result: pass
  - Evidence: `tests/test_dataset_rows.py::test_ne_matches_empty_cells_and_text_matching_ignores_case` returns the empty-score row for `score ne 5`, and the same for text and boolean `ne`, on both databases.
- Criterion: Search "webhook", "WEBHOOK", and "Webhook" return the same rows; a lowercase Vietnamese query with diacritics finds the capitalized value.
  - Result: pass
  - Evidence: The same test loops over the three spellings for search and contains, and finds a capitalized value with Vietnamese diacritics and U+0110 from a lowercase query and from an uppercase fragment.
- Criterion: Text sort orders case-insensitively with a stable tiebreak, identical on both databases.
  - Result: pass
  - Evidence: `tests/test_dataset_rows.py::test_text_sort_ignores_case_with_an_exact_tiebreak` asserts one order for ascending and one for descending, including "ALPHA", "Alpha", "alpha" and two Vietnamese values that start with U+0110 and U+0111, on SQLite and PostgreSQL.
- Criterion: Query performance on 10,000 rows stays within the current query budget.
  - Result: pass
  - Evidence: A local benchmark on 10,000 rows timed search, contains, `ne`, and text sort with offset 9,000. SQLite: 1 to 19 ms, unchanged from the previous build. PostgreSQL: 4 to 11 ms, within 0.6 ms of the previous build.

## UX And Accessibility Coverage

- Criterion: Operator help in the grid and the node editor, in English and Vietnamese.
  - Result: pass
  - Evidence: `e2e/datasets.spec.ts` checks the grid filter help and a search in capitals. `e2e/dataset-node-editor.spec.ts` checks the operator help under the operator control. Locale parity passes.

## Checks Performed

- `pytest -q tests -k dataset` with `TEST_DATABASE_URL` set to the local PostgreSQL — 85 passed, 2 skipped.
- `npx playwright test e2e/datasets.spec.ts e2e/dataset-node-editor.spec.ts` — 4 passed.
- `factory verify run --profile full` — passed.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- The ICU collation path is exercised only in CI (PostgreSQL 17).
- NFD input is not normalized.

## Residual Risk

- Existing saved workflows with `ne` or `contains` can return more rows.

## Assumptions

- Text `lt`, `lte`, `gt`, and `gte` stay exact comparisons. The task names only contains, search, and sort.

## Required Follow-Up

- TASK-0343 brings the same semantics to standalone exports.

## QA Decision

Passed to done.
