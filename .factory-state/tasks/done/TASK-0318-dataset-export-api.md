# Task

## Metadata

- Project: superstep
- Task ID: TASK-0318
- Title: Export binding contract and connected adapters
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Export

## Objective

Run exported Python and TypeScript Dataset steps through a scoped Superstep API.

## Scope

Shared binding metadata, deployment-time configuration, connected adapter in both languages, external operations and schema checks.

## Inputs

Project exporters, Dataset node and Agent tool contracts, scoped tokens and write receipts.

## Expected Outputs

Generated connected adapters for Dataset nodes and Agent read tools, with shared wire format and documented errors.

## Dependencies

[TASK-0315](../done/TASK-0315-dataset-node-runtime.md), [TASK-0317](../done/TASK-0317-dataset-agent-tool.md)

## Acceptance Criteria

- Both generated projects execute live lookup, insert and upsert with scoped tokens.
- Missing settings, incompatible schemas and insufficient permissions fail explicitly.
- Retried writes send the same identity.
- Studio IDs, tokens and connection values are absent from generated source and default artifacts.

## Validation Plan

Execute exported Python and TypeScript fixtures against a local Superstep API, including revocation, drift, retries and Agent tool parity.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0303-TASK-0318-dataset-export-api.md)
- [QA](../../artifacts/QA-0303-TASK-0318-dataset-export-api.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0303. QA QA-0303.
- 2026-11-12: Created during owner-approved requirements planning.

- 2026-11-13: Started on the Dataset Agent tool stack at PR #373.

- 2026-11-13: Verified the generated Python and TypeScript projects against a scoped connected API and moved to review.

## Handoff Notes

Start from integrated develop on `factory/task-0318-dataset-export-api` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
