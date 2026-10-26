---
schema_version: 1
id: CLAR-0004
task_id: REQ-0073
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0073-agent-workflow-tools.md
  - .factory-state/artifacts/REQ-0072-agent-node.md
  - .factory-state/artifacts/REQ-0070-workflows-as-mcp-tools.md
  - .factory-state/decisions/DEC-0063-agent-node-expansion.md
  - .factory-state/decisions/DEC-0018-effectively-once.md
created: 2026-10-26
updated: 2026-10-26
answered_at: null
questions:
  - id: first-feature
    type: single_choice
    prompt: Which Agent feature comes next?
    required: true
    context: >-
      REQ-0072 left four things out of scope. A workflow as a tool also gives several agents working together (a
      supervisor calls specialist workflows that have their own Agent node), with no new node type, and each agent is
      built and tested on its own canvas. A hand-off (one agent passes the conversation to another and stops) needs
      new routing in the graph and in the chat. Code tools and "every tool of an MCP server" are smaller, but they do
      not give several agents.
    recommendation: workflow-tools
    options:
      - value: workflow-tools
        label: Another workflow as a tool (the supervisor pattern for several agents)
      - value: handoff
        label: Hand-off, where one Agent node passes the conversation to another Agent node and stops
      - value: code-tools
        label: Code tools, Python or TypeScript written in the Agent node
      - value: mcp-all-tools
        label: Every tool of an MCP server, without listing each one
    depends_on: null
  - id: run-mode
    type: single_choice
    prompt: How does a workflow tool run?
    required: true
    context: >-
      A linked child run is a run of its own: its own record, history, checkpoints and side-effect ledger, with a
      parent run id. The parent's tool step waits for it. It survives a restart without repeating finished child
      nodes, and it can pause at an approval. It needs a migration (a parent run id) and the most work. Running the
      child graph inside the tool step is simpler and faster, but a restart in the middle runs the whole child again,
      and the child cannot pause.
    recommendation: child-run
    options:
      - value: child-run
        label: A linked child run, which the parent's tool step waits for
      - value: inline-step
        label: Inside the tool step, in the same process, with no run record of its own
    depends_on:
      question: first-feature
      equals: workflow-tools
  - id: child-approval
    type: single_choice
    prompt: What happens when the child workflow needs an approval (a Human node, or an Agent tool that needs approval)?
    required: true
    context: >-
      Passing it up keeps specialist agents safe to reuse: the parent run waits too, and the Approvals inbox and the
      channels show the child's request with both workflow names. This needs a linked child run. Refusing it in the
      validator is simpler but rules out a specialist that sends a refund or an e-mail.
    recommendation: pass-up
    options:
      - value: pass-up
        label: The parent run waits too; the request shows in the inbox and channels as usual
      - value: refuse
        label: The validator refuses workflow tools whose workflow can pause
    depends_on:
      question: first-feature
      equals: workflow-tools
  - id: version
    type: single_choice
    prompt: Which version of the child workflow does a call run?
    required: true
    context: >-
      Subgraph nodes use the child's latest saved version when the run starts. Pinning a version makes the parent's
      behaviour stable while someone edits the specialist, but the builder has to move the pin by hand.
    recommendation: latest
    options:
      - value: latest
        label: The latest saved version when the parent run starts, as for Subgraph nodes
      - value: pinned
        label: A version picked on the tool, changed by hand
    depends_on:
      question: first-feature
      equals: workflow-tools
  - id: trace
    type: single_choice
    prompt: How does the parent's trace show a workflow tool call?
    required: true
    context: >-
      Nested shows the child's steps under the tool call in the parent's trace (as subgraph steps show as "Sub ›
      Node"), plus a link to the child run. Link-only keeps the parent trace short; the child's steps are one click
      away.
    recommendation: nested
    options:
      - value: nested
        label: The child's steps under the tool call, plus a link to the child run
      - value: link-only
        label: The tool call with its result and a link to the child run
    depends_on:
      question: first-feature
      equals: workflow-tools
  - id: exports
    type: single_choice
    prompt: Which code exports support workflow tools in the first version?
    required: true
    context: >-
      Both exports already write Agent nodes (TASK-0119, TASK-0125). A workflow tool becomes the child's own compiled
      graph in the same file, invoked by the tool function. Doing only Python first follows the order of REQ-0072.
    recommendation: python-and-typescript
    options:
      - value: python-and-typescript
        label: Python, the LangGraph project and TypeScript
      - value: python-now
        label: Python and the LangGraph project; TypeScript refuses with a clear error code for now
    depends_on:
      question: first-feature
      equals: workflow-tools
answers: {}
---
# Clarification

Owner questions for REQ-0073 (the next Agent feature). The recommended options are the ones REQ-0073 is written
for. If question 1 picks another feature, REQ-0073 is rewritten for it and questions 2 to 6 no longer apply.

The owner may answer in chat ("theo đề xuất", or one answer per question), or with:

```text
factory clarify CLAR-0004 -C <project-dir>
```
