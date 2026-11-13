# Task

## Metadata

- Project: superstep
- Task ID: TASK-0347
- Title: Show server-side column summaries in the Dataset grid
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0101
- Plan: PLAN-0019
- Phase: 3 Grid
- Priority: P1
- Size: M

## Objective

A summary row under the grid shows per-column statistics computed on the server for the current filter.

## Scope

### In Scope

- Summary API `POST /api/datasets/{id}/rows/summary` with the filter tree and per-column functions: count, empty count and percent, unique count, and for numbers sum, avg, min, max; for dates min and max.
- SQL aggregation on SQLite and PostgreSQL within the query budget; requires read.
- Summary row rendered through TanStack Table column footers with server values and a shadcn per-column function picker; the choice persists with the browser grid layout. TanStack row aggregation is not used because it only sees the loaded page.

### Out Of Scope

- Group-level summaries (TASK-0349 adds them per group).

## Inputs

- PolarBase spreadsheet calculation services as reference; rows repository.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- TASK-0345 merged.

## Acceptance Criteria

- Summary values equal a direct SQL check on seeded data, with filters applied.
- Empty percent counts empty cells per the TASK-0334 rules.

## Tests

- Aggregation tests on both databases; API permission tests; Playwright summary row.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

## Handoff Notes

- Use branch `factory/task-0347-dataset-column-summaries` from `develop` when implementation begins.
