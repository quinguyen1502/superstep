# Task

## Metadata

- Project: superstep
- Task ID: TASK-0138
- Status: done
- 2026-10-27: PR #182 merged into develop (3c835fa) with the owner's approval ("Ok làm đi") after CI passed; moved to done.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-27
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
- 2026-10-26: started on `factory/task-0138-workflow-tool-handbook`, stacked on TASK-0137 (PR #181). The owner asked for
  this order ("Làm tiếp dãy task, screenshots cho tôi xem rồi tới task cuối là handbook"); the e2e screenshots of
  TASK-0135 to TASK-0137 were sent in chat first.
- 2026-10-26: written.
  - Agent node page (en, vi):
    - the "Another workflow" tool source, a row in "When to use it", and a "Workflows as tools" section (the
      supervisor pattern, child runs, waiting, approvals passed up, trace, limits);
    - test runs of workflow tools, the Support team template, workflow tools in the exports, and the errors table
      (`WORKFLOW_TOOL_TOO_DEEP`).
  - Templates page (Support team), approvals page ("Approvals inside a called workflow"), Export to Python (the tool
    function), public API (`waiting.child_run_id`, `parent_run_id`), API reference (`GET /api/runs/{id}`).
  - Comparison pages (en, vi):
    - the "one agent, not a team" text now describes the supervisor pattern; hand-offs are still not supported;
    - the out-of-date "no TypeScript export of it yet" (fixed in TASK-0125) is gone.
  - CHANGELOG Unreleased › Added.
  - Screenshots from a new `handbook.spec.ts` test "workflow tools" (en, vi): the tool card, a run with the order
    desk's steps under the call, and the refund desk's approval on the Approvals page.
  - A UI fix the screenshots showed: after a run that waited for its child moved on, the Agent node on the canvas
    still said "waiting". `openRun` now clears the waiting marks of a run that is no longer waiting
    (`use-studio.ts`).

## Validation Results

- See QA-0122.

## Review And QA

- Review: REV-0122. QA: QA-0122.

## Handoff Notes

- REQ-0073 is done once PRs #177, #178, #179, #180, #181 and this one are merged; then mark the requirement Done.
