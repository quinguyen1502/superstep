# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0069
- Status: Accepted. The owner answered CLAR-0007 on 2026-10-27 with the recommended option for every question ("Trả lời CLAR-0006 đến CLAR-0009 theo đề xuất, rồi merge #200"). This record is the graph those answers run on.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Related Requirements: REQ-0076 (CLAR-0007), REQ-0072, REQ-0073
- Related Architecture:
  - DEC-0009 (layers)
  - DEC-0018 (effectively-once; parallel branches already share a superstep checkpoint)
  - DEC-0063 (Agent expansion; decisions 1 and 3 are amended here)
  - DEC-0066 (a workflow tool is a child run the tool step waits for)
- Related Tasks: TASK-0157, TASK-0158, TASK-0159, TASK-0160, TASK-0161

## Context

- REQ-0076 runs the tool calls of one Agent round at the same time. Each call keeps its own step, ledger entry and idempotency key. A pause, a crash or a restart repeats at most the calls that had not finished. The owner chose: on by default with a per-node switch, a cap of 4 from `STUDIO_AGENT_PARALLEL_TOOLS`, one approval per call, failures that do not cancel the rest, and concurrent exports.
- DEC-0063 expands an Agent node `A` into `A` → `A/__model` ⇄ `A/__tool` → `A/__exit`. `A/__tool` takes `pending[0]` and loops to itself, so a round takes the sum of its calls. The ledger key is `(run, node id, iteration)`. One node id shared by several calls in one superstep would give them one key.
- The runtime already checkpoints a superstep of several nodes as `{nodes, state, counts}` and resumes all of them together. Finished siblings come back from the ledger (DEC-0018). Time travel groups `node_finished` events that share a `superstep` into one fork (`services/time_travel.py`).
- A workflow tool raises `AwaitChild`, which is an `Interrupt`. `RunService.resume_parent` resumes the parent when the one child in `checkpoint.wait.run_id` has settled. `ApprovalRepository.add_wait` closes any other open wait of the same run, because a run has waited at one node.
- The trace bar already places a span at `end - duration`. A wave needs one shared start and each call's own duration (`agent.ms`), drawn under the Agent node.
- No separate design artifact. REQ-0076 and CLAR-0007 already fix the setting, the cap, the trace and the exports. The designer step of the medium-task workflow is skipped for that reason. The medium-task workflow is the one used: one requirement, the clarification is answered, and the work crosses the engine, the run service, the trace and the exports. It is not a new product surface, so the large-task workflow is not used.

## Decision

1. **The setting.** An Agent node has `parallel_tool_calls`, default on. A missing value is on, so workflows saved before this decision run in parallel. Off asks providers that support it for one call at a time, and the engine runs the calls one after another even when the provider still returns several. OpenAI-compatible `bind_tools` gets `parallel_tool_calls=False`. Anthropic's Messages request gets `disable_parallel_tool_use`. Other providers are unchanged. The engine is the guarantee, not the provider flag.
2. **The cap.** `config.agent_parallel_tools()` reads `STUDIO_AGENT_PARALLEL_TOOLS`, default 4, clamped to `1..MAX_CALLS_PER_ROUND` (8). A missing or invalid value is 4. The node setting off forces a wave of 1, whatever the variable says. The cap is per round of one Agent node, not a process-wide limit. `MAX_CALLS_PER_ROUND` still refuses calls beyond 8 with an error result, as in DEC-0063 decision 8. `max_rounds` still counts model calls, not tool calls.
3. **One wave is one superstep of distinct slots.** `expand` replaces the looping `A/__tool` with slots `A/__tool/1` .. `A/__tool/8`, type `agent_tool`, and a join `A/__join`, type `agent_join`. The join is not a side effect. After `A/__model`, no pending calls go to `A/__exit`. Otherwise the router returns `langgraph.types.Send` to the first `min(len(pending), cap)` slots only. Unused slots are not predecessors of the join. Each slot reads the call it was sent and writes a private key of its own (`agent:A#<slot>`), never the shared `agent:A` object. Those keys are declared only on the compiled state, like `agent:A`. The join runs once, after every slot of that wave has finished or paused, appends tool messages in the model's `tool_calls` order, drops the finished calls from `pending`, and routes to the next wave or back to `A/__model`. `step_budget` counts the join as well as the slots, so a round at cap 1 still fits the recursion limit.
4. **Effectively once per call.** Each slot is its own node id, so the ledger key and the idempotency key stay `(run, slot id, iteration)`. Two calls of the same tool in one round get different keys, including when the arguments match. The child key stays `effects.key(slot)#call id` (DEC-0066). A wave that is entered again returns the ledger result of a slot that already finished, and does not call the tool or start the child again. A crash mid-wave repeats at most the slots that had not finished.
5. **Checkpoints and time travel.** The slots of one wave share one `superstep` number, so time travel offers one fork for the state before that wave, not one fork per call. The join is the next superstep: forking it continues with the calls still in `pending`, and the calls already written into the conversation are not run again. A round that the cap splits into two waves therefore has a fork between the waves. That fork is after a finished wave, not between two calls that ran together.
6. **Failures.** A call that raises becomes an error tool result inside its slot, as today. The other slots of the wave finish. The model receives every result, in its order.
7. **Waiting is per call, and the wave resumes once.** A slot that needs approval raises `Interrupt` for itself. A workflow slot calls `start_child` once and raises `AwaitChild`. The checkpoint's `nodes` are the whole wave, so a resume re-enters every slot and the ledger supplies the ones that finished. `checkpoint.waits` lists what is still open: `{kind: "approval", node}` and `{kind: "child", run_id}`. One child and no approval may keep today's `checkpoint.wait = {kind: "child", run_id}` so a single child resumes as it does now. `resume_parent` enqueues one resume of the parent only when every child in the wave has settled and no approval is still open. A second settle does not enqueue a second job. An approval answer, including a deadline's `on_timeout`, resolves only that slot. `add_wait` must not close an open wait of a different node in the same run. The inbox, the channels and the deadlines stay one request per call. Cancelling the run cancels every running or waiting child of the wave. A late child of a run that is no longer waiting does not resume it.
8. **The trace.** `node_finished` of the slots in a wave carries the same `superstep`. The timeline draws those bars from one start. The width of an Agent tool bar is that call's own `ms`, so a short call ends before a long one beside it. `agentOf` treats `A/__tool/<n>` and `A/__join` as steps of `A`. The canvas stays one node.
9. **The offline mock.** `mock_agent` still calls the single best tool, except when the latest user message names two or more of the node's tool names (the `name`, or that name with underscores written as spaces) as whole tokens. Then it returns one call per named tool, in the tool list's order. Existing template prompts do not name both `order_desk` and `refund_desk`, so their cases stay one call.
10. **Exports.** The Python export, the LangGraph project export and the TypeScript export run a round's calls concurrently when the setting is on, and one after another when it is off. The exported cap is 4, overridable by `STUDIO_AGENT_PARALLEL_TOOLS` in the process that runs the file. They do not use `create_react_agent`. Results are returned to the model in the model's order.

## Alternatives Considered

- **Several `Send`s to one `A/__tool` node.** One node id gives every call in the wave the same ledger key, so a retry cannot tell a finished call from one that never started.
- **Keep the sequential loop and only overlap the HTTP client.** Workflow tools, approvals and restart recovery would still run one call at a time, which is the case REQ-0076 is for.
- **A static fan-in of all eight slots.** The join would wait for slots the wave never started.
- **One approval for the whole round.** CLAR-0007 rejected it. It needs a new approval shape, and a rejection would cover calls that should still run.
- **Hide every fork until the round has finished.** A wave boundary is a real checkpoint. Hiding it would make a long second wave impossible to fork, and it is not required. The requirement forbids a fork between calls that ran in parallel.

## Impacts

- DEC-0063 decisions 1 and 3 are amended as above. Decisions 2 and 4 through 7 and 9 still hold. Decision 8 holds, with the join steps added to `step_budget`.
- No new dependency and no migration. Several open `approval_waits` rows for one run are allowed by the table; only `add_wait` assumed one.
- `agent_of_step` and the trace's `agentOf` must recognise a slot id, or approvals and the indented trace miss the Agent node.
- Operator docs gain `STUDIO_AGENT_PARALLEL_TOOLS` (`docs/deploy/env-vars.md` and `env-vars.vi.md`).

## Risks

- LangGraph's barrier semantics differ by version. TASK-0157 has to prove the join runs once, unused slots do not block it, and two calls overlap. The invariant is the test, not an assumption about fan-in.
- A provider that ignores the disable flag can still return several calls. The engine runs them one by one when the setting is off.
- Parallel slots write the ledger from the same superstep. Parallel branches already do that. A race that the branch tests do not catch belongs to TASK-0157, not a new locking design.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-10-27
- Scope And Limits: The CLAR-0007 answers. The slot and join graph is the planning choice that makes those answers checkpoint. The owner confirmed the task set on 2026-10-27 and started TASK-0157.

## Review Or Revisit Trigger

- A model round regularly needs more than 8 calls, or the per-round cap is not enough to protect a tool server.
- LangGraph grows a first-class parallel tool node whose tasks have their own ledger keys. Revisit the slots then.
