# Task

## Metadata

- Project: superstep
- Task ID: TASK-0349
- Title: Group Dataset grid rows by a column
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

The grid can group rows by one select, boolean, text, or date column, with collapsible groups, counts, and group summaries.

## Scope

### In Scope

- Group headers and collapse through TanStack Table grouping and expanding state in manual (server-driven) mode; counts and summaries from the aggregate engine; rows per group paged from the API; group choice persisted with the browser layout. No custom grouping model.

### Out Of Scope

- Multi-level grouping; Kanban views.

## Inputs

- PolarBase `table-group.service.ts` as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- TASK-0347 merged.

## Acceptance Criteria

- Grouping by status shows one header per value including empty, counts match the summary API.

## Tests

- API tests for group counts; Playwright group expand and collapse.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Readiness gate passed. Started stacked on PR #406 to share the aggregate engine.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0340](../../artifacts/REV-0340-TASK-0349-dataset-group-by.md) and QA [QA-0340](../../artifacts/QA-0340-TASK-0349-dataset-group-by.md).

- 2026-11-14: Owner approved merging PR #407 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0349-dataset-group-by` from `develop` when implementation begins.
