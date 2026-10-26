# Task

## Metadata

- Project: superstep
- Task ID: TASK-0138
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073, REQ-0069
- Design IDs: none
- Architecture IDs: DEC-0066

## Objective

Document workflow tools and the supervisor pattern in the handbook (en, vi), update the comparison pages, and add the
CHANGELOG entry.

## Scope

### In Scope

- Agent node page: a "Workflows as tools" section (settings, parameters and results, child runs, approvals passed up,
  the nested trace) and the supervisor pattern with the "Support team" template; screenshots in en and vi.
- Runs and approvals pages: child runs and "called by"; the export page: workflow tools in all three exports.
- Comparison pages (REQ-0069): the "no multi-agent teams" gap becomes the supervisor pattern; hand-off stays listed
  as not supported.
- CHANGELOG `## Unreleased`.

### Out Of Scope

- Code changes.

## Inputs

- TASK-0133 to TASK-0137 as merged.
- `handbook/docs/{en,vi}/`, `CHANGELOG.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`,
  `.factory-state/artifacts/REQ-0069-superstep-comparison-pages.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: none
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- Handbook pages in en and vi that build in strict mode.

## Implementation Notes

- Follow the Vietnamese glossary rows added in TASK-0136.

## Constraints

- en and vi pages say the same things.

## Dependencies

- TASK-0135, TASK-0136, TASK-0137.

## Acceptance Criteria

- The handbook strict build (en, vi) passes; the screenshots match the merged UI; the CHANGELOG lists the feature.

## Validation Plan

- The handbook strict build as in CI; `factory verify run --profile full`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).

## Handoff Notes

-
