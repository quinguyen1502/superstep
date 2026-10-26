# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0066
- Status: Proposed (accepted with the first task's start, as DEC-0063 was)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Related Requirements: REQ-0073 (CLAR-0004), REQ-0072, REQ-0070, REQ-0071, REQ-0042, REQ-0051
- Related Architecture: DEC-0009 (layers), DEC-0018 (effectively-once), DEC-0023 (resources of the owner), DEC-0044
  (test runs), DEC-0063 (Agent node expansion), DEC-0065 (validation message codes)
- Related Tasks: TASK-0133, TASK-0134, TASK-0135, TASK-0136, TASK-0137, TASK-0138

## Context

- REQ-0073 adds a fifth Agent tool source, **workflow**: the model calls another saved workflow by name. The owner
  chose (CLAR-0004) a linked child run that the parent's tool step waits for, approvals inside the child passed up,
  the child's latest saved version taken when the parent run starts, a nested trace, and all three exports.
- An Agent tool call is already one LangGraph step, `A/__tool`, with its own checkpoint, ledger entry and idempotency
  key (DEC-0063). A Human node or an approval makes it raise `Interrupt`; `runtime.run_stream` hands back a
  checkpoint and `RunService` records the run as `waiting`. A resume job continues it, kept on the run until the
  resumed segment records something (TASK-0127).
- Every run segment ends in `RunService.settled()` (API callback, test suite, chat thread). The job queue is in
  memory or on Redis (`services/job_queue.py`), and `RunWorker.recover_unfinished` continues runs after a restart
  (REQ-0071).
- Subgraph nodes (`engine/subgraphs.py`) load other workflows through a loader bound to the workflows the user may
  read, check cycles and depth (`MAX_DEPTH` 5), and refuse imported workflows. REQ-0070 derives a workflow's input
  schema from its state fields (`engine/state_schema.state_schema`).

## Decision

1. **Tool settings.** A workflow tool is `{name, description, source: "workflow", workflow_id, inputs: [field],
   outputs: [field], approval?}`. `parameters()` is the JSON Schema of the child's state fields listed in `inputs`
   (from `state_schema`, so the types match REQ-0070). The result is `{field: value}` of the child's final state for
   the fields in `outputs`, shortened like any tool result.
2. **The child is snapshotted when the parent run is planned.** The expansion step that resolves subgraphs also
   resolves workflow tools, through the same loader: it copies the child's latest saved workflow (and its version
   number) into the tool's settings in the expanded copy, as `snapshot` and `version`, recursively. The parent's
   checkpoint therefore carries the child definitions, so a pause, a restart or a resume runs the same version, and
   the tool step needs no loader at run time. Cycles and depth are checked across subgraphs and workflow tools
   together (`MAX_DEPTH` 5) when saving and when planning.
3. **A call starts a linked child run and the tool step waits.** On the first execution of a workflow call,
   `A/__tool` calls a new port, `ports.start_child(key, workflow, version, input) -> run_id`, and raises a new engine
   exception `AwaitChild(step, run_id)`, a sibling of `Interrupt`. `runtime.run_stream` hands back a checkpoint for
   it as for an interrupt, and `RunService` records the parent as `waiting` with `checkpoint.wait = {kind: "child",
   run_id}`. No approval request or notification is made for the parent itself.
4. **Child runs are ordinary runs with a parent.** A migration adds `runs.parent_run_id` (indexed) and
   `runs.parent_step` (the call key `<step>#<iteration>#<call id>`), unique together. The child is a queue job with
   source `tool`, the parent's owner, and the parent's resource owner (DEC-0023: an inlined subgraph would use the
   parent's credentials, so a child does too). A test run's child inherits `test` and `mock_models` (DEC-0044); the
   demo rules apply as for any run. The child has its own events, checkpoints, ledger, history entry, timeout and
   recovery after a restart.
5. **Effectively once.** `start_child` looks up the call key first and returns the existing child, so a parent that
   is recovered or retried before it recorded `waiting` never starts a second child. When a run with a parent
   settles (`ok`, `error`, `cancelled`, `timeout`, `expired`), `settled()` queues a resume job for the parent with
   `enqueue_resume` and the value `{child_run_id, status, output | error, usage}`. A resume whose parent is no longer
   waiting for that child is dropped, so a repeated settle is harmless. On resume, `A/__tool` turns the value into the
   tool result (an error status becomes an error result for the model), adds the child's usage and cost to the Agent
   node, and records the step as usual.
6. **Approvals are passed up by waiting.** A child that pauses (a Human node, an Agent tool approval) is a waiting run
   like any other, so the inbox, the channels and the deadlines handle it unchanged. Its approval request carries the
   chain of workflow names from the top parent down ("Support team › Refund desk"), read through `parent_run_id`. The
   parent stays `waiting` for the child and is never itself an approval. When the child ends, decision 5 resumes the
   parent.
7. **Cancel, timeout and limits.** Cancelling a parent cancels its running or waiting children (and theirs). A
   parent's timeout covers its own segments; a child has its own run timeout, and a parent waiting for a child is not
   running, as when it waits for a person. The work a supervisor can start is bounded by the Agent limits (rounds ×
   calls per round) and the depth limit; at run time a child whose parent chain is already `MAX_DEPTH` deep fails
   with `WORKFLOW_TOOL_TOO_DEEP`.
8. **Trace and runs.** The parent's `node_finished` for the tool step carries `child_run_id`. The studio and the
   chat's `full` view fetch the child's events (the run API, with the same access check) and show them under the
   tool call, with a link to the child run. A child run shows its parent; the history lists child runs under their
   own workflow with a "called by" link. A waiting parent shows "waiting for <child workflow>".
9. **Exports.** Each child workflow becomes its own compiled graph in the same file (`build_<slug>()` in Python,
   `build<Slug>()` in TypeScript), written once even when several tools use it. The tool function invokes it with
   the arguments and returns the output fields. Inside a parent graph with a checkpointer, an interrupt in the child
   pauses the parent, which is the same "passed up" behaviour.

## Alternatives Considered

- **Run the child inside the tool step** (no run record). Simpler, but a restart runs the whole child again, the
  child cannot pause, and its trace would live only inside the parent (CLAR-0004 question 2).
- **Expand the child inline as a subgraph under the tool step.** Its nodes would checkpoint with the parent, but the
  model chooses when and how often to call it at run time, while expansion happens before compilation; the same
  workflow called twice in a round would need dynamic graph growth.
- **Call the studio's own MCP endpoint (REQ-0070).** Needs a workflow token per child, a network round trip, and the
  child would not be linked to the parent's trace or cancel.
- **Block the parent's worker while the child runs.** Ties up a worker per nesting level and loses the wait on a
  restart; waiting as a checkpoint uses the existing pause and resume path instead.

## Consequences

- The tool step, the pause, the resume job and restart recovery are the existing mechanisms; the new parts are the
  `AwaitChild` hand-back, `start_child`, the resume from `settled()`, and the cancel cascade.
- One migration (`parent_run_id`, `parent_step`). Runs without a parent are unchanged.
- Each call creates a run row, so the history of a specialist workflow also shows the calls made by supervisors.
- A deleted child workflow does not break a waiting parent, whose snapshot holds the child; the next save reports it.
