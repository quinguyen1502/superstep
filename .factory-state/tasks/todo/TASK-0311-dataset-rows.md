# Task

## Metadata

- Project: superstep
- Task ID: TASK-0311
- Title: Typed row CRUD, query and concurrency
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Studio

## Objective

Edit and query persistent rows with identical semantics on both Studio databases.

## Scope

Row models, validation, bounded projection and filtering, server sort/pagination, revisions and database-enforced unique keys.

## Inputs

Dataset schema contract and existing repository/session conventions.

## Expected Outputs

Authorized row endpoints, a portable query and upsert contract, and measured operational limits.

## Dependencies

[TASK-0310](../done/TASK-0310-dataset-schema.md)

## Acceptance Criteria

- Type coercion, nulls, defaults, filtering and ordering behave consistently on SQLite and PostgreSQL.
- Concurrent upserts for one key result in one row.
- Stale edits receive a conflict without overwriting newer data.
- A representative workload measures filtered page and lookup latency and records supported row, byte and query limits.

## Validation Plan

Run repository and API tests on SQLite and PostgreSQL, including simultaneous writes and a representative dataset benchmark.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-12: Created during owner-approved requirements planning.

## Handoff Notes

Start from integrated develop on `factory/task-0311-dataset-rows` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
