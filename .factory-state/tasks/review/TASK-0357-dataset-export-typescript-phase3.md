# Task

## Metadata

- Project: superstep
- Task ID: TASK-0357
- Title: Carry Dataset phase 3 into the TypeScript export
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Export
- Priority: P1
- Size: M

## Objective

Generated TypeScript projects support the filter tree, new operators, `aggregate_rows`, and the new field types and rules on every backend.

## Scope

### In Scope

- Connected, SQLite, and PostgreSQL runtimes; standalone schema setup for new kinds and rules; `docs/dataset-export.md` TypeScript section only.

### Out Of Scope

- Studio grid features (no export impact).

## Inputs

- TypeScript export runtime; TASK-0343 parity suite.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- Same as TASK-0356; may run in parallel with it.

## Acceptance Criteria

- The shared parity cases pass on the Superstep API, SQLite, and PostgreSQL, including a mixed-backend graph.

## Tests

- TypeScript export parity suite.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Readiness gate passed. Started stacked after the Python export to share the connected contract and parity fixtures.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0348](../../artifacts/REV-0348-TASK-0357-dataset-export-typescript-phase3.md) and QA [QA-0348](../../artifacts/QA-0348-TASK-0357-dataset-export-typescript-phase3.md).

## Handoff Notes

- Use branch `factory/task-0357-dataset-export-typescript-phase3` from `develop` when implementation begins.
