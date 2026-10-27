# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0078
- Status: Draft. Waiting on the owner's answers to CLAR-0009.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Source: owner request in chat on 2026-10-27 ("3 hướng có thể làm thì bạn viết REQ trước đi"). REQ-0073 left
  "Hand-off between agents" out of scope (CLAR-0004 question 1 chose workflow tools first).

## Summary

- An Agent node can **hand the conversation off** to another Agent node in the same workflow. The first agent stops,
  and the second continues with the conversation so far and answers the person itself.
- This is the "swarm" or "triage" pattern:
  - a front agent decides who should help, then steps aside;
  - unlike a supervisor (REQ-0073), it does not wait for the result and rephrase it.
- In a chat, the agent that holds the conversation can keep it for the next messages, as CLAR-0009 question 3
  decides.

## Problem Or Opportunity

- With workflow tools, a supervisor always stays in the loop. Every answer passes through it, which costs a model call
  and can lose detail. For a help desk, people expect to be routed: "I'll pass you to billing", after which billing
  answers directly.
- Building that today takes Decision or Condition nodes and a state field the builder has to manage by hand.
- LangGraph supports it (`Command(goto=...)` and `langgraph-swarm`), and so do the OpenAI Agents SDK (`handoffs`) and
  CrewAI. Users who come from them look for it.

## Scope

### In Scope

- **Hand-off targets** on the Agent node: a list of the other Agent nodes this one may hand off to (CLAR-0009
  question 1), each with a short description.
  - Each target becomes a tool the model can call, `transfer_to_<name>`.
  - It takes an optional `reason`.
- **Engine**:
  - calling a hand-off tool ends the agent's round;
  - its exit routes to the target agent instead of following its own outgoing edge;
  - the target agent starts from the conversation so far, as CLAR-0009 question 2 decides;
  - the hand-off is a step with its own checkpoint, so a pause, crash or restart neither repeats it nor loses it.
  - The workflow continues from the agent that answers last, following that agent's outgoing edges.
- **Limit**: a run may hand off at most N times (CLAR-0009 question 4). Past that, the agent must answer itself, and
  the model is told so.
- **Chat**: across messages of one session, the agent that answered last can keep the conversation (CLAR-0009 question
  3). The session remembers it, and the next run starts at that agent.
- **Canvas** (CLAR-0009 question 5): hand-off links are drawn from agent to agent, and adding a target in the node's
  settings adds the link. Saving refuses a target that is not an Agent node of the same workflow.
- **Trace**: a hand-off step shows "Triage › handed off to Billing" with its reason, and the target agent's steps
  follow.
- **Exports**: Python, the LangGraph project and TypeScript, as CLAR-0009 question 6 decides.
- **Template**: a "Help desk with hand-offs" template, with a triage agent, Billing and Technical.
- Errors in CATALOG, `docs/api-errors.md` and both locales. en and vi. Handbook en and vi (the Agent node page and a
  hand-off guide). CHANGELOG. A decision record for the routing and the chat state.
- Tests:
  - engine: routing, the limit, restart in the middle of a hand-off, time travel across a hand-off;
  - pytest: the chat keeps the active agent;
  - export snapshots;
  - e2e: the template in the Chat tab and on the public page, in vi and en.

### Out Of Scope

- Hand-off to another workflow. A workflow tool already calls one, and a cross-workflow hand-off would mean moving the
  chat to another run.
- Hand-off to a person (a Human node as a target). It may come later through the same list.
- Agents that talk to each other freely (group chat).
- Parallel hand-offs to several agents at once.

## Stakeholders Or Users

- Builders of multi-agent workflows, especially chat help desks.
- People who chat with those workflows.

## Current Context

- DEC-0063: an Agent node `A` is expanded into `A → A/__model ⇄ A/__tool → A/__exit`. Its conversation is in the
  private field `agent:A`, which `A/__exit` clears.
- An Agent node's history field (`history_field`) gives it the chat's earlier turns.
- A chat message starts a new run with the history window (`chat_session_service.run_input`). Today, nothing carries
  "who is talking" from one run to the next.
- REQ-0073, DEC-0066: workflow tools, the supervisor pattern.

## Desired Behavior

1. A person writes "I was charged twice". Triage hands off to Billing with the reason "duplicate charge". Billing
   answers. The trace shows the hand-off and then Billing's steps.
2. The person replies "the second charge was yesterday". Billing answers again without going through Triage, if
   CLAR-0009 question 3 keeps the conversation with Billing.
3. Billing finds that the problem is technical and hands off to Technical. A third hand-off in the same run, past the
   limit, is refused, and the agent answers itself.
4. The builder adds Technical as a target of Triage. A dashed link appears from Triage to Technical on the canvas.

## Business Rules

- An agent can hand off only to its listed targets, and never to itself.
- Hand-off tools never need approval. They move no data out of the workflow.
- The target agent uses its own model, prompt, tools and credentials.
- After a hand-off, the output field is written by the agent that answers, so the chat's reply field stays the same
  for every agent.

## Constraints

- DEC-0063 and DEC-0018 still hold: one checkpoint per step, and effectively-once side effects.
- Saving checks the targets and refuses a hand-off cycle that has no limit. The run-time limit is the safety net.
- The layers of DEC-0009 apply. No new dependency.

## Acceptance Criteria

- In a workflow Triage → (Billing | Technical), a mock model that hands off to Billing makes Billing answer. The run's
  final state has Billing's answer in the output field.
- The trace has a hand-off step with the target and the reason.
- The limit stops the (N+1)th hand-off in a run, and the run still finishes with an answer.
- A restart right after the hand-off step continues with the target, with no step repeated.
- In a chat, the second message goes to the agent that kept the conversation, or to the entry agent, as CLAR-0009
  question 3 decides. A test proves it.
- A target that is not an Agent node of the workflow is refused on save with a translated message.
- The exports compile and run a hand-off (`deno check`, the Python snapshot and run tests).
- The backend suite, vitest, e2e, `tests/test_layers.py` and the strict handbook build pass.

## Edge Cases

- The model calls a hand-off tool and another tool in the same round. The hand-off wins, and the other call is
  answered with "not run: the conversation was handed off".
- The target agent was deleted from the workflow after a session started. The chat goes back to the entry agent.
- A hand-off happens in an agent inside a subgraph. The targets must be in the same subgraph.
- Time travel to a checkpoint before the hand-off, with a different answer, can lead elsewhere.

## Assumptions

- Hand-offs stay inside one workflow. Several workflows working together use workflow tools.

## Open Questions

- CLAR-0009: the targets, what the target sees, the chat state, the limit, the canvas, and the exports.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0009-agent-handoff.md`
- `.factory-state/artifacts/REQ-0072-agent-node.md`, `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`
- `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md` (question 1)
- `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- `.factory-state/artifacts/REQ-0048-agent-chat.md`, `.factory-state/decisions/DEC-0052-web-chat-model.md`
- `docs/backend-architecture.md`
