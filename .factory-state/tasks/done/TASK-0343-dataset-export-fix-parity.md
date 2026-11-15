# Task

## Metadata

- Project: superstep
- Task ID: TASK-0343
- Title: Carry the Dataset fixes into Python and TypeScript exports
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0099
- Plan: PLAN-0018
- Phase: Export
- Priority: P1
- Size: M

## Objective

Exported projects follow the same write-only result, receipt, filter, and error rules as Studio.

## Scope

### In Scope

- Connected bindings: handle the identifier-only result and `DATASET_TOKEN_SCOPE`.
- Standalone SQLite and PostgreSQL: Agent tools without Find return identifiers only; no-op upsert keeps the revision; `superstep_dataset_receipts` stores identifiers only (setup migrates existing projects) and expires with a configurable window; null-safe `ne`; case-insensitive contains, search, and sort with the same fold as Studio.
- `docs/dataset-export.md` Python and TypeScript sections.

### Out Of Scope

- Phase 3 operators and field types (TASK-0356, TASK-0357).

## Inputs

- Export runtimes from TASK-0319, TASK-0320, TASK-0329, TASK-0330.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- TASK-0329 and TASK-0330 merged (phase 2 chain), and TASK-0332, TASK-0333, TASK-0334, TASK-0337 merged.

## Acceptance Criteria

- Generated Python and TypeScript projects pass the same write-only, receipt, filter, and token-scope cases on the Superstep API, SQLite, and PostgreSQL.
- Running setup twice on an existing project upgrades receipts without losing rows.

## Tests

- Export parity suites in both languages against a live local Superstep API, SQLite, and PostgreSQL.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

- 2026-11-14: Started on a branch containing the TASK-0333 and TASK-0337 heads. This branch depends on both PRs.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0334](../../artifacts/REV-0334-TASK-0343-dataset-export-fix-parity.md) and QA [QA-0334](../../artifacts/QA-0334-TASK-0343-dataset-export-fix-parity.md).

- 2026-11-14: Owner approved merging PR #400 into develop after the final checks pass.

## Handoff Notes

- Use branch `factory/task-0343-dataset-export-fix-parity` from `develop` when implementation begins.
