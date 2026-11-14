# Task

## Metadata

- Project: superstep
- Task ID: TASK-0350
- Title: Add frozen columns, row height, and virtual scrolling to the Dataset grid
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0101
- Plan: PLAN-0019
- Phase: 3 Grid
- Priority: P2
- Size: M

## Objective

Wide and long datasets stay usable: users freeze leading columns, choose a row height, and scroll large pages smoothly.

## Scope

### In Scope

- Upgrade the grid from TanStack Table 8.21 to the current stable 9.x line (9.3.1 at planning time) following the official migration guide; this also brings the cell selection feature that TASK-0355 uses.
- Frozen columns with the TanStack column pinning feature (up to 3 leading columns); row height short, medium, tall through the virtualizer's size estimate; both persisted with the TASK-0341 browser layout.
- Row virtualization with `@tanstack/react-virtual` (3.x), loading further pages on scroll within `MAX_PAGE_BYTES`. No custom virtualization or pinning code; only styling with theme tokens.

### Out Of Scope

- Server-side saved layouts per user (the owner chose browser storage).

## Inputs

- `dataset-grid.tsx`; PolarBase spreadsheet column and row options as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- REQ-0100 TASK-0341 merged.

## Acceptance Criteria

- 10,000 rows scroll without layout shift; frozen columns stay aligned in both themes and at narrow widths; keyboard cell navigation still works.

## Tests

- Playwright scroll and keyboard tests; regression run of the existing grid specs after the v9 upgrade; performance check recorded in QA.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): library-first per DEC-0101; TanStack Table v9 upgrade added; layout stays in the browser.

- 2026-11-14: Readiness gate passed. Stacked on the grid changes in PR #407 so the upgrade covers grouping and summaries.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0342](../../artifacts/REV-0342-TASK-0350-dataset-grid-layout.md) and QA [QA-0342](../../artifacts/QA-0342-TASK-0350-dataset-grid-layout.md).

- 2026-11-14: Owner approved merging PR #409 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0350-dataset-grid-layout` from `develop` when implementation begins.
