---
schema_version: 1
id: CLAR-0009
task_id: REQ-0078
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0078-agent-handoff.md
  - .factory-state/decisions/DEC-0063-agent-node-expansion.md
  - .factory-state/decisions/DEC-0052-web-chat-model.md
created: 2026-10-27
updated: 2026-10-27
answered_at: null
questions:
  - id: targets
    type: single_choice
    prompt: Which nodes can an Agent node hand off to?
    required: true
    context: >-
      Agent nodes of the same workflow keep everything in one run, one trace and one checkpoint history. Another
      workflow is already reachable as a workflow tool. A Human node as a target ("talk to a person") is useful, but it
      needs its own chat behaviour, so it can come later through the same list.
    recommendation: same-workflow-agents
    options:
      - value: same-workflow-agents
        label: Other Agent nodes of the same workflow
      - value: agents-and-human
        label: Other Agent nodes and Human nodes of the same workflow
  - id: context
    type: single_choice
    prompt: What does the target agent see of the conversation?
    required: true
    context: >-
      The whole conversation (the person's messages, the earlier agent's replies and its tool results) is what
      langgraph-swarm and the OpenAI Agents SDK pass by default, and nothing is lost. Without the tool results the
      prompt is shorter, and the target does not see tools it cannot call. A model-written summary costs an extra call
      and can drop details.
    recommendation: messages-without-tools
    options:
      - value: messages-without-tools
        label: The person's messages and the agents' replies, without tool calls and results, plus the hand-off reason
      - value: everything
        label: The whole conversation, tool calls and results included
      - value: summary
        label: A summary written by the handing-off agent
  - id: chat-state
    type: single_choice
    prompt: In a chat, who answers the next message after a hand-off?
    required: true
    context: >-
      Keeping the agent that answered last is what people expect after "I'll pass you to billing". It needs the session
      to remember that agent and the next run to start there. Always starting at the entry agent is simpler, since the
      entry agent sees the history and can hand off again, but it costs a model call per message and can bounce the
      person around.
    recommendation: keep-last
    options:
      - value: keep-last
        label: The agent that answered last, until it hands off again
      - value: entry-agent
        label: Always the workflow's entry agent, which sees the history
  - id: limit
    type: single_choice
    prompt: How many hand-offs may one run make?
    required: true
    context: >-
      A limit stops two agents from handing a person back and forth forever. 5 per run is plenty for a triage and a
      second opinion. Past it, the hand-off tools are removed and the agent must answer.
    recommendation: five-setting
    options:
      - value: five-setting
        label: 5 per run by default, a workflow setting can change it
      - value: three-fixed
        label: 3 per run, fixed
  - id: canvas
    type: single_choice
    prompt: How does the canvas show hand-offs?
    required: true
    context: >-
      Dashed links from an agent to its targets make the routing visible, the way Condition branches are, and dragging
      a link from one agent to another could add a target. Listing them only in the node's settings is less work, but
      the canvas would hide where a conversation can go.
    recommendation: dashed-links
    options:
      - value: dashed-links
        label: Dashed links between agents, kept in sync with the node's target list
      - value: settings-only
        label: Only in the node's settings, with a badge on the node
  - id: exports
    type: single_choice
    prompt: Which code exports support hand-offs in the first version?
    required: true
    context: >-
      All three exports already write Agent nodes and workflow tools. A hand-off becomes a LangGraph Command(goto=...)
      in Python and the LangGraph project, and the equivalent in TypeScript. Doing all three keeps the exports in step
      with the studio, as for REQ-0073.
    recommendation: all
    options:
      - value: all
        label: Python, the LangGraph project and TypeScript
      - value: python-first
        label: Python and the LangGraph project; TypeScript refuses with a clear error code for now
answers: {}
---
# Clarification

Owner questions for REQ-0078, which lets an Agent node hand the conversation off to another Agent node. Each question
has a recommended option. The owner can answer in chat (for example, "trả lời CLAR-0009 theo đề xuất"), or by editing
the `answers` map.

The owner may answer it with:

```text
factory clarify CLAR-0009 -C <project-dir>
```
