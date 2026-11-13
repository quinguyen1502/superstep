# Task

## Metadata

- Project: superstep
- Task ID: TASK-0358
- Title: Accept Datasets phase 3 and update the handbook
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Acceptance
- Priority: P1
- Size: S

## Objective

One end-to-end path and the handbook cover phase 3.

## Scope

### In Scope

- Support-ticket scenario: nested filter, summary row, group by team, Agent aggregate answer, URL and auto-number fields, a validation rule, and a paste (if TASK-0355 shipped).
- English and Vietnamese handbook with matching anchors; screenshots in both themes.

### Out Of Scope

- Out-of-scope items listed in REQ-0101.

## Inputs

- Handbook Datasets guide.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- All other PLAN-0019 tasks merged or explicitly deferred by the owner.

## Acceptance Criteria

- The scenario passes in Playwright; the handbook build passes.

## Tests

- Playwright scenario; handbook build.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

## Handoff Notes

- Use branch `factory/task-0358-datasets-phase3-acceptance` from `develop` when implementation begins.
