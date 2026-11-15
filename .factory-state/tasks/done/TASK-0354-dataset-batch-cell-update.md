# Task

## Metadata

- Project: superstep
- Task ID: TASK-0354
- Title: Add an atomic batch cell update for Dataset rows
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0101
- Plan: PLAN-0019
- Phase: 3 Editing
- Priority: P2
- Size: M

## Objective

Studio can apply a rectangular paste or fill as one checked change.

## Scope

### In Scope

- `PATCH /api/datasets/{id}/rows/batch` with up to 500 cells across up to 100 rows, each row with its revision; all or nothing; per-cell issues returned on failure; one audit event with counts.
- Uses the writer lock, type and validation rules, unique checks.
- Returns the previous values of changed cells to the Studio caller (who has read) so TASK-0355 can offer one-step undo as another batch.
- Server-side by nature: no grid library replaces it, and it keeps the server the single place for checks (DEC-0101).

### Out Of Scope

- Workflow or token batch writes.

## Inputs

- Rows service and repository.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- DEC-0101 accepted (2026-11-13); TASK-0353 merged.

## Acceptance Criteria

- A batch with one stale row or one invalid cell changes nothing and reports the cell; a valid batch bumps each changed row once.

## Tests

- Service tests on both databases including concurrency.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Readiness gate passed. Started stacked on TASK-0353 to reuse its validation.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0345](../../artifacts/REV-0345-TASK-0354-dataset-batch-cell-update.md) and QA [QA-0345](../../artifacts/QA-0345-TASK-0354-dataset-batch-cell-update.md).

- 2026-11-14: Owner approved merging PR #412 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0354-dataset-batch-cell-update` from `develop` when implementation begins.
