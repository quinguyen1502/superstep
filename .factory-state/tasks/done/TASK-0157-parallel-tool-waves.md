# Task

## Metadata

- Project: superstep
- Task ID: TASK-0157
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-30
- Requirement IDs: REQ-0076
- Design IDs: none
- Architecture IDs: DEC-0069, DEC-0063, DEC-0018

## Objective

An Agent round runs its tool calls as one superstep of distinct slots, capped, ordered, and still effectively once. The node setting off keeps today's one-after-another behaviour.

## Scope

### In Scope

- `engine/agents.py`: slots `A/__tool/1` .. `A/__tool/8`, join `A/__join`, `Send` of only the slots in the wave, per-slot private keys, join once in the model's order, `step_budget` including joins. `agent_of_step` recognises a slot id.
- `engine/compiler.py`: the model router may return `Send`s; the compiled state declares the slot keys; the join is not a side effect.
- `core/config.py`: `agent_parallel_tools()` from `STUDIO_AGENT_PARALLEL_TOOLS` (default 4, invalid falls back to 4, clamped to 1..8). The setting off forces a wave of 1.
- Provider flag when the setting is off: OpenAI-compatible `parallel_tool_calls=False`, Anthropic `disable_parallel_tool_use`. `engine/llm.py` passes the flag through `invoke_tools`. The engine still runs one call at a time if the provider returns several.
- `mock_agent`: one call per tool whose name the latest user message contains as a whole token (underscores may be spaces); otherwise the single best tool, as today.
- Engine tests in `backend/tests/`: three calls overlap; cap 2 never has a third in flight; results are in the model's order; one call raises and the others finish; the same tool twice gets two ledger keys; the setting off is sequential even when the model returns three calls; a wave is one time-travel checkpoint and the join is the next; naming `order_desk` and `refund_desk` returns both, and the existing Support team prompts still call one desk.

### Out Of Scope

- Several children or an approval inside the wave (TASK-0158).
- The editor switch and the trace bars (TASK-0159).
- Exports (TASK-0160). Handbook, CHANGELOG, env-var docs, e2e (TASK-0161).

## Inputs

- DEC-0069 decisions 1 to 6 and 9.
- `backend/app/engine/agents.py`, `compiler.py`, `runtime.py`, `effects.py`, `llm.py`, `providers.py`.
- `backend/app/services/time_travel.py`.
- `backend/tests/test_agent_node.py` and `backend/app/engine/templates.py` (the Support team cases must stay one call).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`
- Decisions: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0018-effectively-once.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`
- Review: `.factory-state/artifacts/REV-0136-task-0157.md`
- QA: `.factory-state/artifacts/QA-0137-task-0157.md`

## Expected Outputs

- A mock model that asks for three calls runs them in one wave. The conversation lists the results in the model's order. With the setting off, the same three calls run one after another.

## Implementation Notes

- Do not `Send` the same node id twice in one wave. The ledger key is the slot id.
- A slot writes `agent:<id>#<slot>`, not the shared `agent:<id>` object. The join is what appends messages and `steps`.
- The join must run once. Unused slots must not be predecessors. A test with three calls and cap 4 is the proof.
- Overlap is measured with a tool that records its start and end under a lock and sleeps. `max(start) < min(end)` for the three calls when the cap is 4. With the cap at 2, a third start is not before one of the first two has ended.
- Tool errors stay inside the slot (`status: error`). They must not raise out of the node.
- `mock_agent` ids stay `mock_call_1`, `mock_call_2`, … in tool-list order.

## Constraints

- No new dependency. No migration. DEC-0009 layers: this task stays in `engine/` and `core/config.py`.
- `MAX_CALLS_PER_ROUND` remains 8. `max_rounds` still counts model calls.
- Existing one-call agent tests and the Support team template cases keep their results.

## Dependencies

- None. Start from `develop` after the owner confirms this set.

## Acceptance Criteria

- A model double that returns three calls runs them concurrently. The test shows overlapping start and end times, and the conversation lists the results in the model's order.
- With `STUDIO_AGENT_PARALLEL_TOOLS=2`, no more than two calls run at once. The third still runs, and the order is the model's order.
- A call that raises gives the model an error result. The other calls complete.
- Two calls of the same tool with the same arguments both run, and their idempotency keys differ.
- With `parallel_tool_calls` false, three calls run one after another, with no overlap. A provider double that ignores the flag still does not overlap.
- `time_travel.checkpoints` of a three-call wave has one fork whose `nodes` are the three slots, then a later checkpoint for the join. It does not offer a fork between two slots.
- The offline mock returns both desks when the message names `order_desk` and `refund_desk`, and one desk for "Where is my order B200?".
- `cd backend && .venv/bin/python -m pytest -q` passes, including `tests/test_layers.py`.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`

## Assumptions

- A missing `parallel_tool_calls` means on. Saved agents change speed, which is the owner's default.
- The cap is per round, not a global semaphore across runs.
- The join between two waves is a fork point. Only calls that shared a superstep are kept in one checkpoint.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0076 (DEC-0069). Medium-task workflow.
- 2026-10-27: owner confirmed the set. Branch `factory/task-0157-parallel-tool-waves` from `develop` at `4cd0dc6`. Moved to doing. No source edited.
- 2026-10-27: implemented the wave, the cap, the provider flag, and the mock. `cd backend && .venv/bin/python -m pytest -q` — 781 passed, 57 skipped.
- 2026-10-27: moved to review. Draft PR https://github.com/quinguyen1502/superstep/pull/206 against `develop`.
- 2026-10-27: REV-0136. Approved for QA. No blocking findings. `roadmap.md` conflicts with `origin/develop` and is resolved on the later rebase.
- 2026-10-27: QA-0137. Pass with follow-up. `cd backend && .venv/bin/python -m pytest -q` on `2a41b76` — 781 passed, 57 skipped. No acceptance criterion failed. The task stays in review.
- 2026-10-27: owner asked to finish the PR. Moved to done. REV-0136 approved for QA. QA-0137 passed with follow-up. Not merged.
- 2026-10-30: merged in PR #206. TASK-0158 to TASK-0161 are done in PR #213.

## Handoff Notes

- A round's calls are slots `A/__tool/1` .. `A/__tool/8` in one superstep. `A/__join` writes the tool messages in the model's order. Each slot is its own ledger key.
- `parallel_tool_calls: false` forces a wave of one and sends the provider flag. A model that still returns several calls is still run one at a time.
- The export still emits one sequential tool node. `same_run` maps slot ids onto that name and skips the join. TASK-0160 replaces the export.
- A slot that raises `Interrupt` can stop a sibling that has not started yet. Siblings that already finished are ledgered and are not repeated on resume. Making every other call finish before the pause is TASK-0158.
- The trace still keys off `ag/__tool`. Live bars and `agentOf` for slot ids are TASK-0159.
- TASK-0158, TASK-0159 and TASK-0160 start after this task is merged.
