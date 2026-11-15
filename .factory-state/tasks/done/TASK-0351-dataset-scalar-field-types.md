# Task

## Metadata

- Project: superstep
- Task ID: TASK-0351
- Title: Add long text, URL, and created and updated time fields
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Fields
- Priority: P1
- Size: M

## Objective

Datasets support long text, URL, and read-only created and updated time columns within the JSON row storage.

## Scope

### In Scope

- `long_text` (up to `MAX_TEXT`, multi-line editor, not unique), `url` (http or https, validated, opens in a new tab), `created_time` and `updated_time` (system columns derived from row metadata, read-only, filterable and sortable).
- CSV import and export, Dataset node mapping (system columns are not writable), Agent tool schema, filters and summaries per kind.
- Python and TypeScript export parity lands in TASK-0356 and TASK-0357; this task documents the contract in `docs/dataset-export.md`.

### Out Of Scope

- Formula, relation, attachment, JSON, and map fields.

## Inputs

- `core/dataset_types.py` `ColumnKind`, `normalize_cell`; schema service; grid editors.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- REQ-0100 TASK-0338 and TASK-0339 merged.

## Acceptance Criteria

- Each type validates, imports, exports, filters, and sorts on both databases; writing a system column is rejected with a schema error.

## Tests

- Type unit tests; API and CSV tests; Playwright editors.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Readiness gate passed. Started independently from develop.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0341](../../artifacts/REV-0341-TASK-0351-dataset-scalar-field-types.md) and QA [QA-0341](../../artifacts/QA-0341-TASK-0351-dataset-scalar-field-types.md).

- 2026-11-14: Owner approved merging PR #408 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0351-dataset-scalar-field-types` from `develop` when implementation begins.
