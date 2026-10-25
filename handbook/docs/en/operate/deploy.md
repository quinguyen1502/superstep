# Deploy with Compose

## Services

| Service | Image | Role |
| --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg17` | Workflows, runs, checkpoints, versions, vectors |
| `redis` | `redis:7-alpine` | Run bus, job queue, rate-limit counters, live notifications |
| `api` | `./backend` | FastAPI. Applies Alembic migrations and seeds on start-up |
| `worker` | `./backend`, `python -m app.worker` | Runs queued jobs: API runs, schedules, recovered runs, webhook deliveries |
| `web` | `./frontend` | nginx serving the Vite build and proxying `/api` and `/ws` |
| `jaeger` | `jaegertracing/all-in-one` | Optional, with `--profile tracing` |

```bash
cp .env.example .env   # set JWT_SECRET and POSTGRES_PASSWORD; never commit .env
docker compose up --build
python scripts/compose_smoke.py http://localhost:8080
```

The UI is at `http://localhost:8080` (`WEB_PORT`). `.env.example` lists every
variable; the most used ones are in [Configuration](../reference/configuration.md).

## Production checklist

| Setting | Why |
| --- | --- |
| `STUDIO_ENV=production` | Refuses the placeholder `JWT_SECRET`, does not create the demo account, and deactivates it if it still has the demo password. |
| `JWT_SECRET` | Signs sessions. Long and random. |
| `STUDIO_SECRET_KEY` | Fernet key for stored credentials. Set it explicitly; losing it makes old credentials unreadable. |
| `STUDIO_ADMIN_EMAILS` | Bootstraps the first admin (the demo admin does not exist in production). |
| `STUDIO_PUBLIC_URL` | Public base URL for links in e-mails, approvals and webhooks. |
| `STUDIO_CORS_ORIGINS` | Only if a browser on another origin calls the API. Production allows none by default. |
| `STUDIO_TRUSTED_PROXIES` | CIDRs of the proxies in front, so client IPs for rate limits are read correctly. |
| TLS | Terminate HTTPS in front of `web`. The session cookie is `Secure` in production. |

An empty `STUDIO_SECRET_KEY` is generated once into the `apidata` volume
(`/data/secret.key`). That works, but back the volume up with the database.

## Upgrade from v0.1.0

v0.1.0 was called LangGraph Studio, and its Compose project was
`langgraph-studio`. The project is now `superstep`, but the volumes keep their
v0.1.0 names (`langgraph-studio_pgdata`, `_redisdata`, `_apidata`), so the
database, queue and generated secret key carry over. Stop the old stack before
starting the new one. Otherwise Compose starts a second set of containers on
the same ports and volumes:

```bash
docker compose -p langgraph-studio down   # keeps the volumes; never add -v
git pull && docker compose up -d --build
```

Also check what still uses the old name:

- **Telemetry:** the default `OTEL_SERVICE_NAME` is now `superstep`. Set it
  to `langgraph-studio` to keep existing dashboards.
- **E-mail:** subjects start with `[Superstep]`. Update mail filters.
- **Local runs (no Docker):** the key and imports move to `~/.superstep/`.
  `~/.langgraph-studio/` is still used while the new folder does not exist.
- **Files:** templates exported and nodes copied from v0.1.0 still import and
  paste.

## Database

`GET /api/health` reports `database` (`postgresql` or `sqlite`) and `run_bus`
(`redis` or `memory`). Leave `DATABASE_URL` empty in local development to use
SQLite `backend/studio.db`, and leave `REDIS_URL` empty to keep the run bus in
memory.

Start-up migrations take a lock so several processes do not migrate at once
(a Postgres advisory lock, or `<db>.migrate.lock` for SQLite). Schema changes
go through Alembic:

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "describe"
.venv/bin/alembic upgrade head
```

## Workers and the queue

`STUDIO_WORKER=1` (the default outside Compose) runs the worker inside the API
process. With `REDIS_URL` set, a separate process is `python -m app.worker`;
Compose sets the API to `STUDIO_WORKER=0` and runs a `worker` service.

```bash
docker compose up --scale worker=3
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_WORKER_CONCURRENCY` | 2 | Jobs one worker runs at once |
| `STUDIO_JOB_VISIBILITY_TIMEOUT` | 30 s | Lease on a job; the worker renews it while running |
| `STUDIO_JOB_REAP_EVERY` | 15 s | How often expired leases are requeued |
| `STUDIO_RECOVER_ON_START` | 1 | In-memory queue: requeue unfinished runs when the server starts |
| `STUDIO_RECOVER_MAX_ATTEMPTS` | 3 | Times one run is taken before recovery gives up with `RUN_INTERRUPTED` |

On Redis, a job whose worker died is requeued when its lease expires, and
continues from the last checkpoint (`run_recovered` in the trace). Each time a
worker takes a run, `runs.lease_gen` increases; writes must carry that fencing
token, so a worker that lost the lease cannot commit and stops.

## Runs across restarts

Superstep keeps its run checkpoints in its own database (SQLite by default,
Postgres with `DATABASE_URL`), not in LangGraph's in-memory saver, so a restart
or a crash loses no paused run:

| Run | After a restart |
| --- | --- |
| Paused at a Human node | Still waiting. Answer it in the studio, a chat channel or the API as before; it continues from its checkpoint. |
| Queued or running API, schedule, chat or test run | Continues from its last finished node. Queue jobs save a progress checkpoint after every node; the node that was in flight runs again, finished calls are not repeated ([effectively-once side effects](../reference/architecture.md#effectively-once-side-effects)). |
| Running in the editor | Ends with the browser connection; it is not stored until it finishes. Run it again. |

How unfinished queue runs come back depends on the queue:

- **Redis** (`REDIS_URL`): the job stays in Redis; once its lease expires any
  worker takes it again.
- **In-memory queue** (no `REDIS_URL`, a single process): jobs held in memory
  are gone, so at start-up the server queues every `queued` or `running` run
  again as a recovered job. Set `STUDIO_RECOVER_ON_START=0` only if several API
  processes share one database without Redis, since one of them would take
  over the runs of another.

A run that has already been taken `STUDIO_RECOVER_MAX_ATTEMPTS` times (for
example a node that keeps crashing the server) is not continued again: it ends
as `error` with code `RUN_INTERRUPTED`, keeping its events so far.

## Local models from Compose

Inside Compose, `localhost` is the container. `api` and `worker` set
`extra_hosts: host.docker.internal:host-gateway`, so point Ollama at
`http://host.docker.internal:11434` and LM Studio at
`http://host.docker.internal:1234/v1`. On Linux run
`OLLAMA_HOST=0.0.0.0 ollama serve` and enable LM Studio's *Serve on Local
Network*; the firewall may need to accept the Docker bridge.

## The Docker socket

Compose mounts `/var/run/docker.sock` into `api` and `worker`, for
[Code mode](code-runtime.md) and [repo import](import.md). That socket is
root-equivalent on the Docker host. Keep both features off on a host you do
not trust. On Linux, if the container user (uid 10001) cannot open the socket,
set `STUDIO_DOCKER_GID="$(stat -c %g /var/run/docker.sock)"`.
