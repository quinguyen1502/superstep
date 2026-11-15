# Task

## Metadata

- Project: superstep
- Task ID: TASK-0315
- Title: Dataset node runtime and atomic write receipts
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Runtime

## Objective

Execute Find rows, Get row, Insert row and Upsert row in authenticated workflows.

## Scope

Dataset engine port, validator/compiler integration, typed state mapping, grant enforcement, recovery-safe writes and explicit dry-run behavior.

## Inputs

Dataset query/write contract, grant policy, RunService ports and existing Effects/fencing.

## Expected Outputs

Dataset runtime execution and a reusable transactional idempotency contract.

## Dependencies

[TASK-0311](../done/TASK-0311-dataset-rows.md), [TASK-0314](../done/TASK-0314-dataset-access.md)

## Acceptance Criteria

- Configured lookups return only requested fields within limits.
- A worker that stops after commit and retries gets the previous result.
- Changed arguments under the same receipt identity are rejected, separate loop iterations write independently, and stale workers cannot mutate.
- Resume and nested runs honor their effective grants.
- Public paths are denied and test writes leave rows untouched.

## Validation Plan

Run engine and worker integration tests on SQLite and PostgreSQL, including concurrent recovery, revoke-on-resume and public entry paths.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)
- [Review](../../artifacts/REV-0300-TASK-0315-dataset-node-runtime.md)
- [QA](../../artifacts/QA-0300-TASK-0315-dataset-node-runtime.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0300. QA QA-0300.
- 2026-11-12: Created during owner-approved requirements planning.

- 2026-11-12: Started on an explicit stack over TASK-0314 (#370). Began with the transactional write receipt and worker lease check.

- 2026-11-12: SQLite receipt tests cover concurrent retry, the original response after a later edit, changed arguments, rollback after uniqueness failure, distinct logical steps, stale leases and revocation. The Dataset engine port, node dispatch, authoring checks and dry-run wiring remain.

- 2026-11-13: Wired the Dataset node into the engine, authoring and the run lifecycle. Verified WebSocket execution and recovery, with targeted checks passing.

## Handoff Notes

Start from integrated develop on `factory/task-0315-dataset-node-runtime` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.

Node data uses `dataset_id`, `operation`, `fields`, `arguments`, and `output_field`. Operation values are `find_rows`, `get_row`, `insert_row`, and `upsert_row`. Data arguments use the existing typed query/write contract.
