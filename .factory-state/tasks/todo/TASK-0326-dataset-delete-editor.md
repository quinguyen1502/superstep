# Task

## Metadata

- Project: superstep
- Task ID: TASK-0326
- Title: Add Delete row to the Dataset node editor
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0099
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0017
- Phase: Studio

## Objective

Let a workflow author configure Delete row without writing the binding by hand.

## Scope

### In Scope

- Dataset node operation Delete row.
- Mapping either a row id or one unique field from workflow state.
- English and Vietnamese labels, keyboard access, and validation for a missing target or a non-unique field.
- Playwright coverage on desktop for saving the binding and seeing a denied run when delete is not granted.

### Out Of Scope

- Agent tool settings, public-entry behavior, export generators, and the handbook.
- Changing the Studio grid delete confirmation.

## Inputs

- `frontend/src/components/datasets/dataset-node-settings.tsx` and the Dataset node runtime from TASK-0325.
- DES-0007 canvas rules and DEC-0098 argument shape.

## Related Artifacts

- Requirements: [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Decisions: [DEC-0098](../../decisions/DEC-0098-dataset-delete-and-public.md)
- Discovery:
- Clarifications:

## Expected Outputs

- Node editor, locale keys, and a browser test for a configured delete.

## Implementation Notes

- The editor offers one mode at a time: row id, or one unique key. It does not offer both arguments together.
- Follow the existing Dataset node field mapping rather than a new form pattern.

## Constraints

- shadcn/ui components and theme tokens only. Identical English and Vietnamese keys. No literal UI text in components.

## Dependencies

- [TASK-0325](../done/TASK-0325-dataset-delete-runtime.md)

## Acceptance Criteria

- An author can save Delete row by id and Delete row by one unique key without hand-written JSON.
- A non-unique field cannot be selected as the key. The saved binding runs through the TASK-0325 operation.
- The controls are keyboard reachable in both languages.

## Validation Plan

- Run the Dataset node editor Playwright spec, frontend tests, lint, and the locale parity test.
- Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Assumptions

- DES-0007 remains the layout direction. This task adds one operation to the existing node settings.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created during owner-approved planning of REQ-0099.

## Handoff Notes

- Start from `develop` after TASK-0325 merges, on `factory/task-0326-dataset-delete-editor`.
