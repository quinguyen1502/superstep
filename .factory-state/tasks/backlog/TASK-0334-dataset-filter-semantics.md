# Task

## Metadata

- Project: superstep
- Task ID: TASK-0334
- Title: Make Dataset filters null-safe and case-insensitive
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P1
- Size: M

## Objective

`ne` matches empty cells, and contains, search, and text sort ignore case the same way on SQLite and PostgreSQL.

## Scope

### In Scope

- `ne` as `IS DISTINCT FROM` (null-safe) for every kind; boolean `ne` included.
- Case-insensitive `contains`, free-text search, and text sort using one Unicode case fold on both databases (Python-registered SQLite function or a normalized expression; PostgreSQL `lower` with a deterministic tiebreak). Vietnamese letters with diacritics fold correctly (for example U+0110 and U+0111, capital and small D with stroke).
- `eq`, unique keys, and upsert matching stay exact.
- UI labels: `is_null`/`not_null` shown as "is empty"/"is not empty"; operator help text in the grid and the node editor; en/vi.
- Agent tool operator descriptions match the new semantics.

### Out Of Scope

- New operators and nested groups (phase 3, TASK-0345).
- Standalone export runtimes (TASK-0343).

## Inputs

- `repositories/dataset_rows.py` `_predicate`, `_contains`, `query`; `core/dataset_types.py` `filter_operators`.
- Review probe: "Webhook" 3 rows, "webhook" 0; `csat ne 5` dropped empty cells.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- None. Branch from `develop`.

## Acceptance Criteria

- `csat ne 5` returns rows where csat is empty.
- Search "webhook", "WEBHOOK", and "Webhook" return the same rows; a lowercase Vietnamese query with diacritics finds the capitalized value.
- Text sort orders case-insensitively with a stable tiebreak, identical on both databases.
- Query performance on 10,000 rows stays within the current query budget.

## Tests

- Parametrized filter, search, and sort tests on SQLite and PostgreSQL, including empty cells and Vietnamese text.
- Agent tool and Dataset node filter tests.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0334-dataset-filter-semantics` from `develop` when implementation begins.
