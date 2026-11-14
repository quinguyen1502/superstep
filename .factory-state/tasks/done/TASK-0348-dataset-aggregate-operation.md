# Task

## Metadata

- Project: superstep
- Task ID: TASK-0348
- Title: Let Agents and workflows aggregate Dataset rows
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0101
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0019
- Phase: 3 Agent
- Priority: P1
- Size: M

## Objective

An Agent tool and the Dataset node can count, sum, average, or take min and max by filter, optionally grouped by one field, without loading rows into the model.

## Scope

### In Scope

- Operation `aggregate_rows`: functions as in TASK-0347, optional `group_by` one field, at most 20 groups returned, filter tree.
- Read grant required; Agent tool setting lets the author enable Aggregate separately from Find; trace shows the operation and group count without values beyond the returned aggregates.
- Allowed from the same entries as Find under DEC-0098.
- Python and TypeScript export parity lands in TASK-0356 and TASK-0357; this task documents the contract in `docs/dataset-export.md`.

### Out Of Scope

- External MCP exposure (REQ-0097 out of scope) and agent schema-changing tools.

## Inputs

- Summary engine from TASK-0347; Agent Dataset tool; PolarBase `server/src/features/mcp/servers/database` tool split as reference.

## Related Artifacts

- Requirements: [REQ-0101](../../artifacts/REQ-0101-datasets-phase-3.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0019](../../artifacts/PLAN-0019-datasets-phase-3.md)

## Dependencies

- TASK-0347 merged; REQ-0099 chain (TASK-0331) merged.

## Acceptance Criteria

- "How many open high-priority tickets per team?" is answered with one `aggregate_rows` call.
- A tool without Aggregate cannot call it; a write-only grant cannot call it.

## Tests

- Engine, Agent tool, and permission tests on both databases; public-entry test.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0101 and PLAN-0019.

- 2026-11-14: Readiness gate passed. Started stacked on the summary engine in PR #405.

- 2026-11-14: Implemented and ran targeted checks. Review [REV-0339](../../artifacts/REV-0339-TASK-0348-dataset-aggregate-operation.md) and QA [QA-0339](../../artifacts/QA-0339-TASK-0348-dataset-aggregate-operation.md).

- 2026-11-14: Owner approved merging PR #406 into develop after successful checks.

## Handoff Notes

- Use branch `factory/task-0348-dataset-aggregate-operation` from `develop` when implementation begins.
