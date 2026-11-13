# Task

## Metadata

- Project: superstep
- Task ID: TASK-0353
- Title: Add per-column validation rules and display formats
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Fields
- Priority: P2
- Size: M

## Objective

Managers set validation rules and display formats per column, and every writer enforces the rules.

## Scope

### In Scope

- Rules: text min and max length, number min and max and integer only, date and datetime min and max, email allowed domains.
- Enforced for Studio edits, CSV import (per-row issues), Dataset node, Agent tool, tokens; a new rule on a dataset with violating rows is refused with the count and sample rows.
- Display formats: number decimals, thousands separator, percent, currency code; date format presets; display only, stored values unchanged.
- Python and TypeScript export parity lands in TASK-0356 and TASK-0357; this task documents the contract in `docs/dataset-export.md`.

### Out Of Scope

- Regular expression rules (open question); conditional formatting.

## Inputs

- Schema service; CSV issue list from TASK-0340; PolarBase field validation as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- REQ-0100 TASK-0338 and TASK-0340 merged; TASK-0351 merged.

## Acceptance Criteria

- A rule violation returns `DATASET_VALUE_INVALID` naming the rule from every writer; formats render in en/vi locales.

## Tests

- Rule tests per writer; Playwright schema editor and formatted grid.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- Allow regular expression rules (not recommended; risk of slow patterns).

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

## Handoff Notes

- Use branch `factory/task-0353-dataset-validation-formats` from `develop` when implementation begins.
