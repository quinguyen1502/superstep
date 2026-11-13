# Task

## Metadata

- Project: superstep
- Task ID: TASK-0341
- Title: Improve Dataset grid layout, paging, and formatting
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0101
- Plan: PLAN-0018
- Phase: Fix UI
- Priority: P2
- Size: M

## Objective

The grid keeps its layout, shows totals and page choices, sizes columns by type, and formats dates one way.

## Scope

### In Scope

- Persist the existing TanStack Table column order, sizing, and visibility state per dataset in browser storage (owner-confirmed: browser, not server). Pagination uses TanStack manual pagination state.
- Page size choice (25, 50, 100); row total and page numbers; the Dataset rows API returns `total` (counted with the active filter and search, capped at the query budget, `total_capped` when exceeded).
- Default widths by column kind; the sticky actions column no longer covers the last header's sort control.
- Long text edits in a multi-line editor.
- Dates and datetimes use the shared locale formatter everywhere in Datasets.
- Breadcrumb order "Datasets / <name>"; Schema and Access as sibling views (tabs) beside Rows as DES-0007 specifies.

### Out Of Scope

- Frozen columns, row height, virtual scroll (phase 3, TASK-0350).

## Inputs

- `dataset-grid.tsx` paging and column defs; `Datasets.tsx` breadcrumb and dialogs; rows API.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- TASK-0340 merged (shares components).

## Acceptance Criteria

- Reloading keeps column order, widths, and hidden columns.
- The grid shows "1-50 of N" and page numbers; changing page size keeps the filter.
- Schema and Access open as tabs with deep links.

## Tests

- Rows API `total` tests on both databases; Playwright for layout persistence, paging, and tabs; screenshot review in both themes.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): layout stays in the browser and uses TanStack Table state (DEC-0101).

## Handoff Notes

- Use branch `factory/task-0341-dataset-grid-usability` from `develop` when implementation begins.
