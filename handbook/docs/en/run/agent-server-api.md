# LangGraph-compatible API

Superstep answers a subset of the
[LangGraph Agent Server API](https://docs.langchain.com/langsmith/server-api-ref)
at `/api/lg`. Code written for LangGraph, with the official `langgraph-sdk`
client or `RemoteGraph`, can run Superstep workflows without changes: point it
at your studio instead of an Agent Server.

| LangGraph | Superstep |
| --- | --- |
| Assistant / graph | A workflow. `assistant_id` and `graph_id` are the workflow id (from the editor URL). |
| Thread | A conversation of runs of one workflow. Its state is the state of its latest run. |
| Run | An API run of the latest saved version. It shows in the workflow's history. |
| Interrupt | A Human node waiting for an answer. |

## Connect

Use a workflow token (only that workflow) or your sign-in token (every
workflow you may run). The SDK sends `api_key` as the `x-api-key` header;
`X-Workflow-Token` and `Authorization: Bearer` work too.

```python
from langgraph_sdk import get_client

client = get_client(url="https://superstep.example.com/api/lg", api_key="wft_...")

assistants = await client.assistants.search()
thread = await client.threads.create(metadata={"customer": "c-42"})
result = await client.runs.wait(thread["thread_id"], "example", input={"message": "Where is order A100?"})
print(result["answer"])
```

Stream the run node by node:

```python
async for part in client.runs.stream(thread["thread_id"], "example",
                                     input={"message": "hello"}, stream_mode=["updates", "values"]):
    print(part.event, part.data)
```

Or use the workflow as a node of your own LangGraph graph:

```python
from langgraph.pregel.remote import RemoteGraph

support = RemoteGraph("example", url="https://superstep.example.com/api/lg", api_key="wft_...")
print(support.invoke({"message": "hello"}))
```

## Human nodes

When a run reaches a Human node, the thread becomes `interrupted` and
`runs.wait` returns the state with `__interrupt__`:

```python
out = await client.runs.wait(thread["thread_id"], wid, input={"message": "refund order A100"})
print(out["__interrupt__"][0]["value"])  # {"node": "ask", "question": "Approve refund ...?"}

done = await client.runs.wait(thread["thread_id"], wid, command={"resume": "approved"})
```

The answer is text, or `true` / `false` for approved / rejected, as in the
[Human approval](human-approval.md) inbox. The same waiting run also shows in
the inbox and in approval channels, so a person can answer it there instead.

## What is supported

| Endpoint | Notes |
| --- | --- |
| `POST /assistants/search`, `GET /assistants/{id}` | The workflows you may run |
| `GET /assistants/{id}/graph`, `GET /assistants/{id}/schemas` | The canvas as a LangGraph graph; schemas from the state fields |
| `POST /threads`, `GET /threads/{id}`, `POST /threads/search`, `DELETE /threads/{id}` | |
| `GET /threads/{id}/state`, `POST /threads/{id}/history` | History has one entry: the current state |
| `POST /threads/{id}/runs`, `/runs/wait`, `/runs/stream` | Also without a thread: `POST /runs`, `/runs/wait`, `/runs/stream` |
| `GET /threads/{id}/runs`, `GET /threads/{id}/runs/{run_id}`, `.../join`, `.../cancel` | |

Behaviour to know:

- A new run on a thread starts from the thread's state with the new input on
  top. A thread runs one workflow, and one run at a time (`409 THREAD_BUSY`).
- `stream_mode` supports `values` (the default) and `updates`. Other modes send
  nothing.
- Not supported: creating or editing assistants, crons, the store, editing
  thread state, checkpoints by id, `interrupt_before` / `interrupt_after`.
- Errors use the usual [error envelope](../reference/errors.md) and HTTP status.

## LangSmith Studio and Agent Chat UI

Not verified. Both run in the browser at another origin, so the studio must
allow it in `STUDIO_CORS_ORIGINS`, and they call endpoints this subset does not
have (checkpoint history, assistant versions). Agent Chat UI also expects a
`messages` list in the state. To work on a workflow in Studio, export it as a
[LangGraph project](../guide/python-export.md) and run `langgraph dev`.
