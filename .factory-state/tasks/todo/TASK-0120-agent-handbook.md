# Task

## Metadata

- Project: superstep
- Task ID: TASK-0120
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0072
- Design IDs: none
- Architecture IDs: DEC-0063

## Objective

Document the Agent node in the handbook (en, vi) and update the pages that compare or list node types.

## Scope

### In Scope

- A handbook page for the Agent node (en, vi): when to use it rather than a fixed graph or a subgraph, the settings,
  the four tool sources, rounds and the limit, approval, the mock, the trace, exports, and a screenshot.
- Updates: the node reference, the MCP guide (an MCP tool in an agent vs the MCP node), the Human node / approvals
  page (agent approvals), the workflow tests page (the "tool called" check), the export pages, and the comparison
  pages' agent cells (`superstep-vs-visual-builders.md`, `superstep-vs-agent-frameworks.md`).
- Both navs (`mkdocs.yml`, `mkdocs.vi.yml`); README feature list; CHANGELOG Unreleased.

### Out Of Scope

- Code changes.

## Inputs

- REQ-0072, DEC-0063, the merged TASK-0116 to TASK-0119, `handbook/docs/{en,vi}/`, the glossary in
  `docs/ui-conventions.md` rule 10.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0072-agent-node.md`, `REQ-0069-superstep-comparison-pages.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Decisions: none
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0003-agent-node.md`

## Expected Outputs

- Handbook pages in en and vi with no stale claims about agents.

## Implementation Notes

- The comparison pages must only claim what is merged.

## Constraints

- Vietnamese wording follows the glossary; no emoji.

## Dependencies

- TASK-0116 to TASK-0119 merged.

## Acceptance Criteria

- Strict handbook builds (en, vi) pass with no issues; the new page is in both navs; links are valid.
- CHANGELOG Unreleased lists the Agent node.

## Validation Plan

- Handbook strict builds en and vi; `factory verify run --profile full`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-25: planned from REQ-0072 (CLAR-0003 answered).

## Handoff Notes

- Last task of REQ-0072.
