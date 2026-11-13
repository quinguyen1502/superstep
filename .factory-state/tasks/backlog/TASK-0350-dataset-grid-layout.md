# Task

## Metadata

- Project: superstep
- Task ID: TASK-0350
- Title: Add frozen columns, row height, and virtual scrolling to the Dataset grid
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Grid
- Priority: P2
- Size: M

## Objective

Wide and long datasets stay usable: users freeze leading columns, choose a row height, and scroll large pages smoothly.

## Scope

### In Scope

- Freeze up to 3 leading columns; row height short, medium, tall; both persisted with the TASK-0341 layout.
- Virtual scrolling with `@tanstack/react-virtual` inside the existing TanStack Table and shadcn rendering (DEC-0097), loading further pages on scroll within `MAX_PAGE_BYTES`.

### Out Of Scope

- Server-side saved layouts per user (open question).

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

- Playwright scroll and keyboard tests; performance check recorded in QA.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- Keep the layout in the browser (recommended until saved views) or store it per user on the server.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

## Handoff Notes

- Use branch `factory/task-0350-dataset-grid-layout` from `develop` when implementation begins.
