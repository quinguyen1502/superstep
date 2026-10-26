# Task

## Metadata

- Project: superstep
- Task ID: TASK-0136
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073
- Design IDs: none (follows the Agent tool cards of TASK-0118)
- Architecture IDs: DEC-0066, DEC-0063

## Objective

Configure workflow tools in the Agent node's settings, and show a call's child steps nested under it in the studio
trace and the chat's `full` view, with a link to the child run (DEC-0066 decision 8).

## Scope

### In Scope

- Agent tool card for the `workflow` source: a workflow picker (workflows the user may read, not the current one),
  name and description, input and output field choices from the child's state fields, an "Open workflow" link.
- Trace: under a workflow tool call, the child's steps fetched from the run API, grouped like subgraph steps, with
  duration, usage and the child's status; a link to the child run. The same in the chat's `full` view.
- en and vi strings with the same keys; glossary rows for "workflow tool" and "child run" (`docs/glossary` or the
  locale glossary used by `locales.test.ts`).
- e2e: add a workflow tool to an Agent node, save, run with the mock, see the nested steps and open the child run.

### Out Of Scope

- Approval and run-page labels (TASK-0135).

## Inputs

- TASK-0133 settings, TASK-0134 child runs (`child_run_id` on `node_finished`).
- `frontend/src/components/` Agent settings and trace (TASK-0118), chat `full` view (REQ-0048), `lib/api.ts`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`, `REQ-0048-agent-chat.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: `DEC-0008-shadcn-ui-and-theme-tokens-only.md` (`docs/ui-conventions.md`),
  `DEC-0063-agent-node-expansion.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- A builder can set up "Support team" in the editor and read the specialists' steps in its trace.

## Implementation Notes

- Fetch the child's events once per expanded call; a child still running shows its status and the link only.

## Constraints

- shadcn/ui components and theme tokens only; `docs/ui-conventions.md` checklist; API through `lib/api.ts`.

## Dependencies

- TASK-0134. Can run alongside TASK-0135 (different files, except the shared locales).

## Acceptance Criteria

- vitest for the tool card and the nested trace; the locale checks pass.
- e2e (en and vi) as in scope; screenshots in the QA record.

## Validation Plan

- `cd frontend && npm run lint && npx tsc -b && npx vitest run`; the e2e spec; `factory verify run --profile full`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).

## Handoff Notes

-
