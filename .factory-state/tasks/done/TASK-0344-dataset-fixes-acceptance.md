# Task

## Metadata

- Project: superstep
- Task ID: TASK-0344
- Title: Accept the Dataset fixes and update the handbook
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Acceptance
- Priority: P1
- Size: S

## Objective

One acceptance pass proves the review findings are closed and the handbook states the corrected rules.

## Scope

### In Scope

- Re-run the review probes (write-only upsert, receipts after delete, search case, team roles, error codes) as automated regression tests.
- Refresh the review screenshots for the changed states in en/vi and both themes.
- English and Vietnamese handbook: write-only results, receipt retention, filter semantics, team management authority, unique-later, CSV fidelity, delete revisions.

### Out Of Scope

- Phase 3 work.

## Inputs

- `handbook/docs/en/guide/datasets.md`, `handbook/docs/vi/guide/datasets.md`; review notes.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- TASK-0332 to TASK-0343 merged.

## Acceptance Criteria

- Every row of the REQ-0100 findings table links to a passing test or screenshot in the QA artifact.
- Handbook en/vi anchors match; handbook build passes.

## Tests

- Regression suite; handbook build; Playwright smoke for Datasets.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

- 2026-11-14: Started acceptance on the integrated implementation heads from PRs #396 through #400. Final acceptance runs again after those PRs merge.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0335](../../artifacts/REV-0335-TASK-0344-dataset-fixes-acceptance.md) and QA [QA-0335](../../artifacts/QA-0335-TASK-0344-dataset-fixes-acceptance.md).

- 2026-11-14: Owner approved merging PR #401 into develop after the final checks pass.

## Handoff Notes

- Use branch `factory/task-0344-dataset-fixes-acceptance` from `develop` when implementation begins.
