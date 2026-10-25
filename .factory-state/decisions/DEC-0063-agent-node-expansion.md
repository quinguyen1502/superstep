# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0063
- Status: Proposed (owner review with the TASK-0116 to TASK-0120 plan)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Related Requirements: REQ-0072 (CLAR-0003), REQ-0011, REQ-0041, REQ-0042, REQ-0043
- Related Architecture: DEC-0009 (layers), DEC-0018 (effectively-once), DEC-0032 (provider registry), DEC-0044 (test runs)
- Related Tasks: TASK-0116, TASK-0117, TASK-0118, TASK-0119, TASK-0120

## Context

- REQ-0072 needs a model-and-tools loop where every model call and every tool call happens once, even across an
  approval pause, a restart (TASK-0115) or a retried job, and where the run can wait before one tool call.
- A LangGraph node that raises an interrupt runs again from its start on resume. The side-effect ledger
  (`engine/effects.py`) records one result per (run, node, iteration), not steps inside a node. So a loop inside one
  node function would repeat the tool calls that ran before a pause, unless it kept a second journal of its own.
- Subgraph nodes (`engine/subgraphs.py`, TASK-0011) already solve "one canvas node, many graph steps": the child
  workflow is expanded inline before validation and compilation, so its nodes trace, pause, checkpoint, recover and
  use the ledger like top-level nodes.
- LangGraph's own agent (`create_react_agent`) is the same shape: a model node, a tools node and a conditional edge
  that loops while the model asks for tools.
- Providers build LangChain chat models (`chat_model`, `bind_tools`) for OpenAI, OpenAI-compatible, LM Studio,
  OpenRouter and Ollama. Anthropic is called over plain HTTP and has no chat model; TypeSafe and SMTP have
  `supports_tools = False`.

## Decision

1. **The Agent node is expanded before validation and compilation**, by a new `engine/agents.py` `expand(wf)` that
   runs after `subgraphs.expand` (so agents inside subgraphs are expanded too) in the run, save-validation and export
   paths. One `agent` node `A` becomes:
   - `A` itself (type `agent`): the entry. It builds the conversation (system prompt, the history field's earlier
     turns, the rendered task prompt) into the agent's private field.
   - `A/__model` (type `agent_model`): one model call per step.
   - `A/__tool` (type `agent_tool`): **one tool call per step**.
   - `A/__exit` (type `agent_exit`): writes the output field and the optional steps field, clears the private field,
     and carries `A`'s outgoing edges.
   - Edges: `A → A/__model`; after `A/__model`, pending calls go to `A/__tool`, otherwise to `A/__exit`; after
     `A/__tool`, more pending calls go to `A/__tool`, otherwise back to `A/__model`. Labels are `Agent › model` and
     `Agent › tool`, and errors are named by label (`subgraphs.readable`).
2. **Private state:** expansion adds a hidden object field `__agent__A`:
   `{messages: [{role, content, tool_calls?, tool_call_id?, name?}], pending: [{id, name, args}], rounds, limit_hit,
   steps: [{tool, args, result, status, ms}]}`. It is plain JSON, so checkpoints, time travel and the exports
   serialize it. Fields starting with `__` are left out of input forms and input schemas.
3. **Effectively-once per step:** `agent_model` and `agent_tool` join `SIDE_EFFECT_TYPES`. Each execution is a
   LangGraph step with its own checkpoint and its own `node_started` iteration, so it gets its own ledger entry and
   idempotency key `(run, A/__tool, iteration)`; HTTP tools send it as `Idempotency-Key`. A pause, crash or restart
   repeats at most the step that had not finished.
4. **Model calls go through the provider registry:** a provider method `invoke_tools(messages, tools, model, cred,
   on_token) -> (text, tool_calls, usage)`. The base implementation uses `chat_model(...).bind_tools(...)`
   (OpenAI, OpenAI-compatible, LM Studio, OpenRouter, Ollama). Anthropic implements it over its Messages API `tools`
   over plain HTTP, with no new dependency. A provider with `supports_tools = False` fails validation with a new
   error code. At the round limit the call is made without tools and `limit_hit` is set (CLAR-0003 Q5).
5. **The mock** (`llm.mock_agent`) is deterministic. With no tool result yet, it calls the listed tool whose name or
   description shares the most words with the task prompt (the first tool when none do), filling string parameters
   with the task text. Otherwise it answers `[mock:<model>] Answer: <last tool result>`.
6. **Tools run through the existing paths:** MCP through `ports.mcp_call`, knowledge base through `ports.retrieve`,
   built-ins through `TOOLS` and `effects.call_tool`, HTTP through `nodes.http_call` (SSRF guard and demo rule shared
   with the HTTP Tool node). Before a call, the arguments are checked against the tool's schema (required properties
   and JSON types, no new dependency). An unknown tool, bad arguments or a failed call becomes an error tool result
   for the model and is never executed. Results are shortened (`engine/limits.py`).
7. **Approval reuses the Human node path:** before a call to a tool marked `approval: true`, `agent_tool` raises
   `Interrupt(A/__tool, prompt)` with `tool` and `arguments` on the waiting event, unless the resume is for this call.
   Expansion copies `A`'s `approval` and `deadline` settings onto `A/__tool`, so `ApprovalService.on_waiting`, the
   inbox, the channels and the deadlines work unchanged. `approved` runs the call. `rejected` (plus the comment)
   becomes the tool result "rejected by a reviewer" (CLAR-0003 Q3, Q4).
8. **Step budget:** `agents.step_budget(wf)` = for each agent, `max_rounds × (1 + MAX_CALLS_PER_ROUND) + 3`, added
   to the recursion limit as `foreach.step_budget` is. `max_rounds` is 1 to 25 (default 5), and
   `MAX_CALLS_PER_ROUND` is 8: further calls in one round get an error result.
9. **Exports:** the Python writer, which the LangGraph project export shares, emits the same four functions and two
   routers, with per-tool approval through `langgraph.types.interrupt()` and the existing stubs (`call_mcp_tool`,
   `retrieve`). It does not use `create_react_agent`, which cannot pause before one tool only and would not write
   the rounds and steps the studio writes. The TypeScript export refuses the node with a new error code
   (CLAR-0003 Q8).

## Alternatives Considered

- **The loop inside one node function, with a per-step journal on the ledger.** The graph stays one node, but this
  adds a second resume mechanism next to LangGraph checkpoints, and time travel, the trace and restart recovery
  would not see the steps.
- **`create_react_agent` compiled as a nested graph inside the node.** It is native LangGraph, but the studio runs
  one checkpointed thread per run. Inner steps would be invisible to the ledger, trace and time travel, and approval
  would apply to all tools or none.
- **A real Subgraph node (a saved workflow).** A subgraph is a fixed graph the builder draws. The agent's control
  flow is chosen by the model at run time, and its graph is generated from the node's settings, not stored.

## Consequences

- The agent's steps are ordinary graph steps: pause and resume, restart recovery (TASK-0115), time travel, the
  ledger, the trace and usage all work without new mechanisms.
- The canvas shows one node. The trace groups `A/__model` and `A/__tool` steps under it, as subgraph steps are
  grouped by label.
- The private field can grow with long conversations; tool results are shortened and the rounds are capped.
- Several API processes need no extra coordination: the steps use the existing leases and fencing.
