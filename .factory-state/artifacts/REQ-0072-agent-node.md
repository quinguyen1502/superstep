# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0072
- Status: Draft (owner questions in CLAR-0003)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Source: owner request in chat, 2026-10-25 ("Node agent sẽ cho LLM tự chọn và gọi các tool bạn cho phép: tool từ MCP
  server, HTTP, tool có sẵn và tìm trong knowledge base. Nó lặp cho tới khi ra câu trả lời, có giới hạn số vòng, và có
  thể bắt phải duyệt trước khi gọi một tool nào đó."). It follows the comparison with Langflow, Flowise, Dify and n8n
  (REQ-0069): those builders have an agent that picks its own tools; Superstep can call an MCP tool only from a fixed
  MCP node (REQ-0011).

## Summary

- A new **Agent** node. The model gets a prompt and a list of tools the builder allows. It decides which tool to call
  and with which arguments, sees the result, and repeats until it gives a final answer.
- Tool sources: **MCP server tools**, **HTTP requests**, **built-in Python tools** and **knowledge base search**.
- The loop has a **maximum number of rounds**. Each tool can be marked **needs approval**: the run pauses before that
  call and waits for a person, like a Human node.

## Problem Or Opportunity

- Today every tool call is a node the builder places and wires by hand (Tool, MCP, Retriever). The graph decides the
  order; the model cannot choose a tool, call it again, or skip it.
- Questions such as "look up the order, then check the refund policy, then answer" need either many Condition nodes
  or a Code node with hand-written LangChain code.
- Visual builders that compete with Superstep all ship an agent node (REQ-0069). LangGraph itself has the pattern
  (`create_react_agent`, `ToolNode`, `interrupt_before`), so it fits the engine and the exports.

## Scope

### In Scope

- **Agent node** in the palette, the config panel, the validator, the compiler, the run trace and the exports.
- **Settings:** credential and model (as the LLM node), system prompt and task prompt (templates with `{{state}}`
  paths), the allowed tools, maximum rounds, output field, and the approval settings (CLAR-0003 Q2).
- **Tools**, each with a name and a description the model reads (CLAR-0003 Q1 decides where tools are defined):
  - **MCP:** a tool of a registered MCP server (REQ-0011). Its input schema comes from the server's tool list.
  - **HTTP:** method, URL, headers, body and credential as the HTTP Tool node, plus the parameters the model fills
    (a small JSON Schema). URL and body templates can use the model's arguments and state.
  - **Built-in:** a function from the Python tool registry (`engine/tools.py`), with a parameter schema.
  - **Knowledge base search:** a knowledge base and `top_k`; the model supplies the query.
- **Loop:** call the model with the tools; run the tool calls it asks for; send the results back; stop when the model
  answers without a tool call, or when the round limit is hit (CLAR-0003 Q5). One round = one model call plus the
  tool calls it asked for. Several calls in one round run one after another, in the model's order.
- **Approval before a tool:** a per-tool "needs approval" switch. The run waits with a prompt that names the tool and
  shows the arguments. It goes through the existing waiting step: the Approvals inbox, the run panel, the approval
  channels (Slack, Telegram) and the deadline settings (REQ-0003, REQ-0034, REQ-0041). The answer resumes the run;
  CLAR-0003 Q3 and Q4 decide what the approver can do and what a rejection does.
- **Mock model:** the offline mock (no key, demo, test runs with the mock option) drives the loop
  deterministically, so templates, tests and the public demo work offline.
- **Trace and usage:** each round shows in the run trace under the Agent node: the model's reply, each tool call with
  arguments, result (shortened), duration and error, and the approval wait. Token usage and cost add up per node.
- **Workflow tests (REQ-0042):** a check that a tool was or was not called; test-case Human answers also answer agent
  approvals.
- **Template:** at least one built-in template with an Agent node (for example support: the order lookup tool plus a
  knowledge base), with test cases, as every built-in template has.
- **Errors:** new codes in `core/errors.py` `CATALOG`, `docs/api-errors.md` and both locales, for example a provider
  without tool calling, the round limit, an approval rejected (if it stops the node).
- **UI:** shadcn/ui and theme tokens only, en+vi strings with identical keys, glossary rows for the new terms
  (`docs/ui-conventions.md` rules 10 and 11). Removing a tool from the list follows the delete rule
  (`ConfirmDeleteDialog`, DEC-0025) only if it deletes a stored record; removing a row from an unsaved node list is
  an edit.
- **Handbook** (en, vi): an Agent node page; the node reference, the MCP guide and the comparison pages updated.
  CHANGELOG Unreleased.

### Out Of Scope

- Several agents handing work to each other (multi-agent, supervisor, handoffs).
- Code-mode tools (Python or TypeScript written in the node) and "another workflow as a tool". They can follow on
  the same tool model.
- Letting the model use every tool of an MCP server without the builder listing it.
- Memory across runs other than the `messages` field convention of the chat (REQ-0048).
- Images, files and audio as tool input or output.
- Streaming each token of a tool-call argument into the trace (the final text streams as the LLM node does).

## Stakeholders Or Users

- Builders who want the model to choose tools instead of wiring every branch.
- Approvers who must agree before an agent sends an e-mail, posts to an API or changes data.
- Workflow owners, whose credentials, model budget and MCP servers the agent uses (DEC-0023).

## Current Context

- **Nodes:** `backend/app/engine/nodes.py` `node_fn` builds each node type: `llm` (`call_llm`, one prompt string, no
  tools), `tool` (`mode` function, http or code), `retriever` (`ports.retrieve`), `mcp` (`ports.mcp_call`), `human`
  (raises `Interrupt`; the resume value is consumed once). Node types are listed in `engine/validator.py` `TYPES`.
- **Models:** `engine/providers.py` registry (OpenAI, Anthropic, Ollama, LM Studio, OpenAI-compatible, OpenRouter,
  TypeSafe). Each provider builds a LangChain chat model (`chat_model`, `bind_tools`) and has a `supports_tools` flag;
  TypeSafe has none. `engine/llm.py` `mock_llm` is the deterministic offline mock.
- **Tools:** `engine/tools.py` (`TOOLS`, `register_tool`), `engine/effects.py` `call_tool`, `nodes.http_call` (SSRF
  guard `core/net.py`), `engine/mcp_client.py` and `services/mcp_service.py`, `services/knowledge_service.py`. The
  engine reaches services only through `engine/ports.py` `Ports`.
- **Effectively-once (TASK-0021, DEC-0018):** `Effects` gives each (run, node, iteration) an idempotency key and a
  ledger entry; HTTP Tool nodes send `Idempotency-Key`. The ledger works per node execution, not per step inside a
  node.
- **Approvals:** `services/approval_service.py` `on_waiting` reads the paused node's `data.approval` (channel,
  target, approvers) and `deadline` (`engine/deadlines.py`), writes the waiting step and sends the channel message.
- **Durability:** runs resume from LangGraph checkpoints after a pause; TASK-0115 (PR #143, REQ-0071) continues
  unfinished runs after a restart from the last checkpoint without repeating finished nodes. Time travel (REQ-0051)
  forks from a checkpoint.
- **Limits:** `STUDIO_RECURSION_LIMIT` (default 25 steps), run timeout, per-node timeout and retries
  (`engine/node_policy.py`), event size caps (`engine/limits.py`).
- **Exports:** `python_export.py`, `typescript_export.py`, `project_export.py` (REQ-0043, REQ-0047, REQ-0053) write
  readable code per node type, with stubs such as `call_mcp_tool` for things the studio provides.
- **Chat (REQ-0048):** the history goes into a `messages` list field; step visibility `none` / `labels` / `full`.

## Desired Behavior

- A builder adds an Agent node to the Support template, picks an OpenAI credential and `gpt-4o-mini`, writes "Help
  the customer: {{message}}", and allows two tools: `lookup_order` (built-in) and "Search the refund policy"
  (knowledge base). `send_refund` (HTTP) is allowed with **needs approval** on. Max rounds: 6. Output field: `answer`.
- A run with "Where is order B200, and can I get a refund?":
  1. Round 1: the model calls `lookup_order`. The trace shows the call, its arguments and "In transit".
  2. Round 2: the model searches the refund policy; the trace shows the top chunks.
  3. Round 3: the model answers without a tool. `answer` holds the text; the next node runs.
- A run where the model wants `send_refund`: the run status becomes `waiting`. The Approvals inbox and the Slack
  channel show "Agent wants to call send_refund" with the arguments. After Approve the call runs and the loop goes on;
  after Reject the outcome follows CLAR-0003 Q4.
- The API restarts while the run waits, or between two rounds: the run continues from the last finished round. No
  tool call and no model call that already finished runs again.
- With no credential (mock), the same workflow runs offline: the mock calls a listed tool, then answers with its
  result, so the trace has at least one tool round.
- A model that keeps calling tools stops after 6 rounds with the outcome chosen in CLAR-0003 Q5.

## Business Rules

- The model can call only the tools listed on the node. A call to an unlisted tool or with arguments that do not
  match the schema is never executed; the error goes back to the model as the tool result and the round counts.
- Tool names are unique within a node and use the characters providers accept (letters, digits, `_`, `-`, at most
  64).
- Tool results are untrusted input: they go back to the model shortened to a size limit and never change the tool
  list, the approval settings or the credentials. Credentials and secrets are never shown to the model.
- A run uses the workflow owner's credentials, MCP servers and knowledge bases, as every saved-workflow run does
  (DEC-0023); the existing access checks apply to each tool.
- Demo mode keeps its rules: tools that are disabled as nodes in the demo (HTTP) are disabled as agent tools too.
- Test runs keep their rules (DEC-0044): no e-mail, channel message, notification or callback is sent.

## Constraints

- Layering (DEC-0009): the loop lives in `engine/`; services reach it through `Ports`; no FastAPI in services; a
  migration only if a stored record changes (a node's settings live in the workflow JSON).
- Effectively-once per tool call: every model call and every tool call inside the loop is a step that is recorded
  once, so a resume after a pause, a restart (TASK-0115) or a retried job does not repeat it. Each HTTP tool call
  gets its own stable idempotency key. The mechanism (for example compiling the node into LangGraph model and tool
  steps with checkpoints, or a per-step journal on the existing ledger) is a design decision for `plan-tasks`
  (DEC).
- Rounds must fit the run's step budget; the round limit has a hard maximum and raises the recursion budget as For
  each loops do (`foreach.step_budget`).
- Offline mock mode keeps working with no API keys (`project.md` constraint).
- API responses use the shared envelope and central handlers; new error codes in the catalog, `docs/api-errors.md`
  and both locales (`tests/test_api_envelope.py`).
- Frontend calls the API only through `lib/api.ts`; every UI string in `locales/en.json` and `locales/vi.json`.

## Acceptance Criteria

- The Agent node can be added, configured, validated, saved, versioned and copied like other nodes; the validator
  reports a missing model, prompt, output field or tool, a duplicate or invalid tool name, a round limit out of
  range, and a model whose provider has no tool calling.
- A run with a real provider (respx-mocked in pytest) calls the listed tools the model asks for, passes the results
  back, and writes the final answer to the output field; MCP, HTTP, built-in and knowledge base tools each have a
  test.
- A tool with "needs approval" pauses the run before the call; the waiting step appears in the Approvals inbox and
  the channels with the tool name and arguments; approve runs the call; reject follows CLAR-0003 Q4; deadlines apply.
- A pytest restart test (as in TASK-0115) shows that a run paused at an agent approval, and a run stopped between
  two rounds, continue after a restart without repeating a finished model call or tool call.
- The round limit stops the loop with the CLAR-0003 Q5 outcome; an unlisted tool or bad arguments are never
  executed.
- The offline mock produces at least one tool round and a final answer; the Agent template's test cases pass with the
  mock option.
- The run trace (studio and the chat's `full` view) shows each round, tool call, result, error and approval; usage
  and cost add up.
- Workflow tests have a "tool called" check; Python export (and the other exports per CLAR-0003 Q8) handle the node.
- en/vi strings with identical keys and glossary rows; handbook pages (en, vi) build in strict mode; e2e covers
  adding the node, a run with tool rounds, and an approval; `factory verify run --profile full` passes.

## Edge Cases

- The model returns several tool calls in one round, one of which needs approval: calls before it run, the run
  waits at it, and the rest run after the answer.
- A tool fails (MCP server down, HTTP 500, knowledge base empty): the error goes back to the model as the result; the
  node fails only if the round limit is hit or the model gives up.
- The provider or model has no tool calling (TypeSafe, some Ollama models): a clear error code, at validation when
  the provider is known, at run time otherwise.
- A tool result too large for the model's context: shortened with a marker (`engine/limits.py`).
- The run is cancelled or times out while a tool runs: the loop stops at the next step, as Code nodes do
  (`ports.cancelled`).
- The node sits inside a For each loop or a subgraph: each iteration has its own rounds, keys and approvals.
- A workflow version changes while a run waits at an approval: the run keeps its own workflow snapshot, as Human
  nodes do.
- Time travel forks a run at a checkpoint inside the loop (if rounds are checkpoints): the fork continues from that
  round.

## Assumptions

- The LangChain chat models the providers already build (`bind_tools`) are the tool-calling interface; no new model
  SDK is needed.
- One Agent node is one agent; the default round limit is small (for example 5) with a hard maximum (for example
  25).
- Answers in CLAR-0003 may move items between In Scope and Out Of Scope; the requirement is updated when they come.

## Open Questions

- Eight owner questions in `.factory-state/artifacts/CLAR-0003-agent-node.md`: where tools are defined, who
  approves, whether an approver can edit arguments, what a rejection does, what the round limit does, what the node
  writes to state, whether the chat history goes in, and which exports support the node.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0003-agent-node.md`
- `.factory-state/artifacts/REQ-0003-human-in-the-loop.md`, `REQ-0007-rag-node.md`, `REQ-0011-mcp-tools.md`,
  `REQ-0034-more-approval-channels.md`, `REQ-0041-approval-deadlines-and-inbox.md`, `REQ-0042-workflow-tests.md`,
  `REQ-0043-python-export.md`, `REQ-0048-agent-chat.md`, `REQ-0051-time-travel.md`,
  `REQ-0069-superstep-comparison-pages.md`
- REQ-0071 (durable resume after restart, TASK-0115, PR #143) and REQ-0070 (workflows as MCP tools, TASK-0114,
  PR #142), on their branches until merged.
- `.factory-state/decisions/DEC-0018-effectively-once.md`, `DEC-0023-rbac-sharing.md` (a run uses the owner's
  resources), `DEC-0025-ui-only-delete-confirmation.md`, `DEC-0044-workflow-test-runs.md`
- `docs/backend-architecture.md` (DEC-0009), `docs/ui-conventions.md` (DEC-0008, DEC-0025)
