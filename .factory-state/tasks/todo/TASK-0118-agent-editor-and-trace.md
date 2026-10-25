# Task

## Metadata

- Project: superstep
- Task ID: TASK-0118
- Status: todo
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

## Handoff Notes

- Can start after TASK-0116 is merged, in parallel with TASK-0117.
