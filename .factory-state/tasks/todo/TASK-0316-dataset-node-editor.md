# Task

## Metadata

- Project: superstep
- Task ID: TASK-0316
- Title: Dataset node palette and mapping editor
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

Configure and test a Dataset node on the workflow canvas.

## Scope

Palette entry, binding picker, operation-specific forms, input/output mapping, validation and workflow rebind UX.

## Inputs

Dataset node config contract, schema/grant APIs and existing editor components.

## Expected Outputs

Dataset node config, human-readable validation and portable workflow reference handling.

## Dependencies

[TASK-0312](../done/TASK-0312-dataset-studio-grid.md), [TASK-0314](../done/TASK-0314-dataset-access.md), [TASK-0315](TASK-0315-dataset-node-runtime.md)

## Acceptance Criteria

- A user can configure lookup and upsert without writing SQL or JSON by hand.
- Renamed display labels preserve mappings.
- Missing fields, revoked bindings and non-unique upsert keys show actionable feedback.
- Importing a workflow with missing dataset references prompts rebinding, and the dry-run state is visible.

## Validation Plan

Run frontend validation, lint and build, plus Playwright for configure, rebind, test and authenticated run.

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

Start from integrated develop on `factory/task-0316-dataset-node-editor` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
