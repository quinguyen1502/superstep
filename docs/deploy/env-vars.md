# Environment variables for PaaS deploys

[Tiếng Việt](env-vars.vi.md) · [Deploy guide](README.md)

The variables that matter for the all-in-one image. The full list, including channels, SMTP, MCP and tracing, is in
[`.env.example`](../../.env.example).

## Required

| Variable | Default in the image | Purpose |
|---|---|---|
| `JWT_SECRET` | none | Signs session tokens. Production refuses to start without it. |
| `STUDIO_SECRET_KEY` | none | Encrypts stored credentials. Production refuses to start without it, unless `/data/secret.key` exists from an earlier start. A Fernet key is used as is; any other value (for example a platform-generated secret) is turned into one with SHA-256. Never change it after the first start. |
| `STUDIO_ADMIN_EMAILS` | empty | Comma-separated admin emails. When no admin exists, the first one is created at start-up. |

## Recommended

| Variable | Default in the image | Purpose |
|---|---|---|
| `STUDIO_ADMIN_PASSWORD` | empty | Password for that first admin. Empty = generated and logged once. Must have 8+ characters, a letter and a digit. Only used when the account is created. |
| `STUDIO_DEMO_MODE` | empty | `true` runs the public demo ([demo.md](demo.md)): a read-only visitor account per sign-in, sample workflows seeded on every boot, Code/HTTP/Send email nodes off, models on the mock. Never for real work. |
| `STUDIO_DEMO_VISITOR_TTL` | `86400` | Demo mode only: seconds before a visitor account is removed with its runs and chats. |
| `STUDIO_DEMO_RUN_RATE_LIMIT` | `20` | Demo mode only: runs per client IP per minute (0 = off). |
| `STUDIO_PUBLIC_URL` | empty | The https address of the app (links in emails, Slack/Telegram callbacks). |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | empty | Default LLM provider. Empty = sample answers; users can also add credentials in Settings. |

## Database and queue

| Variable | Default in the image | Purpose |
|---|---|---|
| `DATABASE_URL` | empty = SQLite at `STUDIO_DB` | `postgres://`, `postgresql://` and `postgresql+psycopg://` URLs are accepted (the first two are rewritten to the psycopg driver). Vector search in knowledge bases uses pgvector when it is available. |
| `STUDIO_DB` | `/data/studio.db` | SQLite file. Put `/data` on a persistent volume. |
| `REDIS_URL` | empty | Optional. Empty = in-memory run bus and queue in the web process (one instance). Set it to run a separate worker (`python -m app.worker`) or more than one web instance. |
| `STUDIO_WORKER` | `1` | `0` = the web process does not take queued runs (leave them to the worker). |
| `STUDIO_AGENT_PARALLEL_TOOLS` | `4` | How many tool calls of one Agent round may run at once. Clamped to 1..8. An invalid value stays at 1. An Agent node can turn parallel calls off. |

## Code nodes

| Variable | Default in the image | Purpose |
|---|---|---|
| `STUDIO_ENABLE_CODE_NODES` | `1` | `0` turns Code mode off. |
| `STUDIO_CODE_RUNTIME` | `subprocess` | Runs on host: code runs directly on the server, without Docker limiting its access. Use only for trusted code. There is no Docker daemon in the image, so `docker` does not work here. `remote` sends Code calls to the [sandbox service](sandbox.md). |
| `STUDIO_SANDBOX_URL`, `STUDIO_SANDBOX_TOKEN` | empty | The sandbox service and its shared token (16+ characters), for `STUDIO_CODE_RUNTIME=remote`. |
| `STUDIO_CODE_NO_NETWORK` | empty (`1` in the sandbox image) | `1` = Python Code refuses sockets, new processes and ctypes (an audit hook inside the interpreter). |
| `STUDIO_CODE_LANGUAGES` | `python,typescript` | Languages offered. TypeScript runs on the bundled Deno. |
| `STUDIO_CODE_TS_DENO_DIR`, `STUDIO_CODE_TS_PACKAGES` | `/opt/deno-cache`, `npm:zod@3,npm:date-fns@4` | The TypeScript packages cached in the image. Keep them unchanged unless you build your own image. |
| `STUDIO_CODE_PACKAGES` | `pydantic,python-dateutil` | Python packages shown to users as importable. |
| `STUDIO_CODE_MAX_SECONDS` | `30` | Time limit per call. |

## Network and platform

| Variable | Default in the image | Purpose |
|---|---|---|
| `PORT` | `8000` | Port the server listens on. Render, Heroku and Railway set it. |
| `STUDIO_TRUSTED_PROXIES` | `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10` | Proxies whose `X-Forwarded-For` hops are skipped when finding the client IP (rate limits, audit log). The default covers the private and shared ranges PaaS routers connect from. Behind a CDN such as Cloudflare, add its ranges. |
| `STUDIO_ENV` | `production` | Production mode: no demo account, Secure session cookie, required secrets. |
| `STUDIO_COOKIE_SECURE` | `1` in production | Set `0` only if you serve the app over plain HTTP. |
| `STUDIO_STATIC_DIR` | `/app/static` | Built UI served by the API. Empty = API only. |
| `STUDIO_SECRET_KEY_FILE` | `/data/secret.key` | Key file used when `STUDIO_SECRET_KEY` is empty (existing installs only). |

Tracing (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `STUDIO_TRACE_URL`) and LangSmith
(`LANGSMITH_*`) work the same as in `docker-compose.yml`; point them at a hosted collector.
