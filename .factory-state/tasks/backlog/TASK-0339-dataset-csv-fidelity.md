# Task

## Metadata

- Project: superstep
- Task ID: TASK-0339
- Title: Keep CSV values intact and require revisions on Studio deletes
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P2
- Size: S

## Objective

CSV import keeps leading zeros and round-trips the formula guard, and Studio deletes always check the revision.

## Scope

### In Scope

- Type inference: values with a leading zero, a leading `+`, or more than 15 digits infer as text; the preview shows the inferred type and lets the user change it.
- Import strips the export formula guard: a leading `'` followed by `=`, `+`, `-`, `@`, tab, or carriage return is removed; other apostrophes stay.
- Studio row DELETE and dataset DELETE require `revision`; missing returns a validation error, stale returns the existing conflict code. Frontend always sends it.
- Changelog note for PAT clients.

### Out Of Scope

- Workflow `delete_row` (DEC-0098), Excel or JSON formats.

## Inputs

- `services/dataset_csv.py` inference and export guard; `api/routes/datasets.py` delete routes.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- None. Branch from `develop`.

## Acceptance Criteria

- Export then import of a dataset with `00123`, `+84901234567`, and `=SUM(A1)` gives identical values.
- DELETE without `revision` is rejected; a stale revision returns the conflict code.

## Tests

- CSV round-trip tests; inference tests; API tests for delete revisions; Playwright import preview with a changed type.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): required revision on Studio DELETE confirmed.

## Handoff Notes

- Use branch `factory/task-0339-dataset-csv-fidelity` from `develop` when implementation begins.
