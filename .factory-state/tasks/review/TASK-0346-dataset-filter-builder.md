# Task

## Metadata

- Project: superstep
- Task ID: TASK-0346
- Title: Build the nested filter builder for the grid and the Dataset node
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Query
- Priority: P1
- Size: M

## Objective

Users build AND/OR groups with typed rules in the grid toolbar and the Dataset node editor.

## Scope

### In Scope

- One shadcn-based filter builder component used in the grid and the node editor: add rule, add group, switch conjunction, remove, typed value inputs, multi-value input for `in`/`not_in`.
- Keyboard reachable, en/vi, both themes, active filter count badge.

### Out Of Scope

- Saved or shared filter presets.

## Inputs

- Current grid Filter popover and node filter editor.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- TASK-0345 merged.

## Acceptance Criteria

- A user builds a two-level filter with the keyboard only and the grid result matches the API.
- The node editor round-trips the tree and shows validation inline.

## Tests

- Component unit tests; Playwright for grid and node editor.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Started after the readiness gate passed. Stacked on TASK-0345 (PR #403), which itself includes the Factory state reconciliation (PR #402).

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0337](../../artifacts/REV-0337-TASK-0346-dataset-filter-builder.md) and QA [QA-0337](../../artifacts/QA-0337-TASK-0346-dataset-filter-builder.md).

## Handoff Notes

- Use branch `factory/task-0346-dataset-filter-builder` from `develop` when implementation begins.
