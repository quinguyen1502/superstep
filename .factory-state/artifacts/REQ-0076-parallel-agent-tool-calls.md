# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0076
- Status: Accepted on 2026-10-27 with the CLAR-0007 answers (all recommended options). Planned on 2026-10-27 (DEC-0069, TASK-0157 to TASK-0161).
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Source: owner request in chat on 2026-10-27 ("3 hướng có thể làm thì bạn viết REQ trước đi"), from what REQ-0073
  left out: "A round's tool calls still run one after another".

## Summary

- When the model asks for several tool calls in one round, an Agent node runs them **at the same time**. The round
  ends when every call has a result, and the model gets the results in the order it asked for them.
- Each call keeps what DEC-0063 gives it today:
  - its own step;
  - its own checkpoint;
  - its own side-effect ledger entry and idempotency key;
  - its own approval.
- So a pause, a crash or a restart still repeats at most the calls that had not finished.
- Workflow tools benefit the most. A supervisor that asks two desks starts both child runs at once and waits for both.

## Owner Decisions

The owner answered CLAR-0007 on 2026-10-27 with the recommended option for every question ("Trả lời CLAR-0006 đến
CLAR-0009 theo đề xuất, rồi merge #200").

1. **Default**: on for every Agent node, with a per-node setting to turn it off. Off asks providers for one call at
   a time and runs the calls one after another.
2. **Cap**: 4 calls at once per round by default, set by `STUDIO_AGENT_PARALLEL_TOOLS`.
3. **Approvals**: one approval per call, as today. The other calls of the round run meanwhile.
4. **Failures**: the other calls finish, and the model gets every result, errors included.
5. **Exports**: Python, the LangGraph project and TypeScript run the calls concurrently, honouring the node setting.

## Problem Or Opportunity

- Models ask for parallel calls often: OpenAI and Anthropic return several tool calls in one turn when they are
  independent. Today, `A/__tool` runs **one call per step** (DEC-0063 decision 1), so a round takes the sum of its
  calls' times.
- With workflow tools (REQ-0073), each call is a child run that can take seconds. The Support team template asks the
  Order desk and the Refund desk one after the other.
- LangGraph's prebuilt `ToolNode` and the OpenAI Agents SDK run a turn's tool calls concurrently. Users who come from
  them expect the same.

## Scope

### In Scope

- **Engine**:
  - the pending calls of a round run as parallel steps of the same superstep (LangGraph `Send`);
  - each step is an `A/__tool` execution with its own iteration, checkpoint, ledger entry and idempotency key;
  - the next model step waits for all of them;
  - results go back into the conversation in the model's order, whatever order they finish in.
- **Setting** on the Agent node, on by default (CLAR-0007 question 1). With the setting off, providers that
  support it are asked for one call at a time (`parallel_tool_calls: false`).
- **Concurrency cap** per round (CLAR-0007 question 2).
- **Waiting inside a round**:
  - a call that needs approval pauses on its own, as a Human node does in a parallel branch;
  - a workflow tool waits for its child;
  - the other calls run, and the round continues when all have results (CLAR-0007 question 3).
- **Failures**: a failed call gives the model an error result, as today. The other calls still finish (CLAR-0007
  question 4).
- **Trace**: the round's calls show as overlapping bars under the same round. The run's timeline shows that they ran
  at the same time.
- **Time travel**: a fork starts from the checkpoint before the round or after it, never between two of its parallel
  calls.
- **Exports**: the Python, LangGraph project and TypeScript exports run the calls concurrently, honouring the node
  setting (CLAR-0007 question 5).
- Handbook en and vi (the Agent node page). CHANGELOG. DEC-0063 is amended by a new decision.
- Tests:
  - engine: order of results, cap, one call failing, approval in a round, restart in the middle of a round with no
    call repeated;
  - pytest: workflow tool children started together;
  - e2e: the Support team template with two desks in one round, in vi and en.

### Out Of Scope

- Several Agent nodes running in parallel. Branches of the graph already do that.
- Streaming the results of a round's calls to the model one by one.
- Parallel calls inside one HTTP or MCP tool, for example batching.

## Stakeholders Or Users

- Builders of Agent workflows, especially supervisors that use workflow tools.
- People who chat with those workflows and wait for answers.

## Current Context

- DEC-0063: `A → A/__model ⇄ A/__tool → A/__exit`. One call per `A/__tool` step. The pending calls are in the private
  field `agent:A.pending`.
- The engine runs parallel branches and resumes the siblings of a Human node together
  (`engine/runtime.py`, `run_waiting.checkpoint.nodes`).
- Workflow tools raise `AwaitChild`. The run service resumes the parent when the child settles (`resume_parent`). With
  several children in one round, the parent must resume only once all of them have settled.
- The ledger (`engine/effects.py`) keys a result by (run, node, iteration).

## Desired Behavior

1. The Support team supervisor gets "Where is order A100 and can I get a refund for B200?". The model asks
   `order_desk` and `refund_desk` in one round. The trace shows both calls starting together. The answer comes in
   about the time of the slower desk, instead of the two added together.
2. One of the two calls needs approval. The approval waits in the inbox, and the other call finishes. After the
   approval, the round completes and the model answers.
3. The worker restarts while one child run is still going. After the restart, the finished call is not run again, and
   the round waits for the other.

## Business Rules

- Results always reach the model in the order of its `tool_calls`.
- A round never starts more calls than the cap at once. The rest start as calls finish.
- `max_rounds` still counts model calls, not tool calls.
- An idempotency key stays unique for each call, including when two calls of the same tool run in one round.

## Constraints

- DEC-0018 (effectively once) and DEC-0063 decision 3 still hold for each call.
- No new dependency. The layers of DEC-0009 apply.
- The exports must still compile and run (`deno check`, the Python snapshot tests).

## Acceptance Criteria

- A mock model that asks for three calls in one round runs them concurrently. The test measures overlapping start and
  end times, and the conversation lists the results in the model's order.
- With the cap at 2, no more than two calls run at once.
- A call that raises gives the model an error result, and the others complete.
- An approval in a round pauses only that call. Answering it completes the round.
- A restart in the middle of a round repeats none of the finished calls. Ledger tests cover this.
- Two workflow-tool calls in one round start two child runs together. The parent resumes once, after both settle.
- With the node setting off, the calls run one after another as today.
- The backend suite, vitest, e2e, `tests/test_layers.py`, and the export tests pass.

## Edge Cases

- The model asks for the same tool twice with the same arguments. Both run, each with its own key.
- One child run is cancelled. Its call gets the cancelled result, and the round goes on.
- The run is cancelled during a round. Every running call and child is cancelled.
- The deadline of a waiting approval passes while another call is still running. The approval's timeout rule
  applies, and the round goes on when the rest finish.
- A provider ignores `parallel_tool_calls: false`. The engine still runs the calls one after another.

## Assumptions

- Most tools that models call in one round are independent, as the providers' own guidance says.

## Open Questions

None. CLAR-0007 is answered.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`
- `.factory-state/artifacts/REQ-0072-agent-node.md`, `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`
- `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`, `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- `.factory-state/tasks/done/TASK-0157-parallel-tool-waves.md`, `.factory-state/tasks/todo/TASK-0158-parallel-tool-waits.md`, `.factory-state/tasks/todo/TASK-0159-parallel-tool-trace.md`, `.factory-state/tasks/todo/TASK-0160-parallel-tool-exports.md`, `.factory-state/tasks/todo/TASK-0161-parallel-tool-handbook.md`
- `.factory-state/artifacts/REV-0136-task-0157.md`, `.factory-state/artifacts/QA-0137-task-0157.md`
- `.factory-state/decisions/DEC-0018-effectively-once.md`
- `docs/backend-architecture.md`
