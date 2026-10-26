# Task

## Metadata

- Project: superstep
- Task ID: TASK-0135
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073
- Design IDs: none
- Architecture IDs: DEC-0066, DEC-0063

## Objective

Pass approvals inside a child up to the people who approve (DEC-0066 decision 6), and show the link between parent
and child runs in the API, the run page and the history (decision 8, runs part).

## Scope

### In Scope

- `ApprovalService` and the inbox: a child's request (Human node or Agent tool approval) carries the chain of
  workflow names from the top parent ("Support team › Refund desk"), in the inbox, Slack, Telegram and e-mail
  messages.
- Run API: `parent_run_id` and the children (`[{run_id, workflow_id, workflow_name, status, step}]`) on run details;
  a waiting parent's `waiting_for` child. SDKs (Python, TypeScript) read the new fields.
- Frontend: the run page shows "Called by <parent>" and, for a waiting parent, "Waiting for <child workflow>" with a
  link; the history marks child runs. en and vi strings with the same keys.
- Tests: approve and reject inside a child resume the child and then the parent; a deadline that expires in a child
  ends it and gives the parent an error result; access (a child run is readable by those who may read the parent).

### Out Of Scope

- The nested trace (TASK-0136).

## Inputs

- TASK-0134's child runs.
- `services/approval_service.py`, `services/inbox_service.py`, `services/approval_channels/`,
  `api/routes/runs.py`, `frontend/src/` run page and history, `sdk/python`, `sdk/typescript`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`, `REQ-0041-approval-deadlines-and-inbox.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: `DEC-0063-agent-node-expansion.md`, `DEC-0008-shadcn-ui-and-theme-tokens-only.md`
  (`docs/ui-conventions.md`), `DEC-0043-approvers-answer-in-studio.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- The "Refund desk" scenario of REQ-0073: both runs wait, the inbox shows "Support team › Refund desk", Approve
  finishes both.

## Implementation Notes

- The parent is never an approval itself; only the child's request appears.

## Constraints

- shadcn/ui and theme tokens; en and vi strings; API envelope; no migration beyond TASK-0134's.

## Dependencies

- TASK-0134.

## Acceptance Criteria

- pytest: approve, reject and deadline inside a child, each ending in the expected parent result; the inbox and a
  channel message carry both workflow names; run details list parent and children.
- vitest for the run page labels; e2e: a supervisor run waits, the inbox approval finishes both runs.

## Validation Plan

- Backend pytest, frontend lint and vitest, the e2e spec, SDK tests; `factory verify run --profile full`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).

## Handoff Notes

-
