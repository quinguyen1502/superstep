# Task

## Metadata

- Project: superstep
- Task ID: TASK-0327
- Title: Let an Agent insert and upsert dataset rows
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Runtime

## Objective

Allow an Agent tool to insert and upsert only the fields and operations configured for it.

## Scope

### In Scope

- Agent tool settings for a combination of Find rows, Insert row, and Upsert row. Delete row is not offered.
- Model-facing parameters that expose only the selected operations, fields, and filter operators.
- Insert and upsert through the workflow write grant, with the existing type, unique-key, row-size, and receipt rules.
- A stable receipt identity per logical tool call. A distinct call in the same run is a new write.
- Trace outcome and count without an extra copy of the row values.
- English and Vietnamese settings, and Playwright for a read-only tool and a write tool.

### Out Of Scope

- `allow_delete`, `delete_row`, the public-entry policy change, and standalone export.
- Raising the current Agent row and filter limits.

## Inputs

- `dataset_nodes.agent_binding`, `frontend/src/components/datasets/dataset-agent-settings.tsx`, and the Agent tool runner.
- Existing read-only Dataset tool tests.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Configurable Agent writes, settings UI, and tests for success, rejection, replay, and revocation.

## Implementation Notes

- A tool with only Find rows must still reject insert and upsert.
- Upsert requires a selected unique key. A unique value owned by another row returns `DATASET_UNIQUE_CONFLICT` and does not change that row.
- Public runs remain denied until TASK-0328. Cover writes from Studio Run and the simulated test path.

## Constraints

- Backend layers in `docs/backend-architecture.md`. shadcn/ui and identical locale keys.
- Audit and traces do not record cell values or secrets.

## Dependencies

- None. Branch from `develop`. The write grant already exists.

## Acceptance Criteria

- An Agent configured for insert and upsert writes only its allowed fields, and the row appears in Studio.
- The same tool rejects a field or an operation that was not configured. A read-only tool still cannot write.
- A retried call returns the original result. A later call in the run can write again. Revocation applies to the next call.
- A test run does not change stored rows. The trace shows the outcome and count without a second copy of the values.

## Validation Plan

- Run the Dataset Agent tool, runtime, layer, and API-envelope tests on SQLite and PostgreSQL.
- Run the Agent tool Playwright spec, frontend tests, and locale parity.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- Receipt identity follows DEC-0098 and REQ-0099. The task chooses the stable key inside the existing receipt store.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.

## Handoff Notes

- This task may start beside TASK-0324. Use `factory/task-0327-dataset-agent-write` from `develop`. Do not mix the two branches.
