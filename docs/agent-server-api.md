# LangGraph Agent Server API (subset)

Superstep serves a subset of the [LangGraph Agent Server API](https://docs.langchain.com/langsmith/server-api-ref)
under `/api/lg`, so LangGraph clients (the `langgraph-sdk` Python and JS clients, `RemoteGraph`) can run Superstep
workflows as if they were graphs on an Agent Server.

## Decisions

- **Path:** `/api/lg`. It rides the same proxy rules as the rest of the API (Vite, nginx, PaaS), so no deployment
  change is needed. Clients use `<studio>/api/lg` as the server URL.
- **Bodies:** the Agent Server shapes (no `{success, data, error}` envelope), because the clients read them as is.
  Errors keep the error envelope and the usual HTTP status; the clients raise on the status.
- **Auth:** a workflow token (`wft_…`, only its workflow and the threads it created) or a user JWT (every workflow the
  user may run, and the user's own threads), in `x-api-key` (what the SDK sends for `api_key`), `X-Workflow-Token`
  or `Authorization: Bearer`. Runs started with a token count against the token's rate limit.
- **Assistants** are workflows: `assistant_id` = `graph_id` = the workflow id. One assistant per workflow, version 1;
  creating or updating assistants is not supported.
- **Threads** are stored in `agent_threads`; a thread's state is the state of its latest run. A new run on a thread
  starts the workflow from that state with the run's `input` on top (a shallow merge). A thread is bound to the
  workflow of its first run.
- **Runs** are ordinary queued API runs (history source `api`, webhook-free), linked to their thread in
  `agent_thread_runs`; the run id is the Superstep run id. One run at a time per thread (`multitask_strategy`
  `reject`, `409 THREAD_BUSY`).
- **Human nodes:** a waiting run makes the thread `interrupted`; `runs.wait` returns the state with `__interrupt__`
  (`[{id, value: {node, question}}]`), `get_state` has `next` and `tasks[].interrupts`. A run with
  `command={"resume": answer}` (text, or true / false) continues the same Superstep run.
- **Streaming:** `stream_mode` `values` (default) and `updates`, from the run's saved progress (polled every 0.25 s,
  so a worker on another process streams too). Other modes (`messages`, `debug`, `events`, …) send nothing.

## Endpoints

| Endpoint | Notes |
| --- | --- |
| `GET /info`, `GET /ok` | Server info and health |
| `POST /assistants/search`, `GET /assistants/{id}` | Workflows the caller may run |
| `GET /assistants/{id}/graph`, `GET /assistants/{id}/schemas` | Drawable graph JSON; JSON schemas from the state fields |
| `POST /threads`, `GET /threads/{id}`, `POST /threads/search`, `DELETE /threads/{id}` | `metadata`, `if_exists` |
| `GET /threads/{id}/state`, `POST /threads/{id}/history` | History has one entry: the current state |
| `POST /threads/{id}/runs`, `POST /runs` | Start in the background (`/runs`: a new thread) |
| `POST /threads/{id}/runs/wait`, `POST /runs/wait` | Wait for the result |
| `POST /threads/{id}/runs/stream`, `POST /runs/stream` | Server-sent events |
| `GET /threads/{id}/runs`, `GET /threads/{id}/runs/{run}`, `GET …/join`, `POST …/cancel` | |

Not implemented: assistant create / update / versions, crons, the store, thread copy / patch / state update,
checkpoints by id, `interrupt_before` / `interrupt_after`, and webhooks on runs.

## Verification

`tests/test_agent_server_api.py` drives the API with the SDK's own client classes; `scripts/agent_server_smoke.py`
starts a backend and checks it over the network with `langgraph_sdk.get_client` and `RemoteGraph`.
