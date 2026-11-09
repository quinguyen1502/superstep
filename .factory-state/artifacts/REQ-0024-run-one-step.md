# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0024
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request 2026-10-18, “Can we allow running up to one step, to test?”

## Summary

The author can run a studio workflow one superstep at a time, look at the result, then take one more step or continue to the end.

## Problem Or Opportunity

Run always executes the whole graph. Trying the first node still spends the rest of the graph, including later model and tool calls.

## Scope

### In Scope

- A Step action on the editor, next to Run, for a workflow compiled in the studio.
- One step runs a single LangGraph superstep, then pauses that same run.
- From that pause, Step runs one more superstep, and Continue runs until the graph ends, a Human node waits, the run is cancelled, or it errors.
- With a node selected, Run to here runs from the start, or from the current pause, until that node has finished, then pauses. Nodes after it do not run.
- The pause is stored on the run and can be resumed from the open log or from history.

### Out Of Scope

- Editing state between steps.
- Stepping an imported repository graph. Those runs stay full-run only.
- `Command`, `Send`, `error_handler`, and `defer`.
- Changing what a normal Run does.

## Stakeholders Or Users

- Workflow authors testing a graph before a full run

## Current Context

- The editor starts a run over `/ws/run` with `{workflow_id, workflow, input}` and streams until `run_finished`, `error`, `run_cancelled`, or Human `run_waiting`.
- `engine/runtime.py` already yields a `_checkpoint` at each superstep. Human resume sends `{resume_run_id, response}` and continues that run.
- A superstep can contain several parallel nodes. Stored run statuses include `ok`, `error`, `cancelled`, `timeout`, and `waiting`.
- `waiting` is the Human approval state. It opens the approval panel, the pending-approval badge, and approval notifications.

## Desired Behavior

- Step uses the same input as Run. Invalid JSON still blocks the run and shows the existing input error.
- After one superstep, the nodes that ran are finished in the log and on the canvas. The run is not finished and no later node has started.
- The pause is not an approval. The Human panel, the pending-approval badge, and approval notifications stay quiet.
- Step again appends the next superstep to the same log and the same run.
- Continue appends the rest of the run to that log.
- Cancel still stops the run between steps.
- A linear graph Start → A → B → End pauses after A on the first step. A and B in one parallel superstep both finish before that step pauses.
- Run to here on B of that graph pauses after B. A and B are finished. End has not started.
- Run to here on a node the condition does not take finishes the path that did run and reports `RUN_NODE_NOT_REACHED`.

## Business Rules

- One step is one superstep, the same boundary the runtime already checkpoints. It is not one model token.
- A Human node still waits for a person. Step does not answer it.
- UI strings live in `en.json` and `vi.json` with the same keys.
- The new pause uses its own status and event. It must not reuse `waiting` or `run_waiting`.

## Constraints

- Routers stay thin. The engine does not import FastAPI.
- No new API error code unless validation of the step request cannot use an existing code. Any new code goes through `core/errors.py`, `docs/api-errors.md`, and both locale files.
- shadcn components and theme tokens only.

## Acceptance Criteria

- On a linear three-node graph, Step finishes the first working node and does not emit `run_finished`. A second Step finishes the next node. Continue then emits `run_finished`.
- Two nodes in one parallel superstep both finish in that single step.
- The approval panel and the pending-approval count do not appear for a step pause.
- Run with no step limit still runs to `run_finished`.
- An imported repository run has no Step action and no Run to here action.

## Edge Cases

- A superstep that is only Start does not consume the step. The first Step on Start → A → B → End still pauses after A.
- A graph that ends inside the stepped superstep finishes normally instead of pausing.
- Closing the socket while a step is in flight cancels, as a normal run does.
- A paused run left in history offers Step and Continue, not the Human response form.

## Assumptions

- The owner first accepted one superstep per Step. On 2026-10-18 they added Run to here: choose a node and run until it finishes.
- Designer and architect are skipped. The control sits with Run and reuses the checkpoint resume path.
- `factory ready` does not exit 0 on this machine (no PyYAML on system Python, no `textual` in the QA venv). The owner has accepted that for planning. Do not install packages to clear it.
- One task.

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0036-run-one-step.md`
- Review: `.factory-state/artifacts/REV-0035-task-0036.md`
- QA: `.factory-state/artifacts/QA-0035-task-0036.md`
- Pull request: https://github.com/quinguyen1502/langgraph-studio/pull/39
- Architecture: `.factory-state/artifacts/ARCH-0001-current-architecture.md`
- Runtime: `backend/app/engine/runtime.py`
- Run socket: `backend/app/api/routes/runs_ws.py`
