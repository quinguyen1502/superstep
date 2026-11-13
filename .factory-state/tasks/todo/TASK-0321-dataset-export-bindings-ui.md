# Task

## Metadata

- Project: superstep
- Task ID: TASK-0321
- Title: Project export binding UI and optional snapshots
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Export

## Objective

Choose a deployment backend for each dataset and optionally seed a standalone project.

## Scope

Project export dialog, per-binding backend choices, generated configuration, permission-checked snapshot creation and explicit restore.

## Inputs

Both standalone adapters, connected binding contract, project export and CSV limits.

## Expected Outputs

A guided export flow in both languages, generated README and environment templates, plus an optional seed artifact.

## Dependencies

[TASK-0316](../done/TASK-0316-dataset-node-editor.md), [TASK-0319](TASK-0319-dataset-export-python-standalone.md), [TASK-0320](TASK-0320-dataset-export-typescript-standalone.md)

## Acceptance Criteria

- A project can use mixed bindings and change backends at deployment without regenerating the graph.
- Default archives include no data or secrets.
- A snapshot requires explicit selection and read access and is bounded and disclosed in the UI.
- Restore checks schema and is safe to repeat without silently overwriting data.

## Validation Plan

Run export archive inspections and Playwright for mixed bindings, default export, snapshot selection and denied access. Restore the generated seed in both languages.

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

Start from integrated develop on `factory/task-0321-dataset-export-bindings-ui` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
