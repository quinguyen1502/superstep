---
schema_version: 1
id: CLAR-0003
task_id: REQ-0072
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0072-agent-node.md
  - .factory-state/artifacts/REQ-0011-mcp-tools.md
  - .factory-state/artifacts/REQ-0041-approval-deadlines-and-inbox.md
  - .factory-state/artifacts/REQ-0048-agent-chat.md
  - .factory-state/decisions/DEC-0018-effectively-once.md
created: 2026-10-25
updated: 2026-10-25
answered_at: null
questions:
  - id: tool-definition
    type: single_choice
    prompt: Where does the builder define the agent's tools?
    required: true
    context: >-
      Inline keeps one node with a tool list in its config panel, like Dify and Flowise; it is the smallest change
      to the validator, compiler and exports. Tool nodes on the canvas wired to the agent (n8n and Langflow style)
      show the tools in the graph and reuse the Tool, MCP and Retriever node panels, but they are nodes that do not
      run in the graph order, which the validator, the compiler, the exports and the trace must all special-case.
    recommendation: inline
    options:
      - value: inline
        label: A tool list inside the Agent node's settings (pick an MCP tool, a built-in, a knowledge base, or define an HTTP tool)
      - value: canvas
        label: Tool, MCP and Retriever nodes on the canvas, connected to the Agent node by a tool handle
      - value: both
        label: Inline now; canvas tool nodes later as a second task
    depends_on: null
  - id: approval-where
    type: single_choice
    prompt: Where can a tool call that needs approval be answered?
    required: true
    context: >-
      Human nodes already have a waiting step in the Approvals inbox, the run panel, Slack and Telegram, approvers by
      e-mail and deadlines (REQ-0034, REQ-0041). Reusing them means the Agent node carries the same approval settings
      once, for all its tools that need approval. The studio-only option is smaller but an approver must open the
      studio.
    recommendation: same-as-human
    options:
      - value: same-as-human
        label: Same as a Human node (inbox, run panel, channels, approvers, deadline), set once on the Agent node
      - value: studio-only
        label: Only in the studio (run panel and Approvals inbox), no channels or deadlines yet
    depends_on: null
  - id: approval-edit
    type: single_choice
    prompt: What can the approver do with a pending tool call?
    required: true
    context: >-
      Editing the arguments (LangGraph's "edit tool call") fixes a wrong amount or address without rerunning, but
      the channel messages only have Approve and Reject buttons today, so editing would work in the studio only.
    recommendation: approve-reject
    options:
      - value: approve-reject
        label: Approve or Reject, with an optional comment
      - value: edit-in-studio
        label: Approve or Reject anywhere; edit the arguments before approving in the studio
    depends_on: null
  - id: on-reject
    type: single_choice
    prompt: What happens when an approver rejects a tool call?
    required: true
    context: >-
      Telling the model lets it answer without the action ("I could not issue the refund, a reviewer declined it")
      and keeps the run going; the round counts. Failing the node is stricter and lets an error path in the graph
      handle it.
    recommendation: tell-model
    options:
      - value: tell-model
        label: The model gets "rejected by a reviewer" (and the comment) as the tool result and the loop goes on
      - value: fail-node
        label: The Agent node fails with an error code; the node's error settings decide what happens next
    depends_on: null
  - id: max-rounds
    type: single_choice
    prompt: What happens when the agent reaches the round limit?
    required: true
    context: >-
      A last call without tools usually gives a usable answer and costs one more model call. An error is the most
      predictable for tests and costs nothing more.
    recommendation: final-answer
    options:
      - value: final-answer
        label: One more model call without tools asks for a final answer; the trace marks that the limit was hit
      - value: error
        label: The node fails with an error code (for example AGENT_MAX_ROUNDS)
    depends_on: null
  - id: output
    type: single_choice
    prompt: What does the Agent node write to the state?
    required: true
    context: >-
      The final text in one field matches the LLM node. A second, optional field with the steps (tool, arguments,
      result) lets later nodes and test checks read what the agent did. Structured output with a schema is a bigger
      feature that also suits the LLM node.
    recommendation: answer-and-steps
    options:
      - value: answer-and-steps
        label: The final answer in the output field, and optionally the list of tool calls in a second field
      - value: answer-only
        label: Only the final answer in the output field
    depends_on: null
  - id: memory
    type: single_choice
    prompt: Does the agent read the chat history?
    required: true
    context: >-
      The chat (REQ-0048) puts earlier turns in a `messages` list field. Reading it makes a multi-turn chat agent
      work with one node; without it the prompt template must paste the history in as text.
    recommendation: messages-field
    options:
      - value: messages-field
        label: "Yes, optionally: a 'history field' setting (default `messages`) adds earlier turns before the task prompt"
      - value: prompt-only
        label: No, only the system and task prompts
    depends_on: null
  - id: export
    type: single_choice
    prompt: Which code exports must support the Agent node in the first version?
    required: true
    context: >-
      Python and the LangGraph project export share the Python writer, so they come together; the node becomes
      `create_react_agent` (or a model and ToolNode loop) with stubs like the existing `call_mcp_tool`. TypeScript
      needs its own writer with LangGraph.js; it could refuse the node with a clear error at first.
    recommendation: python-now
    options:
      - value: python-now
        label: Python and the LangGraph project now; TypeScript refuses the node with a clear error until a later task
      - value: all
        label: Python, the LangGraph project and TypeScript in the first version
    depends_on: null
answers: {}
---
# Clarification

Owner questions for REQ-0072 (Agent node). Each question has a recommended option; the requirement is written so
that the recommended answers fit it without a scope change.

The owner may answer it with:

```text
factory clarify CLAR-0003 -C <project-dir>
```

The implementing agent must propagate submitted answers into the related requirement, design, architecture, decision, or task artifacts.
