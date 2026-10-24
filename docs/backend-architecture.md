# Backend architecture (TASK-0017, DEC-0009)

```
            HTTP / WebSocket
                  │
   api/routes/*  (controllers: parse request, call service, shape response)
   api/deps.py   (DI: Database singleton, services, current_user, body limit)
   api/error_handlers.py (DomainError → HTTP status, readable 422)
                  │
   services/*    (business rules: ownership, naming, auth, run lifecycle, import)
        │                         │
   repositories/*            engine/*  (LangGraph: validator, compiler, nodes, llm, tools,
   (SQLAlchemy queries)                 runtime, limits, repo_import + sandbox runner)
        │
   models/*  (SQLAlchemy 2.0 typed Mapped models, Database: engine/session/migrate)
   migrations/ (Alembic; 0001_initial = MVP schema)
                  │
   core/*  (config/env vars, security: hashing + JWT, DomainError types, logging) — used by all
   schemas/* (Pydantic DTOs) — used by api
```

## Import rules (enforced by `tests/test_layers.py`)

| Layer | May import | Must not import |
|---|---|---|
| `core` | stdlib, jwt | anything else in `app`, FastAPI |
| `engine` | `core` | models, repositories, services, api, FastAPI |
| `models` | `core` | repositories, services, api, engine |
| `schemas` | pydantic | models, repositories, services, api |
| `repositories` | `models`, `core` | services, api, FastAPI |
| `services` | repositories, engine, models, core | api, FastAPI |
| `api` | everything | — |

- Services raise `core.errors` (`BadRequest`, `NotFound`, `Forbidden`, `Conflict`, `Unauthorized`, `TooLarge`); only `api/error_handlers.py` maps them to HTTP.
- Repositories hold no rules; each method opens its own short session (safe from the run worker thread).
- Service unit tests use in-memory fake repositories (`tests/test_services.py`).

## Responses and errors (DEC-0010)

- Every REST response is the envelope `{success, data, error}`. Routes return plain data; `EnvelopeResponse` (the FastAPI default response class) wraps it.
  One exception: the LangGraph Agent Server API subset under `/api/lg` (`api/routes/agent_server.py`, see `docs/agent-server-api.md`) returns the Agent Server bodies, so the official LangGraph clients work; its errors still use the error envelope.
- Services raise `AppError("CODE", details=…, **params)`; codes and messages live only in `core/errors.py` `CATALOG`. `api/error_handlers.py` is the only place that builds error responses. Format and code catalog: `docs/api-errors.md`.
- Engine messages (validator, node errors) are English free text carried in `details` / `errors`.

## Database

- `DATABASE_URL` (SQLAlchemy URL) overrides `STUDIO_DB`; default `sqlite:///<STUDIO_DB or backend/studio.db>`. SQLite keeps WAL + 15 s busy timeout.
- Postgres: `DATABASE_URL=postgresql://…` (normalised to `postgresql+psycopg://`; `psycopg[binary]` is a dependency). Models use portable types (Text, Float). CI runs the whole suite on Postgres 17 + Redis 7, and `tests/test_db_postgres.py` migrates a throwaway database (TASK-0009, DEC-0011).
- Startup runs `alembic upgrade head` programmatically (`services/seed.bootstrap`), then seeds the demo user and example workflow.
- Revision `0001_initial` is idempotent: on a pre-Alembic SQLite file it creates only missing tables and adds `workflows.owner` if absent, then stamps the version. Existing data is untouched.
- CLI: `cd backend && .venv/bin/alembic upgrade head`; new migration: `.venv/bin/alembic revision -m "…"` (add `--autogenerate` after editing models).

## Where things live (old → new)

| Old | New |
|---|---|
| `main.py` (everything) | `main.py` (app factory) + `api/routes/{auth,meta,workflows,imports,runs_ws}.py`, `services/*`, `repositories/*`, `models/*` |
| `auth.py` | `core/security.py` (+ `api/deps.current_user`) |
| `compiler.py` | `engine/{errors,templating,tools,llm,validator,nodes,compiler,runtime}.py` |
| `limits.py` | `engine/limits.py` (values in `core/config.py`) |
| `importer.py`, `sandbox/runner.py` | `engine/repo_import.py`, `engine/sandbox/runner.py`, `engine/sandbox/container.py` |
| `example.py` | `engine/examples.py` |

## Import sandbox (TASK-0015)

`STUDIO_ENABLE_IMPORT` defaults off. `ImportService` then raises `IMPORT_DISABLED` (404) from `start`, `status` and `finalize`; `start_job` itself stays callable so tests can drive the engine directly. When the flag is `1`, `engine/sandbox/container.py` builds `docker run` for install, inspect and run (read-only root, the job directory only, a fresh env, memory/cpu/pid limits). `STUDIO_IMPORT_RUNTIME=subprocess` keeps the host subprocess. Git clone and zip extract stay on the host. Each job writes `job.json`; `finalize` calls `mark_kept` so cleanup does not delete a workspace a workflow still points at. The engine does not query the database.

## Credentials (TASK-0005, ported from PR #2: done)

| PR #2 piece | Goes to |
|---|---|
| `credentials` table (raw `CREATE TABLE`) | `models/credential.py` + Alembic revision `0002_credentials` |
| `credentials.py` encryption (Fernet) | `core/crypto.py` |
| provider registry `PROVIDERS`, provider HTTP calls in `compiler.py` | `engine/llm.py` (`call_llm`) |
| CRUD + resolver | `repositories/credentials.py`, `services/credential_service.py` (`resolver(uid)`) |
| `/api/providers`, `/api/credentials*` | `api/routes/credentials.py` |
| resolver passed to `run_stream` | `RunService.plan` binds `CredentialService.resolver(uid)` into `RunPlan`; `RunPlan.events()` → `run_stream(wf, inp, resolve)` → `node_fn` |

Secrets are encrypted in the service before they reach the repository; only `resolve()` decrypts, at run time.

## Run bus (TASK-0009, DEC-0011)

`services/run_bus.py` defines `RunBus` (start / finish / owner / request_cancel / is_cancelled / publish / ping):

- `InMemoryRunBus` when `REDIS_URL` is unset (one process).
- `RedisRunBus` when `REDIS_URL` is set: keys `run:{id}:owner` and `run:{id}:cancel` (24 h TTL), events published on `run:{id}:events`.

`RunService.execute` registers each run, publishes every event (best effort) and checks the cancel flag between steps. `POST /api/runs/{id}/cancel` → `RunService.cancel` (owner only, else `RUN_NOT_FOUND`). The bus is built once in `api/deps.get_run_bus`.

## Telemetry (TASK-0010, DEC-0012)

- `engine/usage.py`: price table and the usage record `{provider, model, tokens_in, tokens_out, tokens, cost_usd, estimated}`. `call_llm(..., on_usage)` reports it; `runtime.run_stream` attaches it to `node_finished.usage`. Mock runs are estimated and cost 0.
- `services/telemetry.py`:
  - `summarize(events)` gives the persisted run metrics;
  - `Telemetry.record_run(...)` builds the run's trace from event timestamps after the run;
  - `exporter_configs()` reads `OTEL_*` / `LANGSMITH_*`;
  - `trace_url()` fills `STUDIO_TRACE_URL`.
- `RunService.record` computes the metrics, records the trace (errors swallowed), stores both, and the socket gets a final `run_summary` event (not stored in `events`). History items carry `metrics`, `trace_id` and `trace_url`.
- Built once in `api/deps.get_telemetry`; tests inject `InMemorySpanExporter`.

## Human-in-the-loop (TASK-0006, DEC-0013)

- Engine:
  - `engine/nodes.py` `human` node raises `engine.errors.Interrupt` when it has no response.
  - `runtime.run_stream` turns that into `run_waiting` with a checkpoint {node, state}.
  - `run_stream(..., resume={node, value, state})` compiles with `entry=node` and feeds `value` to that node once (a loop back to it pauses again).
- Service:
  - `RunService.plan` sees `resume_run_id`, then `plan_resume` checks owner and `waiting` status and builds a plan with the same run id and the earlier events.
  - `record()` stores the checkpoint while waiting and clears it when the run ends; the trace is emitted only at the end.
- `runs.owner` (backfilled from workflows) and `runs.checkpoint` come from migration `0004_hitl`.

## API triggers and the job queue (TASK-0007, DEC-0014)

- `services/job_queue.py`: `JobQueue` with `enqueue` / `dequeue`. `InMemoryJobQueue` is the default; `RedisJobQueue` is a Redis list `studio:run-jobs` when `REDIS_URL` is set.
- `services/trigger_service.py`:
  - token create, list and revoke (only the SHA-256 is stored);
  - `authenticate`, which binds a token to its workflow and owner;
  - `start`, which pre-creates the run as `queued` (source `api`) and enqueues the job;
  - `wait`, the sync mode, which polls the runs table;
  - `run_result`, the public result shape shared by the REST response and the webhook;
  - `check_callback_url`, the SSRF guard.
- `services/run_worker.py`: `RunWorker` dequeues a job, skips it if it is no longer `queued`, sets it to `running`, then calls `RunService.plan` and `execute` (no socket: `send` is a no-op and cancel comes via the RunBus), then delivers the webhook.
  - Started by the app lifespan when `STUDIO_WORKER` is not `0`; `app/worker.py` runs it standalone.
- Routes: `api/routes/triggers.py` (owner, JWT) and `api/routes/hooks.py` (public, workflow token; tag `public`). `api/openapi_public.py` builds the public-only spec from `hooks.py` (`/openapi.public.json`, `/docs/public`, `docs/api/openapi.public.json`).

## Workflow versions (TASK-0008, DEC-0015)

- `models/workflow_version.py` + `repositories/workflow_versions.py`: one immutable row per version, unique `(workflow_id, version)`. Migration `0006_workflow_versions` backfills v1 for existing workflows and adds `runs.workflow_version`.
- `WorkflowService._write` is the single write path (save, rename, duplicate, import, seed, restore). It writes the workflow and then a new version only when the stored JSON changed.
- `services/workflow_diff.py` holds the pure functions:
  - `diff_workflows(a, b)` matches nodes and edges by id and state fields by name, and reports added, removed and changed (with before/after), plus `moved` for position-only changes;
  - `same_content` ignores the name and positions.
- `RunService.plan` tags a run with the latest version when the workflow it runs has the same content as that version, otherwise `NULL` (unsaved edits). A resume or cancel keeps the original tag.
- Routes live in `api/routes/workflows.py`: `/versions`, `/versions/diff`, `/versions/{n}`, `/versions/{n}/restore`.

## Phase-2 hardening (TASK-0019, DEC-0016)

- `services/webhooks.py` handles result webhooks:
  - `resolve` (SSRF check + single DNS resolution), `pinned_request` (connect to the IP, keep Host/SNI);
  - `sign` / `verify_signature` (HMAC-SHA256 over `"<ts>.<body>"`) and `deliver`.
- `services/rate_limit.py`: fixed-window `RateLimiter`. It uses Redis (async client) when `REDIS_URL` is set and memory otherwise. Called by `TriggerService.check_rate`.
- `services/redis_async.py`: one `redis.asyncio` client per event loop. Used by `RedisRunBus.astart/apublish` and the Redis rate limiter. `finish` runs on a worker thread (TASK-0060).
- `services/job_queue.py`, `RedisJobQueue`:
  - `dequeue` = BLMOVE into `studio:run-jobs:processing:<worker>`; `ack` = LREM;
  - `heartbeat` = `studio:worker:<id>` with a TTL; `recover_stale` requeues dead workers' jobs as `recovered`. *(Replaced by leases + reaper in TASK-0020.)*
  - `RunWorker` acks after `run_job` and re-executes `running` jobs only when they are `recovered`.
- `RunService`:
  - `expire_waiting` (sweep in the app lifespan every 60 s, plus lazy checks in `waiting_run` and `pending`), status `expired`;
  - `telemetry.waited_s` removes human waits from `duration_ms`.
- `WorkflowService._write` retries version-number conflicts and prunes by `STUDIO_VERSION_KEEP`. `WorkflowVersionRepository.prune` never deletes versions referenced by `runs.workflow_version`.
- `Database.migrate` holds `pg_advisory_xact_lock` (Postgres) or an `fcntl` lock on `<db>.migrate.lock` (SQLite).
- `engine/usage.prices()` gives built-ins, overridden by `STUDIO_PRICES_FILE` and then by `STUDIO_PRICES`.
- `telemetry.disable_langchain_tracer()` is called when our LangSmith exporter is configured.
- Migration `0007_hardening`: `workflow_tokens.signing_secret` (Fernet-encrypted).

## Deferred hardening (TASK-0020, DEC-0017)

- `NotificationService` (+ `NotificationRepository`, route `api/routes/notifications.py`): `run_event` stores a row, then sends SMTP e-mail and the notify webhook in a background thread. Called from `RunService.record` on waiting/expired.
- `DeliveryService` (+ `WebhookDeliveryRepository`): `create` stores and enqueues a `delivery` job; `attempt` uses `webhooks.post` -> `Attempt(ok, code, latency_ms, error, retryable)` and re-enqueues with `backoff(n)` via `JobQueue.enqueue_at`; `redeliver` resets attempts.
- `TriggerService.signing_secrets` returns the current secret plus the previous one inside `STUDIO_SECRET_GRACE`; `webhooks.sign` emits one `v1` per secret; `rotate_secret`.
- `RedisJobQueue`: leases `studio:job-lease:<sha1>` (TTL = visibility), `touch`, `ack`, `reap` (two-strike), delayed zset `studio:run-jobs:delayed` + `promote_due`. `RunWorker` dispatches by `kind`, renews leases while running, and runs a `maintain` loop (promote + reap).
- `RunService`: `plan_recover` resumes `recovered` jobs from the last progress checkpoint (`runs.save_progress`, engine `_checkpoint` events); `_close_waiting` shared by cancel and expire.
- `Telemetry`: `start_run` / `node` / `end_run` export spans live (`RunSpan`); segments parented through the checkpoint's `trace`; optional `MeterProvider` metrics.
- Migration `0008_notifications_deliveries`: `notifications`, `webhook_deliveries`, `workflow_tokens.signing_secret_prev` / `secret_rotated`.

## Effectively-once execution (TASK-0021, DEC-0018)

- `engine/effects.py`: `Effects(run_id, attempt, ledger, guard)` wraps LLM/Tool nodes: ledger hit -> reuse; else guard (fencing) -> run -> record. `idempotency_key(run, node, iteration)`; HTTP Tool nodes send `Idempotency-Key`, `X-Studio-Run-Id`, `X-Studio-Attempt`; `call_tool` passes `idempotency_key` to tools that declare it.
- `engine/runtime.run_stream`: compiled with an in-memory LangGraph saver; `stream_mode=["updates", "checkpoints"]` gives superstep boundaries -> `node_started` events and `_checkpoint {node, nodes, state, counts}`. `compile_workflow(entry=[...])` resumes at several nodes.
- `engine/sandbox/runner.py`: `attach_saver` / `dump_checkpoint` / `load_checkpoint` (LangGraph serde, base64) for imported graphs; `repo_import.run_imported(checkpointing=, resume={"blob"})`.
- `NodeResultRepository` (`node_results`), `RunRepository.claim` (CAS + `lease_gen`), fenced `add` / `save_progress` raising `StaleLease`.
- `RunService`: `plan.fence/attempt/effects`; `_guard`, `_fenced` (stop without writing); `plan_recover` exports the lost root (`Telemetry.close_lost`) and resumes or restarts; a progress save at the start of every queue segment stores `span.ref`.
- `Telemetry`: `_IdGenerator` (forced ids for `close_lost`), `RunSpan.ref`, `start_run(links=)`.
- `NotificationHub` (`services/notification_hub.py`) + WebSocket `/ws/notifications`; `NotificationService.preferences/set_preferences`, `email_text/email_html`.
- Migration `0009_effectively_once`: `node_results`, `runs.lease_gen`, `users.notify_in_app/notify_email`.

## LLM providers (TASK-0030, DEC-0032)

`engine/providers.py` is the provider registry (one strategy class per provider: defaults, model listing, LangChain chat model). `engine/llm.py` dispatches LLM nodes to it; `services/credential_service.py` uses it for validation, model lists and connection tests. Engine failures are `ProviderError(code)` and become `AppError` in the service.

Live LLM text: nodes write deltas with LangGraph's `get_stream_writer()` (`custom` stream mode). `engine/runtime.py` yields them as `node_token` events, and `services/run_service.py` sends them to the socket and the run bus but does not store them. Embeddings for knowledge bases go through `Provider.embed()`. The knowledge service keeps one vector dimension per knowledge base (`dims`).
