# Task

## Metadata

- Project: superstep
- Task ID: TASK-0314
- Title: Workflow grants and scoped Dataset API tokens
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Runtime

## Objective

Grant Dataset operations explicitly to a workflow or external deployment.

## Scope

Per-workflow read/write grants, scoped external token lifecycle, audit metadata, Access UI and authorization contract for runtime and connected export.

## Inputs

Existing Studio team policy, workflow shares, token handling and audit services.

## Expected Outputs

Dataset grant and token policy, service/API, audit records and Studio controls.

## Dependencies

[TASK-0310](../done/TASK-0310-dataset-schema.md), [TASK-0311](../done/TASK-0311-dataset-rows.md), [TASK-0312](TASK-0312-dataset-studio-grid.md)

## Acceptance Criteria

- Cross-team access, workflow-owner inheritance, unsaved grant impersonation, insufficient permissions and revoked grants/tokens are denied.
- Authorized grants and token rotation work.
- Tokens are displayed once, stored hashed and excluded from logs.
- Access UI uses typed confirmation to revoke.

## Validation Plan

Run API authorization matrix and Playwright for grant/token creation and revocation, plus log and audit assertions.

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

Start from integrated develop on `factory/task-0314-dataset-access` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
