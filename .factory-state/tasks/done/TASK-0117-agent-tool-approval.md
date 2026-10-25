# Task

## Metadata

- Project: superstep
- Task ID: TASK-0117
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0072
- Design IDs: none
- Architecture IDs: DEC-0063

## Objective

Pause before a tool call that needs approval, answer it through the Human node's approval path, and prove that agent
runs survive pauses and restarts without repeating a finished model or tool call.

## Scope

### In Scope

- `agent_tool` raises `Interrupt(<id>/__tool, prompt)` before a call to a tool with `approval: true`; the waiting
  event carries `tool` and `arguments`; the prompt names the tool and shows the arguments (en, vi).
- Expansion copies the agent's `approval` and `deadline` settings onto `<id>/__tool`; `ApprovalService.on_waiting`,
  the Approvals inbox, the run panel answer, Slack/Telegram and deadlines work unchanged.
- Resume: `approved` runs the call; `rejected` with the optional comment becomes the tool result "rejected by a
  reviewer" and the loop goes on (CLAR-0003 Q3, Q4); a deadline's `on_timeout` maps to the same two outcomes.
- Several calls in one round, one needing approval: the calls before it run, the run waits, the rest run after the
  answer.
- Workflow tests: test-case Human answers also answer agent approvals by node (`<agent id>`), so TASK-0119's template
  tests can approve.
- `backend/tests/test_agent_approval.py`; restart cases in `backend/tests/test_durable_restart.py` (paused at an agent
  approval; stopped between two rounds).

### Out Of Scope

- Editing the arguments before approval (CLAR-0003 Q3); the UI parts beyond what the existing inbox and run panel
  show (TASK-0118).

## Inputs

- REQ-0072, DEC-0063 (decision 7), `services/approval_service.py`, `engine/deadlines.py`, `engine/nodes.py` (Human
  resume), `services/workflow_test_service.py`, `backend/tests/test_durable_restart.py` (TASK-0115).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0072-agent-node.md`, `REQ-0041-approval-deadlines-and-inbox.md`,
  `REQ-0034-more-approval-channels.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Decisions: `DEC-0018-effectively-once.md`, `DEC-0044-workflow-test-runs.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0003-agent-node.md`

## Expected Outputs

- An agent run waits before an approved-only tool, shows in the inbox and channels, and continues after the answer.

## Implementation Notes

- The resume value is consumed once, as for Human nodes, so a later call to the same tool asks again.
- The waiting step's label is `Agent › tool` with the tool name, so the inbox names it clearly.

## Constraints

- Layers (DEC-0009); errors only through the catalog; en+vi strings for the prompt and any new text.

## Dependencies

- TASK-0116 (the expansion and `agent_tool`).
- TASK-0115 (PR #143) merged into develop, for the restart test harness and in-memory queue recovery.

## Acceptance Criteria

- pytest: approve runs the call once; reject gives the model "rejected by a reviewer" plus the comment; the inbox
  lists the waiting step with the tool and arguments; a Slack/Telegram approval message is sent when the agent has
  a channel (adapters faked as in the existing tests); a deadline with `on_timeout: reject` rejects.
- Restart tests: a run paused at an agent approval resumes after a restart; a run killed between two rounds
  continues and does not repeat the finished model call or tool call (counted by a test tool and respx call counts).
- A workflow test case with a Human answer for the agent passes in a test run.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`; `factory verify run --profile full`.

## Assumptions

- The existing response values `approved` / `rejected` and the comment field of the inbox are enough; no schema
  change.

## Open Questions

- None.

## Activity Log

- 2026-10-25: planned from REQ-0072 (CLAR-0003 answered).
- 2026-10-25: started on `factory/task-0117-agent-tool-approval`, stacked on TASK-0116 (`factory/task-0116-agent-engine-loop`,
  PR #144) with TASK-0115 (PR #143) merged in for the restart harness; the owner asked to continue the remaining work
  before #144 and #143 merge.
- 2026-10-25: implemented.
  - `agent_tool` raises `Interrupt` before a call to a tool with `approval: true`; the `run_waiting` event adds
    `label` ("Helper › send_refund"), `tool` and `arguments`; the prompt names the tool and shows the arguments (en, vi).
  - Answers: `approved` runs the call; `rejected` or any other text rejects it. A text reply is the comment: the model
    gets "Rejected by a reviewer: <text>". This keeps the existing answer shape (Approve, Reject, text reply).
  - A call with an unknown tool or invalid arguments fails without asking an approver.
  - The validator checks the Agent node's deadline when a tool needs approval.
  - In a chat, an Agent tool approval is always answered by a reviewer, never by the person chatting.
  - Test cases answer an Agent node's approvals under the Agent node's id; a draft case made from a run does the same.
  - Tests: `tests/test_agent_approval.py` (12) and two Agent cases in `tests/test_durable_restart.py`.
- 2026-10-25: validation (`factory verify run --profile full`: only the 6 known environment failures), review REV-0110
  (no blocking findings), QA QA-0110 (pass with follow-up); task to review.
- 2026-10-25: PR #146 merged into develop (e348e58) with the owner's approval; moved to done by TASK-0120.

## Handoff Notes

- Start after TASK-0116 is merged and #143 is in develop.
