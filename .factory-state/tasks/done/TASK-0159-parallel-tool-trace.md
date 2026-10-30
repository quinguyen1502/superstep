# Task

## Metadata

- Project: superstep
- Task ID: TASK-0159
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-30
- Requirement IDs: REQ-0076
- Design IDs: none
- Architecture IDs: DEC-0069

## Objective

A builder can turn parallel tool calls off on one Agent node, and a round's calls show as overlapping bars under that node.

## Scope

### In Scope

- Agent node setting in `frontend/src/components/agent-settings.tsx`: a `Switch`, on when `parallel_tool_calls` is missing or true, bound to the node data. Strings in `frontend/src/locales/en.json` and `vi.json`, same keys. No literal UI text.
- Trace: `frontend/src/lib/trace.ts` and `frontend/src/components/run-trace.tsx`. `agentOf` matches `A/__tool/<n>` and `A/__join`, including under a subgraph id. Slots of one superstep start at the same offset. An Agent tool bar's width is that call's `agent.ms`.
- Vitest: three tool events with one `superstep` render three bars that share a start, the short call's bar is shorter, and `agentOf('ag/__tool/2')` and `agentOf('sub/ag/__join')` return the Agent id. A wave is not split into one fork per call by any UI change in this task. The checkpoints API already groups a superstep (TASK-0157). This task only checks the dialog still shows the rows the API returns.

### Out Of Scope

- Engine scheduling, the cap and the ledger (TASK-0157).
- Approvals and child resume (TASK-0158).
- Exports, handbook, e2e (TASK-0160, TASK-0161).
- A new status colour. The bars keep the existing primary, warning and destructive tokens.

## Inputs

- DEC-0069 decisions 1 and 8.
- TASK-0157's event shape: slot ids, shared `superstep`, `agent.ms` on each tool step.
- `frontend/src/components/agent-settings.tsx`, `frontend/src/lib/trace.ts`, `frontend/src/components/run-trace.tsx`, `frontend/src/lib/__tests__/agent-trace.test.ts`, `frontend/src/components/editor/time-travel-dialog.tsx`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`
- Decisions: `.factory-state/decisions/DEC-0008-shadcn-ui-and-theme-tokens-only.md`, `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`

## Expected Outputs

- The Agent config shows the switch, on by default. A round of three tool calls draws three overlapping bars under the Agent node.

## Implementation Notes

- Use the shadcn `Switch` already used for a tool's approval. Theme tokens only. Both locales, identical keys.
- A missing `parallel_tool_calls` is on. Saving an untouched agent may omit the field. Turning the switch off writes `false`.
- `buildTrace` must keep `superstep` from `node_finished`. The bar start for those spans is the start of the earliest span in that superstep, not each event's own `ts - duration`, when the events belong to one Agent wave.
- Width uses `agent.ms` for `agent.kind === 'tool'`. Other spans keep today's width.
- `agentOf` today is `/__(model|tool|exit)$`. Extend it. Update `agent-trace.test.ts`, which asserts the old helper.

## Constraints

- `docs/ui-conventions.md` (DEC-0008): shadcn components and theme tokens, no hard-coded colours.
- No new API, and no confirm-by-typing. This is not a delete.
- The API client stays `lib/api.ts` `api()`. No new user-facing error code.

## Dependencies

- TASK-0157 merged to `develop`, for the slot ids and the shared `superstep`.

## Acceptance Criteria

- The Agent settings render a switch. It is on when the field is missing, and turning it off stores `parallel_tool_calls: false`. The en and vi strings share one key. The component has no literal UI text.
- Vitest: three `agent_tool` events with the same `superstep` and `ms` of 100, 400 and 400 produce bars with one start. The 100 ms bar is shorter than the 400 ms bars.
- `agentOf('ag/__tool/2')` is `ag`, `agentOf('sub/ag/__join')` is `sub/ag`, and `agentOf('ag/__model')` stays `ag`.
- A checkpoint fixture with one wave is still one row in the time-travel dialog, not three.
- `cd frontend && npm test` and `cd frontend && npm run lint` pass.

## Validation Plan

- `cd frontend && npm test`
- `cd frontend && npm run lint`

## Assumptions

- The time-travel dialog lists API checkpoints as they are. TASK-0157 makes a wave one checkpoint, so this task does not add fork logic.
- Overlap is visible from event fixtures. A browser pass of a live run belongs to TASK-0161.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0076 (DEC-0069). Medium-task workflow. No design artifact: CLAR-0007 fixes the setting and the overlapping bars.
- 2026-10-30: delivered with TASK-0158, TASK-0160 and TASK-0161 on PR #213 (`69d55a2`). Review of that PR left no blockers after `b16c468`. QA: the bar test and the Support team e2e passed, and CI on `b16c468` was green. Owner merged. Moved to done.

## Handoff Notes

- The Agent setting `parallel_tool_calls: false` forces one call. Tool bars of one superstep share a start.
