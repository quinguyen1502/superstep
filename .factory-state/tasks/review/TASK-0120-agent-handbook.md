# Task

## Metadata

- Project: superstep
- Task ID: TASK-0120
- Status: review
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
- 2026-10-25: started on `factory/task-0120-agent-handbook` from develop 65ed3bb (TASK-0116 to TASK-0119 merged).
- 2026-10-25: implemented.
  - New handbook page `guide/agent.md` (en, vi): when to use it, settings, the four tool sources, rounds and the
    limit, approval, the mock, the trace, tests, the template, exports and errors. Three screenshots come from a new
    `agent <lang>` test in `e2e/handbook.spec.ts` (`HANDBOOK_SHOTS=1 npm run e2e -- handbook -g agent`).
  - Updated pages (en, vi): nodes, guide index, MCP (MCP node or Agent node), templates, Python export (an Agent
    node; the TypeScript refusal), human approval, tests (the "Tool called" check), traces, chat, and the three
    comparison pages.
  - Updated elsewhere: both navs, the README feature lists (14 node types, Agent node) and CHANGELOG Unreleased.
  - TASK-0119 follow-up fix: the Support agent template's gallery name and description in both locales, with a test
    that every built-in has them.
  - TASK-0115 to TASK-0119 moved to done (their PRs merged).
- 2026-10-25: validation (strict builds en and vi; `factory verify run --profile full`: only the 6 known environment
  failures), review REV-0112 (no blocking findings), QA QA-0112 (pass); task to review.

## Handoff Notes

- Last task of REQ-0072.
