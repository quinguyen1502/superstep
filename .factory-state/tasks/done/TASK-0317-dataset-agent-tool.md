# Task

## Metadata

- Project: superstep
- Task ID: TASK-0317
- Title: Read-only Dataset tool for Agents
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

Allow an Agent to retrieve configured Dataset fields through structured filters.

## Scope

Per-binding tool configuration, fixed read operations, selected output fields, bounded results and trace outcomes.

## Inputs

Dataset service/port and Agent tool registration, configuration and trace conventions.

## Expected Outputs

Read-only Dataset tool plus its editor configuration and run trace support.

## Dependencies

[TASK-0315](../done/TASK-0315-dataset-node-runtime.md), [TASK-0316](../done/TASK-0316-dataset-node-editor.md)

## Acceptance Criteria

- An Agent can query only configured datasets, fields and allowed operators.
- Write attempts and unauthorized field requests fail.
- Revocation affects later tool calls.
- Trace shows tool identity, outcome and count without an extra copy of values.

## Validation Plan

Run Agent tool integration, input limit and permissions tests, plus Playwright for tool setup and trace.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0302-TASK-0317-dataset-agent-tool.md)
- [QA](../../artifacts/QA-0302-TASK-0317-dataset-agent-tool.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0302. QA QA-0302.
- 2026-11-12: Created during owner-approved requirements planning.

- 2026-11-13: Started on the Dataset editor stack at PR #372.

- 2026-11-13: Implemented the read-only tool, checked the permission boundaries in live workflow runs, and moved to review.

## Handoff Notes

Start from integrated develop on `factory/task-0317-dataset-agent-tool` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
