# Changelog

All notable changes to Superstep. Versions follow [Semantic Versioning](https://semver.org/); dates are in UTC+7.

## Unreleased

### Added

- **Workflows as MCP tools.** An MCP server at `/mcp` (official MCP Python SDK, Streamable HTTP, stateless JSON
  responses). Turn it on per workflow under **API > MCP** (off by default; route `GET`/`PUT
  /api/workflows/{wid}/mcp`); clients authenticate with the workflow's token (`Authorization: Bearer wft_...` or
  `X-Workflow-Token`) and get `run_<workflow>` (input schema from the state fields), `get_run` and `resume_run`
  (answers a run paused at a Human node). The tab copies a config for Cursor, Claude Desktop (via `mcp-remote`) or
  Claude Code. New error code `MCP_SERVER_DISABLED`. Handbook page Workflows as MCP tools (en, vi).
- **Handbook: two comparison pages** (en, vi), next to Superstep vs LangSmith. **Superstep vs visual builders**
  compares Superstep with n8n, Dify, Langflow and Flowise (what runs under the canvas, license, hosting, human in the
  loop, durable runs, evals and observability, API and code export). **Superstep vs agent frameworks** compares
  Superstep plus LangGraph with the code-first frameworks CrewAI and PydanticAI. Both cite each project's docs and
  license file and say when to choose another tool.

## 0.6.0 (2026-10-24)

### Added

- **Handbook: Superstep vs LangSmith** (en, vi). A comparison with LangSmith Studio and LangSmith Agent Builder
  (what each is for, pricing and hosting, how the LangGraph interop features work with LangSmith), citing
  LangChain's Studio docs, pricing page, self-hosted overview and the Agent Builder GA post.
- **Time travel in the Run panel.** **Time travel** on a finished run lists its checkpoints (the nodes that ran
  next and the state before them, then the final state); inspect or edit a state and **Fork from here** to start
  a new run at those nodes. The fork runs the original run's stored version, keeps iteration counts and records
  `forked_from` on its `run_started` event. Route `GET /api/runs/{run_id}/checkpoints`, WebSocket request
  `{"fork": {run_id, checkpoint, state?}}`; error codes `CHECKPOINT_NOT_FOUND`, `RUN_FORK_UNSUPPORTED`.
- **LangSmith evals and trace links (opt-in).** With `LANGSMITH_API_KEY` set and the admin setting **Send test
  results to LangSmith** on, each finished workflow test run goes to LangSmith: the test cases as a dataset (kept
  in sync) and the run as an experiment with `passed` and per-check feedback; a **LangSmith** menu (Open in
  LangSmith, Send to LangSmith) in the Tests panel, whose toolbar now uses one outline style and default sizes. Runs traced to LangSmith (`LANGSMITH_TRACING=true`) link to their LangSmith
  trace when `STUDIO_TRACE_URL` is not set. Routes `GET|PUT /api/admin/langsmith`,
  `POST /api/workflows/{wid}/tests/runs/{sid}/langsmith`; columns `runs.trace_root`,
  `workflow_test_suites.langsmith_url` (migration 0037); error codes `LANGSMITH_NOT_CONFIGURED`,
  `LANGSMITH_PUSH_FAILED`.
- **LangGraph Agent Server API (subset) at `/api/lg`.** The official `langgraph-sdk` clients and `RemoteGraph` can
  run Superstep workflows: assistants (one per workflow: search, get, graph, schemas), threads (create, get, search,
  delete, state, history), runs (create, wait, stream with `values` / `updates`, get, list, join, cancel, also
  without a thread), Human nodes as interrupts resumed with `Command(resume=...)`. Auth with a workflow token or a
  user JWT (`x-api-key`, `X-Workflow-Token` or `Authorization: Bearer`). New tables `agent_threads` and
  `agent_thread_runs` (migration 0036), error codes `THREAD_NOT_FOUND`, `THREAD_EXISTS`, `THREAD_BUSY`,
  `THREAD_WORKFLOW_MISMATCH`. Handbook page **LangGraph-compatible API** (en, vi); design in
  `docs/agent-server-api.md`; live check `scripts/agent_server_smoke.py`.
- **LangGraph project export.** The Code tab's **Project .zip** button (and
  `GET /api/workflows/{wid}/export/{language}/project`) saves the Python or LangGraph.js export as a runnable project:
  `langgraph.json`, the graph module with a module-level `graph`, `requirements.txt` + `pyproject.toml` or
  `package.json`, `.env.example` and a README. It runs with `langgraph dev` (Python `langgraph-cli[inmem]`, JS
  `@langchain/langgraph-cli`) and opens in LangSmith Studio; `scripts/langgraph_dev_smoke.py` checks both with the
  official `langgraph-sdk`.
- **Public API and SDKs.** The two workflow-trigger routes (`POST /api/hooks/workflows/{wid}/runs`,
  `GET /api/hooks/workflows/{wid}/runs/{run_id}`) now have a full OpenAPI contract: `WorkflowToken` (`X-Workflow-Token`)
  and `WorkflowBearer` security schemes, typed request and response models, error-envelope responses with examples,
  operation ids `startRun` / `getRun` and a `public` tag. A public-only spec is served at `/openapi.public.json` with a
  Swagger view at `/docs/public`, and committed as `docs/api/openapi.public.json` by `scripts/gen_public_openapi.py`
  (a test fails when it is stale). An async start now also sends the poll URL in the `Location` header.
- **Python SDK** (`sdk/python`, package `superstep`): sync and async clients on httpx, typed models, `run`, `get_run`,
  `wait`, `run_and_wait` with timeout and poll backoff, errors typed by error code, env var fallback.
- **TypeScript SDK** (`sdk/typescript`, `@superstep/sdk`): fetch-based, zero runtime dependencies, ESM and CommonJS,
  types generated from the public spec (`npm run gen`), `run`, `getRun`, `wait`, `runAndWait`, AbortSignal support.
- Both SDKs have unit tests and a live test against a local backend (`scripts/sdk_integration.sh`), run on CI; a
  tag-triggered publish workflow (`sdk-py-v*`, `sdk-ts-v*`) is ready but needs the registry setup in `sdk/README.md`.
- Handbook: **Public API and SDKs** guide and a **Public API reference** page rendered from the spec with a vendored
  Redoc bundle (works offline), in English and Vietnamese.

### Changed

- The offline mock model answers in the requester's UI language: English by default, Vietnamese when the studio is in
  Vietnamese (the studio sends `locale` with run and chat requests; `Accept-Language` is the fallback). The example
  `lookup_order` tool follows it too, and exported code's mock now answers in English. README overview screenshots
  regenerated, so the English one shows English replies.
- Public demo: each "Try the demo" sign-in gets an anonymous visitor account of its own, so run history, chats, waiting
  runs and notifications are no longer shared between visitors; the samples stay shared and read-only. Visitors older
  than `STUDIO_DEMO_VISITOR_TTL` (default one day) are removed with their runs and chats.

### Fixed

- Flaky tests: the parallel Human-sibling test accepts both valid orders (LangGraph cancels siblings that have not
  started when the Human node pauses), the process-group test skips with a reason when the host's process limit
  prevents the fork, the credentials e2e waits for the list before deleting, the Code time-limit bound allows a slow
  CI runner, and the compose smoke waits for `run_summary` before reading run history.
- `factory validate` is clean again: the factory verification workflow is the generated one (it no longer runs on
  pushes to `main`; release PRs still run it) and merged tasks are filed as done.

### Removed from known limits

- Demo visitors no longer see each other's run history and chats, and mock replies are no longer always Vietnamese.

## 0.5.0 (2026-10-24)

### Added

- **Web chat** (REQ-0048 phase 1). Backend: chat sessions and messages, a web chat trigger with Chat settings (input,
  reply and history fields, steps shown to visitors, turns and retention), Human nodes answered by the person chatting
  or by a reviewer (#116, migration `0035_chat_sessions`). Studio: a Chat side panel beside the canvas (Chat button or
  Shift+C, 340–760 px, fullscreen with the list of chats), a session picker and New chat, **View as** Workflow builder /
  Chat visitor with a preview banner, tool steps and confirmations in the thread (#117).
- **Editor layout**: the bottom panel is Run · Test · Code; Run shows the input and the logs side by side with a run
  picker and **View all**; Config folds away on narrow screens (#117).
- **Alignment guardrails** (TASK-0086, DEC-0055): rule 11 in `docs/ui-conventions.md`, `npm run lint:ui` on CI,
  `e2e/alignment.spec.ts`; Badge and TabsList `size="sm"`; ScrollArea content no longer overflows its panel (#118).
- **PaaS deploys**: an all-in-one image (UI, API and WebSocket on one port) with Render and Heroku buttons, Railway,
  Coolify and Dokploy configs (#119); Fly.io, DigitalOcean, Koyeb, Zeabur, Northflank and a self-hosted guide, image CI
  (#120); a remote sandbox service so Code nodes can run isolated where the platform has no Docker (#121).
  Guides in `docs/deploy/`.
- **Public demo mode** (`STUDIO_DEMO_MODE`): a shared read-only visitor with "Try the demo", seeded samples (the
  Chatbot with web chat on), Code, HTTP and Send email nodes off, mock models, a per-IP run limit (unit-tested) and a demo banner; visitors can chat with the Chatbot;
  the live demo runs on Render (#122).

### Changed

- README restyled: centred header, overview screenshot, feature table; handbook screenshots and text refreshed for the
  new layout and the chat panel (#117).

### Fixed

- The editor top bar no longer overlaps or half-clips its info badges at 1440 px (the demo viewer in Vietnamese was the
  tightest case): the LLM mode and id badges hide whole when they do not fit; `e2e/alignment.spec.ts` checks the bar for
  an admin and a viewer in en and vi.
- Demo-mode node errors ("… nodes are turned off in the public demo") no longer carry a stray `AppError: ` prefix.
- README feature-row captions are no longer clipped.

### Known limits

- In the public demo every visitor shares one account, so the run history and chats are shared until the next reset
  (`docs/deploy/demo.md`).

### Earlier (0.4.0)

- TypeScript in Code mode on Deno and the LangGraph.js export shipped in 0.4.0 (#109–#112).
