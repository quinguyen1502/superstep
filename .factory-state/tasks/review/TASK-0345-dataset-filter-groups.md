# Task

## Metadata

- Project: superstep
- Task ID: TASK-0345
- Title: Add nested AND/OR filter groups and new Dataset operators
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Query
- Priority: P1
- Size: M

## Objective

Dataset queries accept a filter tree of AND/OR groups and the operators in, not in, and does not contain, through the API, the Dataset node, and the Agent tool.

## Scope

### In Scope

- Filter tree contract: `{type: group, conjunction: and|or, children: [...]}` and `{type: rule, field, op, value}`; depth at most 3, at most 20 rules; the flat `filters` + `filter_mode` form stays accepted and maps to one group.
- Operators `in`, `not_in` (at most 50 values, typed), `not_contains` (case-insensitive, null-safe), on the kinds that support them.
- Engine and repository compile the tree with the TASK-0334 semantics on SQLite and PostgreSQL; unique `eq`/`in` use the key index.
- Dataset node: mapped values inside groups; validation names the group and rule. Agent tool: allowed operators include the new ones; the model-facing schema stays bounded.
- Python and TypeScript export parity lands in TASK-0356 and TASK-0357; this task documents the contract in `docs/dataset-export.md`.

### Out Of Scope

- The filter builder UI (TASK-0346); saved views (REQ-0097 out of scope).

## Inputs

- `core/dataset_types.py` operators; `repositories/dataset_rows.py` `_predicate`; PolarBase `client/src/app/shared/field-system/filter/models.ts` and `server/src/features/agent/agents/database/schemas/where-filter.schema.ts` as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- REQ-0100 TASK-0334 merged.

## Acceptance Criteria

- `(status in [open, pending]) AND (priority = high OR csat < 3)` returns the same rows on both databases and through API, node, and Agent tool.
- Trees over the limits return a validation error naming the limit.
- Existing flat filters in saved workflows keep working unchanged.

## Tests

- Tree compiler unit tests; parametrized SQLite and PostgreSQL tests; node and Agent tool tests; backward compatibility test with saved workflows.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Started on top of the lifecycle reconciliation in PR #402.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0336](../../artifacts/REV-0336-TASK-0345-dataset-filter-groups.md) and QA [QA-0336](../../artifacts/QA-0336-TASK-0345-dataset-filter-groups.md).

## Handoff Notes

- Use branch `factory/task-0345-dataset-filter-groups` from `develop` when implementation begins.
