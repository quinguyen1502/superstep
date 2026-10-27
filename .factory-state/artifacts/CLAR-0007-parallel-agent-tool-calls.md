---
schema_version: 1
id: CLAR-0007
task_id: REQ-0076
status: open
source_artifacts:
  - .factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md
  - .factory-state/decisions/DEC-0063-agent-node-expansion.md
  - .factory-state/decisions/DEC-0066-workflow-tools-child-runs.md
  - .factory-state/decisions/DEC-0018-effectively-once.md
created: 2026-10-27
updated: 2026-10-27
answered_at: null
questions:
  - id: default
    type: single_choice
    prompt: Do an Agent node's tool calls run in parallel by default?
    required: true
    context: >-
      Models ask for several calls in one round only when they judge them independent, and LangGraph's ToolNode and the
      OpenAI Agents SDK run them in parallel by default. A builder whose tools must run in order (for example "create",
      then "send") can turn it off per node, and then the provider is asked for one call at a time. Off by default would
      keep every existing workflow exactly as it is, but most builders would never find the setting.
    recommendation: on-with-setting
    options:
      - value: on-with-setting
        label: On by default, with a per-node setting to turn it off
      - value: off-with-setting
        label: Off by default, with a per-node setting to turn it on
      - value: always
        label: Always on, with no setting
  - id: cap
    type: single_choice
    prompt: How many calls of one round may run at once?
    required: true
    context: >-
      A cap protects the tools' servers and the worker's threads. 4 covers the rounds models produce in practice. An
      operator who needs more can raise it with an environment variable. With no cap, one round could start dozens of
      HTTP calls or child runs.
    recommendation: four-env
    options:
      - value: four-env
        label: 4 by default, set by STUDIO_AGENT_PARALLEL_TOOLS
      - value: node-setting
        label: A number on each Agent node (default 4)
      - value: unlimited
        label: No cap
  - id: approvals
    type: single_choice
    prompt: How are approvals asked when several calls of one round need one?
    required: true
    context: >-
      One approval per call works with the inbox, channels and deadlines unchanged, since each call is its own step
      that pauses like a Human node in a parallel branch. One approval for the whole round is quicker for the reviewer,
      but it needs a new kind of approval that lists several calls, and a rejection would cover all of them.
    recommendation: per-call
    options:
      - value: per-call
        label: One approval per call, as today; the other calls run meanwhile
      - value: per-round
        label: One approval that lists every call of the round
  - id: failures
    type: single_choice
    prompt: What happens to the other calls when one call of a round fails?
    required: true
    context: >-
      Today a failed call gives the model an error result and the agent goes on, so the model can retry or answer
      without it. Keeping that for every call of a round is the same rule. Cancelling the others would waste work
      already done and differ from the sequential behaviour.
    recommendation: finish-all
    options:
      - value: finish-all
        label: The other calls finish; the model gets every result, errors included
      - value: cancel-rest
        label: Cancel the calls still running and give the model the error
  - id: exports
    type: single_choice
    prompt: How do the code exports run a round's calls?
    required: true
    context: >-
      The Python and LangGraph project exports can run them concurrently with a thread pool, and TypeScript with
      Promise.all, which keeps exported code behaving like the studio. Keeping them sequential in the exports is less
      work, but the exported workflow would be slower than in the studio.
    recommendation: concurrent
    options:
      - value: concurrent
        label: Concurrently in Python, the LangGraph project and TypeScript, honouring the node setting
      - value: sequential
        label: One after another in the exports for now
answers: {}
---
# Clarification

Owner questions for REQ-0076, which runs the tool calls of one Agent round at the same time. Each question has a
recommended option. The owner can answer in chat (for example, "trả lời CLAR-0007 theo đề xuất"), or by editing the
`answers` map.

The owner may answer it with:

```text
factory clarify CLAR-0007 -C <project-dir>
```
