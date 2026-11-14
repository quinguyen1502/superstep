# Task

## Metadata

- Project: superstep
- Task ID: TASK-0352
- Title: Add multi-select and auto-number fields
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
- Priority: P2
- Size: M

## Objective

Datasets support multi-select values and server-assigned auto-numbers.

## Scope

### In Scope

- `multi_select`: array of declared options stored in the JSON row; operators `contains_any`, `contains_all`, `is_null`; CSV cells use `;` as the delimiter (owner-confirmed); not unique.
- `auto_number`: assigned under the writer lock from a per-dataset counter, unique, read-only, never reused; added to an existing dataset it backfills by created order.
- Node mapping, Agent tool schema, summaries, and filters per kind.
- Python and TypeScript export parity lands in TASK-0356 and TASK-0357; this task documents the contract in `docs/dataset-export.md`.

### Out Of Scope

- Option colors beyond theme tokens; user fields.

## Inputs

- TASK-0351 type plumbing.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- TASK-0351 merged.

## Acceptance Criteria

- Concurrent inserts get distinct auto-numbers on both databases; multi-select filters return the expected rows.

## Tests

- Concurrency tests; filter tests; CSV round trip.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): `;` delimiter confirmed.

- 2026-11-14: Readiness gate passed. Started stacked on scalar column types in PR #408.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0343](../../artifacts/REV-0343-TASK-0352-dataset-structured-field-types.md) and QA [QA-0343](../../artifacts/QA-0343-TASK-0352-dataset-structured-field-types.md).

- 2026-11-14: Owner approved merging PR #410 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0352-dataset-structured-field-types` from `develop` when implementation begins.
