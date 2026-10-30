# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0073
- Status: Proposed on 2026-10-30. Waits for the owner to confirm the task set (TASK-0179 to TASK-0184).
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Related Requirements: REQ-0078 (CLAR-0009)
- Related Architecture: DEC-0063 (Agent node expansion), DEC-0069 (parallel tool calls), DEC-0052 (web chat model), DEC-0009, DEC-0010, DEC-0008, DEC-0033
- Related Tasks: TASK-0179, TASK-0180, TASK-0181, TASK-0182, TASK-0183, TASK-0184

## Context

- An Agent node `A` is expanded before compilation into `A` → `A/__model` ⇄ tool wave → `A/__join` → `A/__exit`, and the agent's outgoing edges leave from `A/__exit`.
- CLAR-0009 fixed targets (same-workflow Agent nodes), context (messages without tool traffic, plus reason), chat state (keep the last agent), the limit (5, workflow setting), the canvas (dashed links) and exports (all three).

## Decision

1. **Model.** Targets live in Agent node data (`handoffs`), not as workflow edges. The canvas derives dashed links from them. `max_handoffs` is a workflow setting, default 5. Targets must be in the same graph level (workflow or subgraph).
2. **Routing.** Each target is a tool `transfer_to_<slug>`. Calling it sets a private `__handoff` field and ends the round. A new step `A/__handoff` (own checkpoint) records the hand-off, increments the run counter and routes by a conditional edge to the target's entry; without a hand-off, `A/__exit` follows the agent's own edges. LangGraph `Command(goto)` is not used.
3. **Context.** The target receives the person's messages and the agents' final replies, without tool calls and results, plus a system note with the source agent and reason. Past the limit the hand-off tools are removed and the model is told to answer itself.
4. **Chat.** The chat session stores `active_agent`. The next run's input carries `__start_agent`; a start router added by the compiler routes to that agent when it exists, else to the normal entry.
5. **Exports.** Python, the LangGraph project and TypeScript mirror steps 2 to 4 with the same step names.

## Rationale

- A conditional edge on a private field fits the existing expansion, checkpointing, time travel and exporters, which all assume static edges.
- Targets in node data keep a single source of truth for the canvas and the validator.

## Alternatives Considered

- `Command(goto=...)`: idiomatic LangGraph, but the compiler, time travel and three exporters would each need a second routing style. Not chosen.
- Hand-off edges stored as workflow edges with a `kind`: visible in the JSON, but every edge consumer would have to skip them. Not chosen.
- Resuming the previous chat run's checkpoint instead of a start router: keeps full state but couples sessions to old runs and versions. Not chosen.

## Impacts

- New node and workflow fields, an Alembic revision for `chat_sessions.active_agent`, new error code `AGENT_HANDOFF_TARGET_INVALID`, new trace step kind, export changes, a new template.

## Risks

- Hand-off loops between two agents are bounded only by the limit; the limit message must make the model answer.
- Interaction with REQ-0076 waves: a hand-off in a wave must cancel the other calls cleanly.

## Approval

- Approved By: pending
- Approved On: pending
- Scope And Limits: CLAR-0009 answers.

## Review Or Revisit Trigger

- Hand-off to a person or to another workflow is requested.
