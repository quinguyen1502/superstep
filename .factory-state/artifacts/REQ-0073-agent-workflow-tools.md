# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0073
- Status: Accepted (owner, 2026-10-26; CLAR-0004 answered with all recommended options)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Source: owner request in chat, 2026-10-26 ("Cả 2 lần lượt": after TASK-0132, write the requirement for the next
  Agent feature, either extending the Agent node or several agents working together; analysis only, no code). REQ-0072
  left both out of scope: "Several agents handing work to each other" and "another workflow as a tool".

## Summary

- An Agent node can list **another saved workflow as a tool**. The model calls it by name with arguments, and the
  workflow runs and returns its result.
- A workflow that contains its own Agent node then acts as a **specialist agent**, and the calling Agent is its
  **supervisor**. This gives several agents working together without a new node type. Each agent keeps its own
  prompt, model, tools and limits, and is built and tested on its own canvas.
- A **hand-off**, where one agent passes the conversation to another and stops, is not in scope (CLAR-0004 question 1).

## Owner Decisions

CLAR-0004, answered 2026-10-26 (all recommended options):

1. **Workflow tools come first**: another saved workflow as an Agent tool, which gives the supervisor pattern. Hand-off,
   code tools and every tool of an MCP server stay out of scope.
2. **A workflow tool runs as a linked child run**: a run of its own (record, history, checkpoints, ledger) with a
   parent run id. The parent's tool step waits for it, and a restart repeats neither the child's finished nodes nor
   the child itself.
3. **Approvals inside the child are passed up**: the parent run waits too, and the Approvals inbox and the channels
   show the child's request with both workflow names.
4. **The latest saved version** of the child, taken when the parent run starts, as for Subgraph nodes. A waiting
   parent keeps that version in its snapshot.
5. **The trace is nested**: the child's steps show under the tool call in the parent's trace, with a link to the
   child run.
6. **Exports:** Python, the LangGraph project and TypeScript all support workflow tools in the first version.

## Problem Or Opportunity

- A single Agent node with many tools gets a long system prompt, a long tool list and more wrong tool calls. Splitting
  the work ("orders", "refunds", "policy questions") into smaller agents is the usual remedy. Today it needs a Code
  node with hand-written LangChain code, or a hand-built router of Condition nodes.
- A builder can already reuse a workflow with a Subgraph node, but the graph decides when it runs. The model cannot
  choose it, call it twice, or skip it.
- REQ-0070 exposes workflows as MCP tools to outside clients. An Agent node could reach them through its MCP tool
  source and the studio's own `/mcp` endpoint, but only by registering the studio as an MCP server with a workflow
  token. It is also slow, and the child run would not show in the parent's trace.
- The comparison pages (REQ-0069) list "no multi-agent teams or hand-offs" as a gap against CrewAI, AutoGen and the
  LangGraph supervisor pattern. Langflow and Flowise let an agent call another flow as a tool.

## Scope

### In Scope

- A fifth tool source on the Agent node, **workflow** (next to MCP, HTTP, built-in and knowledge base). The builder
  picks a saved workflow and gives the tool a name and a description the model reads.
- **Parameters:** derived from the chosen workflow's state fields (as REQ-0070 does for MCP tools), with a choice of
  which fields the model fills. **Result:** the fields of the workflow's final state that the builder picks, as JSON,
  shortened like any tool result.
- **Running the call:** the workflow runs as a linked child run (Owner Decision 2) with the parent run's resource
  owner, so the owner's credentials, MCP servers and knowledge bases (DEC-0023), and the same demo and test-run rules
  (DEC-0044).
- **Limits:** a depth limit and a cycle check across workflow tools and subgraphs (A calls B calls A is refused when
  saving, as for Subgraph nodes). The child's steps count toward a budget, so a supervisor cannot start unbounded
  work.
- **Trace:** the tool call shows the child workflow's steps nested under it, with a link to the child run, and its
  duration, usage and cost added to the Agent node (Owner Decision 5).
- **Approvals inside the child** (a Human node, or an Agent tool that needs approval) are passed up: the parent run
  waits too, and the inbox and the channels show the child's request with both workflow names (Owner Decision 3).
- **Runs:** a child run shows its parent (a link) in the run page and the history; a parent shows "waiting for
  <child workflow>" while a child runs or waits. Cancelling the parent cancels its children.
- **Validator:** a missing or unreadable workflow, an imported (code) workflow, a cycle, too deep, unknown result
  fields. All of these get message codes (DEC-0065) in en and vi.
- **Workflow tests (REQ-0042):** the existing "tool called" check works for workflow tools; test runs of the parent
  run the child with test-run rules.
- **Exports:** the Python, LangGraph project and TypeScript exports write the child workflow as its own graph in the
  same file, called by the tool function (Owner Decision 6).
- **Template:** a built-in "Support team" template. A supervisor Agent uses two specialist workflows as tools, with
  test cases that pass with the mock model.
- **UI:** the tool card for the workflow source (a workflow picker, the parameter and result field choices, a link to
  open the child). shadcn/ui and theme tokens only, en and vi strings with the same keys, glossary rows for new terms.
- **Handbook (en, vi):** the Agent node page (a "Workflows as tools" section and the supervisor pattern), the
  comparison pages, and the export page. CHANGELOG Unreleased.

### Out Of Scope

- Hand-off between agents (CLAR-0004 question 1).
- Agents running in parallel. A round's tool calls still run one after another (REQ-0072).
- Agents that talk to each other freely (group chat, AutoGen style) or share a memory other than the state they pass.
- Code-mode tools (Python or TypeScript written in the Agent node), and using every tool of an MCP server without
  listing it (CLAR-0004 question 1).
- Calling a workflow of another user that is not shared with the run owner.
- Images, files and audio as tool input or output.

## Stakeholders Or Users

- Builders who want small, focused agents instead of one agent with every tool.
- Approvers, when a specialist's tool needs approval: the request names both workflows.
- Workflow owners: the child runs with their credentials and budget (DEC-0023).

## Current Context

- **Agent node (REQ-0072, DEC-0063):** `backend/app/engine/agents.py`. `SOURCES = ("mcp", "http", "builtin",
  "knowledge")`, `parameters(t)` gives each tool's JSON Schema, and `run_tool()` runs one call. `agents.expand()` turns
  the node into entry, model, tool and exit steps, one tool call per step, so each call is checkpointed once.
  Approvals use `Interrupt` and the Human approval path.
- **Subgraphs (TASK-0011):** `engine/subgraphs.py` expands a saved workflow inline before compiling. `check()` finds
  missing workflows, cycles (`MAX_DEPTH` 5) and imported workflows. `validate_with()` and `WorkflowService._loader()`
  resolve the workflows the user may read.
- **Workflows as MCP tools (REQ-0070, TASK-0114):** `services/workflow_mcp_service.py` derives a tool's input schema
  from the workflow's state fields and returns its output; a run that waits returns `run_id` and `status: waiting`.
- **Runs:** `services/run_service.py` (`RunService`, queue jobs, `record`, recovery after a restart (REQ-0071,
  TASK-0115, TASK-0127)); `engine/runtime.py` `run_stream`; the step budget is `STUDIO_RECURSION_LIMIT`, raised by
  For each loops and Agent rounds.
- **Effectively once (DEC-0018):** the ledger and idempotency keys are per node execution and per agent tool step.
- **Exports:** `engine/python_export.py`, `engine/typescript_export.py` and `engine/project_export.py`. Subgraphs are
  exported inline; Agent nodes as the four steps (TASK-0119, TASK-0125).
- **Validation messages** carry codes (DEC-0065, TASK-0132).

## Desired Behavior

- A builder makes two workflows, "Order desk" (an Agent with `lookup_order`) and "Refund desk" (an Agent with the
  refund policy knowledge base and `send_refund`, which needs approval). Each takes `message` and writes `answer`.
- In a third workflow, "Support team", an Agent node lists both as tools: `order_desk` ("Questions about where an
  order is") and `refund_desk` ("Questions about refunds"). Parameters: `message`. Result: `answer`.
- A run with "Where is B200, and can I get a refund?":
  1. The supervisor calls `order_desk` with a message about B200. The trace shows the child's steps under that call,
     with a link to its run, and the result `{"answer": "B200 is in transit…"}`.
  2. It calls `refund_desk`. `send_refund` needs approval, so the child run and the parent run are both `waiting`.
     The Approvals inbox shows the request with both workflow names ("Support team › Refund desk: Agent wants to call
     send_refund"), and after Approve the child finishes and the parent goes on.
  3. The supervisor answers using both results.
- Saving "Order desk" with a workflow tool that points back to "Support team" fails with a cycle message, in the UI
  language.
- With no credential (mock), the template runs offline: the mock supervisor calls one specialist, which calls its
  own tool and answers.

## Business Rules

- The model can call only the workflows listed on the node, with arguments that match the derived schema. Other calls
  go back to the model as an error result, as for any tool (REQ-0072).
- A workflow tool runs the child's latest saved version, taken when the parent run starts (as for Subgraph nodes).
  The parent's snapshot keeps it, so a pause, a restart or a resume runs the same version.
- The child's result is untrusted tool output: shortened, and it never changes the parent's tools, approvals or
  credentials.
- Depth: workflow tools and subgraphs together nest at most `MAX_DEPTH` (5) levels. A cycle is refused when saving and
  again when running.
- A cancel or timeout of the parent stops the child.

## Constraints

- Layering (DEC-0009): the engine reaches other workflows only through `Ports` (as `subgraphs` gets a loader). No
  FastAPI in services. A migration adds the parent run and the calling step to child runs (DEC-0066).
- Effectively once: a finished child call is never repeated after a pause, a restart or a retried job. Its result is
  recorded with the tool step.
- The step budget and the run timeout cover the child's work.
- The offline mock keeps working with no API keys.
- API responses use the shared envelope; new error codes go in the catalog, `docs/api-errors.md` and both locales;
  validation messages in `engine/issues.py` and both locales (DEC-0065).

## Acceptance Criteria

- The Agent node's tool list offers the workflow source. A workflow tool can be configured, validated, saved,
  versioned and copied. The validator reports a missing or unreadable workflow, an imported workflow, a cycle, too
  deep, and unknown parameter or result fields.
- A run (pytest, with a respx-mocked provider) calls a workflow tool. The child runs as the owner and its result goes
  back to the model; usage and cost add up on the Agent node.
- The supervisor template runs offline with the mock and its test cases pass.
- A restart test (as in TASK-0115 and TASK-0127) shows that a finished child call is not repeated, and that a call cut
  off mid-way finishes or fails clearly.
- An approval inside a child makes both runs wait; the inbox and the channels show it with both workflow names; after
  Approve or Reject the child settles and the parent goes on, with a test for each.
- Cancelling the parent cancels a running or waiting child; a failed child gives the model an error result.
- The trace shows the child's steps under the tool call with a link to the child run, in the studio and the chat's
  `full` view.
- The Python, LangGraph project and TypeScript exports handle workflow tools; they pass `python -m py_compile`,
  `deno check` and the same-path test.
- en and vi strings with the same keys, glossary rows; handbook pages (en, vi) build in strict mode; e2e covers adding
  a workflow tool and a run that calls it; `factory verify run --profile full` passes.

## Edge Cases

- The child workflow is deleted or unshared after the parent was saved: the call returns a clear error to the model,
  and the validator reports it on the next save.
- The child fails (a node error): the error text goes back to the model as the tool result; the parent goes on.
- The model calls the same workflow tool several times in one run: each call is its own child run or step, with its
  own idempotency keys.
- A child that is itself a supervisor (depth 2 or more): the depth limit applies; the trace stays readable.
- A workflow tool inside a For each loop or a subgraph: each iteration calls the child on its own.
- Time travel (REQ-0051) forks the parent at a step after a child call: the fork keeps the recorded result and does not
  call the child again.
- The parent and the child use different credentials: each node uses its own, all owned by the run owner.

## Assumptions

- "Several agents" means the supervisor pattern first: one agent calls others as tools. Hand-off and parallel agents
  come later, if at all.
- A workflow tool reuses the subgraph loader's access rules (workflows the run owner can read).
- The child's state fields are the contract, as for MCP tools (REQ-0070), so no new "workflow inputs" setting is
  needed.

## Open Questions

- None: CLAR-0004 answered 2026-10-26 (Owner Decisions above).

## Planning

- 2026-10-26: the owner accepted REQ-0073 with the CLAR-0004 answers. Planned as TASK-0133 (tool settings and
  validation), TASK-0134 (linked child runs), TASK-0135 (approvals inside a child, runs pages), TASK-0136 (editor and
  nested trace), TASK-0137 (tests check, template, exports) and TASK-0138 (handbook), with DEC-0066 (a workflow tool
  is a linked child run that the parent's tool step waits for).

## Related Artifacts

- `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`
- `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Tasks: TASK-0133 to TASK-0138 under `.factory-state/tasks/` (`TASK-0133-workflow-tool-settings.md`,
  `TASK-0134-workflow-tool-child-runs.md`, `TASK-0135-child-run-approvals.md`, `TASK-0136-workflow-tool-editor-trace.md`,
  `TASK-0137-workflow-tool-template-export.md`, `TASK-0138-workflow-tool-handbook.md`; the folder follows each task's
  lifecycle state)
- `.factory-state/artifacts/REQ-0072-agent-node.md`, `.factory-state/artifacts/CLAR-0003-agent-node.md`,
  `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- `.factory-state/artifacts/REQ-0070-workflows-as-mcp-tools.md`, `.factory-state/artifacts/REQ-0071-durable-resume-after-restart.md`,
  `.factory-state/artifacts/REQ-0042-workflow-tests.md`, `.factory-state/artifacts/REQ-0051-time-travel.md`,
  `.factory-state/artifacts/REQ-0069-superstep-comparison-pages.md`
- `.factory-state/decisions/DEC-0018-effectively-once.md`, `DEC-0023-rbac-sharing.md`, `DEC-0044-workflow-test-runs.md`,
  `DEC-0065-validation-message-codes.md`
- `docs/backend-architecture.md` (DEC-0009), `docs/ui-conventions.md` (DEC-0008, DEC-0025)
