# Task

## Metadata

- Project: superstep
- Task ID: TASK-0118
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0072
- Design IDs: none (layout below; `docs/ui-conventions.md` rules apply)
- Architecture IDs: DEC-0063

## Objective

Let builders add and configure the Agent node in the editor, and show its rounds, tool calls and approvals in the run
trace and the chat.

## Scope

### In Scope

- Palette entry, canvas node (icon, label, a small "N tools" badge) and `node-types.ts` meta.
- `components/agent-settings.tsx` in the config panel:
  - credential and model (as the LLM node, models without tool calling marked);
  - system prompt and task prompt (template field editor);
  - max rounds, output field, optional steps field and history field;
  - the tool list: add a tool by source (MCP server and tool, built-in function, knowledge base and `top_k`, HTTP
    with method, URL, headers, body, credential and a parameters editor), name, description, a "needs approval"
    switch, reorder and remove;
  - the approval section reusing `human-approval-settings.tsx` and `human-deadline-settings.tsx`, shown when a tool
    needs approval.
- Run trace (`lib/trace.ts`, `run-trace.tsx`): steps of `A/__model` and `A/__tool` grouped under the Agent node by
  round; each tool call with arguments, a shortened result, duration, error, the approval wait and its answer; a
  "round limit reached" mark; usage summed.
- Chat (REQ-0048): the `full` step view shows the tool calls; `labels` shows "Agent › tool name".
- en+vi strings with identical keys; glossary rows (agent, tool call, round); `npm run lint:ui` rules.
- vitest for the trace grouping; e2e `frontend/e2e/agent-node.spec.ts` (vi and en): add the node, add two tools, run
  with the mock, see the rounds, approve a tool in the run panel.

### Out Of Scope

- Canvas tool nodes (CLAR-0003 Q1); editing arguments on approval (Q3).

## Inputs

- REQ-0072, DEC-0063, TASK-0116 trace events, `components/mcp-settings.tsx`, `retriever-settings.tsx`,
  `code-settings.tsx` (HTTP fields), `human-approval-settings.tsx`, `human-deadline-settings.tsx`,
  `components/editor/editor-config.tsx`, `editor-palette.tsx`, `canvas-nodes.tsx`, `lib/trace.ts`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0072-agent-node.md`, `REQ-0048-agent-chat.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Decisions: DEC-0008 (`docs/ui-conventions.md`), `DEC-0025-ui-only-delete-confirmation.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0003-agent-node.md`

## Expected Outputs

- The node can be built and debugged in the studio without editing JSON.

## Implementation Notes

- Removing a tool row edits the unsaved node settings, so it needs no typed-name confirmation (DEC-0025 covers
  stored records).
- API calls only through `lib/api.ts`; errors through `errorText` / `eventErrors`.

## Constraints

- shadcn/ui components and theme tokens only; no hard-coded colours or hand-set sizes (ui-conventions rules 10, 11).

## Dependencies

- TASK-0116 (node data shape and trace events). The approval display needs TASK-0117; if TASK-0117 is not merged,
  the e2e approval step lands with TASK-0117's merge.

## Acceptance Criteria

- The settings panel saves every field of REQ-0072; validator errors show on the node.
- The trace groups rounds and shows each tool call, result, error, approval and the limit mark; the chat `full` and
  `labels` views show the steps.
- `npm run build`, `npm test`, `npm run lint`, `npm run lint:ui` pass; e2e `agent-node.spec.ts` passes in vi and en,
  screenshots reviewed.

## Validation Plan

- `cd frontend && npm run build && npm test && npm run lint && npm run lint:ui && npm run e2e -- agent-node`;
  `factory verify run --profile full`.

## Assumptions

- The existing template field editor and approval settings components can be reused without changes to their
  props, or with small additions.

## Open Questions

- None.

## Activity Log

- 2026-10-25: planned from REQ-0072 (CLAR-0003 answered).
- 2026-10-25: started at the owner's request in parallel with TASK-0116, on `factory/task-0118-agent-editor-and-trace`,
  stacked on `factory/task-0116-agent-engine-loop` (PR #144, 9eac951). Its PR targets develop and contains #144's
  commits until #144 merges; then develop is merged in. REV-0108 follow-ups taken here: hide `agent:` fields in the
  trace; treat text from tool rounds as steps in the chat.
- 2026-10-25: implemented. Agent in the palette and canvas (`META.agent`, `--node-agent*` tokens light and dark,
  `DEFAULTS.agent`, `samples.agentPrompt`); `components/agent-settings.tsx` (credential with a warning for providers
  without tool calling, model, system and task prompts, max rounds, output, steps and history fields, tool cards for
  MCP / HTTP / built-in / knowledge base with name, description, parameters (HTTP), reorder, remove and "needs
  approval", and the Human approval and deadline settings when a tool needs approval); `lib/agent.ts`; trace rows of
  agent steps indented with the round, the tools called, the answer, the tool result and the limit mark, the
  `agent:` field hidden (`lib/trace.ts`, `run-trace.tsx`); chat steps: tool calls by name, model calls in `full` only,
  the reply stream keeps the last model call (`lib/chat.ts`, `chat_session_service.steps_of`); en/vi strings and
  glossary rows. Tests: `lib/__tests__/agent-trace.test.ts`, `test_chat_steps_show_tool_calls_by_name`,
  `e2e/agent-node.spec.ts` (vi light, en dark; screenshots reviewed). Checks run: tsc, vitest (103), lint, lint:ui,
  build, e2e agent-node + agent-chat + trace + mcp, pytest agent + chat sessions + layers.
- 2026-10-25: review fix (0572604): tool cards keep their own state when moved, unnamed parameters are skipped; e2e
  moves a tool. Validation: `factory verify run --profile full` passed every check except `python:backend:test`,
  whose only failures are the 6 environment tests (QA-0109). REV-0109 approved for QA; QA-0109 pass with follow-up.
  Moved to review; Draft PR #145 into develop (stacked on #144).
- 2026-10-25: PR #145 merged into develop (9ec4e98) with the owner's approval; moved to done by TASK-0120.

## Handoff Notes

- Stacked on TASK-0116 (#144). Review REV-0109, QA-0109. Next: owner review; `finish-pr` after #144 merges and CI is green.
- Validator errors show in the run panel's error list, naming the node (as for every node type); there is no per-node
  error badge on the canvas.
- The "needs approval" switch and the approval settings are saved now; the run pauses before such a call only with
  TASK-0117. Merge order: #144, TASK-0117, this task (or this task before TASK-0117 with the switch documented as
  not yet active).
