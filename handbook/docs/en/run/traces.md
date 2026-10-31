# Runs and traces

## The Logs timeline

![Run trace](../images/run-trace.png)

The logs in the **Run** tab have one row per node step: status, name, kind, duration, a
waterfall bar, and tokens when the model reports them. Loops show `#2`, `#3`
and so on. The summary line shows the run status, duration, steps, input and
output tokens, cost and error count.

Click a row, or a node on the canvas, to open its detail:

| Tab | Shows |
| --- | --- |
| Input | The state the node received |
| Output | What it returned (streamed tokens for an LLM node while it runs) |
| State diff | Fields added, changed or removed by this step |
| Raw | The step's original events |

![State diff](../images/trace-detail.png)

An [Agent node](../guide/agent.md#trace-and-usage) shows its steps under it:
`Agent › model` rows with the round and the tools it called or its answer, and
`Agent › tool` rows with the tool, a shortened result, and **approved** or
**rejected by a reviewer** when a person answered.

**Raw events** switches the whole timeline to the original event stream. Pick
an earlier run in the run menu next to the tabs (the last 10), or in **View
all**, to replay it on the same timeline, labelled with its version.

## Stepping

| Control | Effect |
| --- | --- |
| **Step** | Runs one superstep, then pauses the same run (status `paused`). |
| **Continue** | Runs the rest. |
| **Run to here** | Select a node first. Runs until that node finishes, then pauses. If the path never reaches it, the run finishes and says so. |

A pause is not a human approval. A superstep that is only Start does not use
up the step.

## Time travel: fork from a checkpoint

Open a finished run (or pick one in **View all runs**) and press **Time travel**
above its timeline. The dialog lists the run's checkpoints: one per step, named
after the nodes that ran next ("Before Approved?"), with the state they started
from, and last the final state.

1. Pick a checkpoint to inspect its state.
2. Optionally edit the state (it must stay a JSON object). **Reset** puts the
   recorded state back.
3. Press **Fork from here**. A new run starts at those nodes with that state;
   the nodes before it do not run again. Its timeline shows **Forked from**
   the original run and checkpoint. The original run is not changed.

A fork runs the workflow version the original run ran when that version is
stored, else the saved workflow. Iteration counts (loop limits) carry over.
Checkpoints whose state was too large to record, the final state, runs of
imported LangGraph graphs and runs still waiting or running cannot be forked.
Only the run's owner (or the workflow's owner and admins) can see its
checkpoints.

```text
GET  /api/runs/{run_id}/checkpoints
WS   /ws/run   {"fork": {"run_id": "...", "checkpoint": 1, "state": {...}}}   (state is optional)
```

## Cancel

**Cancel** (++ctrl+period++) sends `{"type": "cancel"}`. Closing the tab also
cancels. Cancel is cooperative: it stops between steps, so an LLM or HTTP call
already in flight may finish. A Code node's container is killed.

## Statuses

| Status | Meaning |
| --- | --- |
| `ok` | Reached End. |
| `error` | A node failed after its retries, or validation failed. |
| `cancelled` | Stopped by a person or a closed tab. |
| `timeout` | Ran past `STUDIO_RUN_TIMEOUT`. |
| `paused` | Stopped by Step or Run to here. |
| `waiting` | At a Human node. |
| `expired` | Waited longer than `STUDIO_WAIT_TTL`. |

Errors are one line, with `sk-…`, `Bearer …` and `api_key=…` redacted.

## Limits

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_RECURSION_LIMIT` | 25 | Max steps per run. A loop that never passes a Condition stops with an error. For each steps do not count. |
| `STUDIO_RUN_TIMEOUT` | 120 s | Max duration of a run, then `timeout`. Waiting at a Human node does not count, and neither does the setup before the first node (such as saving the first progress checkpoint). |
| `STUDIO_EVENT_MAX_BYTES` | 262144 | Max size of one event. Oversized fields become `{"_truncated": true, …}`. |
| `STUDIO_RUN_MAX_BYTES` | 2097152 | Max stored events per run. The middle is replaced by `{"type": "truncated", "dropped": n}`. |
| `STUDIO_INPUT_MAX_BYTES` | 262144 | Max run input. |
| `STUDIO_WORKFLOW_MAX_BYTES` | 1048576 | Max workflow JSON. Larger saves return HTTP 413. |

The timeline also clips `input` and `delta` at 16 000 JSON characters so the
page stays light.

## Tokens and cost

Cost is computed from the token counts and a price table in
`backend/app/engine/usage.py`. The mock estimates tokens and costs `$0`. A
model missing from the table shows `—`. Override prices in USD per million
tokens with `STUDIO_PRICES='{"my-model": [1.0, 2.0]}'` (input, output) or
`STUDIO_PRICES_FILE`; the longest matching prefix wins.

## Export to a tracing backend

Each run can also become an OpenTelemetry trace in Jaeger, Tempo or
LangSmith, with an **Open trace** link in the timeline. See
[Observability](../operate/observability.md).
