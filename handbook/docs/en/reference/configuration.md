# Configuration

The backend reads environment variables. `.env.example` at the repository
root lists every variable Compose passes; this page groups them.

## Core

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_ENV` | `dev` | `production` refuses the placeholder `JWT_SECRET` and skips the demo account |
| `JWT_SECRET` | placeholder | Signs session tokens |
| `JWT_TTL_SECONDS` | `86400` | Session lifetime |
| `STUDIO_SECRET_KEY` | generated | Fernet key for stored secrets |
| `STUDIO_SECRET_KEY_FILE` | `~/.superstep/secret.key` | Where a generated key is kept |
| `DATABASE_URL` | SQLite `backend/studio.db` | SQLAlchemy URL, e.g. `postgresql://…` |
| `STUDIO_DB` | `backend/studio.db` | SQLite path when `DATABASE_URL` is empty |
| `REDIS_URL` | empty | Run bus, queue and counters; empty keeps them in memory |
| `STUDIO_PUBLIC_URL` | empty | Public base URL for links in e-mails, approvals and webhooks |
| `STUDIO_CORS_ORIGINS` | `*` in dev, none in production | Allowed browser origins |
| `STUDIO_COOKIE_SECURE` | `1` in production | `Secure` flag on the session cookie |
| `WEB_PORT` | `8080` | Compose: port of the `web` service |

## Accounts

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_ADMIN_EMAILS` | empty | Bootstrap admins |
| `STUDIO_DEFAULT_ROLE` | `editor` | Role of new accounts (`editor` or `viewer`) |
| `STUDIO_LOGIN_MAX_FAILURES` | `5` | Failed sign-ins before a lockout |
| `STUDIO_LOGIN_WINDOW` | `900` | Window they are counted in (s) |
| `STUDIO_LOGIN_LOCK` | `900` | Lock duration (s) |
| `STUDIO_PASSWORD_RESET_TTL` | `3600` | Lifetime of a reset link (s) |

## Models

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Fallback for LLM nodes and embeddings with no credential |
| `OPENAI_BASE_URL` | empty | Base URL for that fallback |
| `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL` | empty | Fallback for Decision nodes |
| `STUDIO_PRICES` | empty | JSON price overrides, USD per 1M tokens `{"prefix": [in, out]}` |
| `STUDIO_PRICES_FILE` | empty | The same, from a file |

## Runs and limits

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_RECURSION_LIMIT` | `25` | Steps per run |
| `STUDIO_RUN_TIMEOUT` | `120` | Run duration (s); import runs default to 300 |
| `STUDIO_EVENT_MAX_BYTES` | `262144` | One event |
| `STUDIO_RUN_MAX_BYTES` | `2097152` | Stored events per run |
| `STUDIO_INPUT_MAX_BYTES` | `262144` | Run input |
| `STUDIO_WORKFLOW_MAX_BYTES` | `1048576` | Workflow JSON |
| `STUDIO_WAIT_TTL` | `604800` | A waiting run expires after this (s); `0` never |
| `STUDIO_VERSION_KEEP` | `0` | Versions kept per workflow; `0` keeps all |
| `STUDIO_TEST_CASES_MAX` | `50` | [Test cases](../run/tests.md) per workflow |
| `STUDIO_TEST_PARALLEL` | `4` | Test cases of one run of the tests that run at a time |
| `STUDIO_ENABLE_DEMO_TOOLS` | `0` | Registers `sleep_demo` for cancel and timeout tests |

## Workers and the queue

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_WORKER` | `1` | Run the worker inside the API process |
| `STUDIO_WORKER_CONCURRENCY` | `2` | Jobs per worker |
| `STUDIO_JOB_VISIBILITY_TIMEOUT` | `30` | Job lease (s) |
| `STUDIO_JOB_REAP_EVERY` | `15` | Requeue expired leases every (s) |
| `STUDIO_RECOVER_ON_START` | `1` | In-memory queue: requeue unfinished runs at start-up ([runs across restarts](../operate/deploy.md#runs-across-restarts)) |
| `STUDIO_RECOVER_MAX_ATTEMPTS` | `3` | Restarts that may cut one run off before it ends as `RUN_INTERRUPTED` |

## API triggers and webhooks

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_TRIGGER_RATE_LIMIT` | `60` | Runs per token per window; `0` off |
| `STUDIO_TRIGGER_RATE_WINDOW` | `60` | The window (s) |
| `STUDIO_CHAT_TRIGGER_RATE_LIMIT` | `60` | Chat triggers: runs per sender and trigger per window; `0` off |
| `STUDIO_SYNC_WAIT_MAX` | `30` | Longest `sync` wait (s) |
| `STUDIO_ALLOW_PRIVATE_CALLBACKS` | `0` | Allow callbacks to private addresses |
| `STUDIO_WEBHOOK_MAX_ATTEMPTS` | `5` | Delivery attempts |
| `STUDIO_WEBHOOK_BACKOFF_BASE` | `2` | Backoff base (s) |
| `STUDIO_WEBHOOK_BACKOFF_MAX` | `300` | Backoff cap (s) |
| `STUDIO_SECRET_GRACE` | `86400` | Old signing secret stays valid after rotation (s) |

## Tools, e-mail and MCP

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_HTTP_TOOL_ALLOW_PRIVATE` | `0` | HTTP Tool nodes may call private addresses |
| `STUDIO_HTTP_TOOL_TIMEOUT` | `30` | HTTP Tool request timeout (s) |
| `STUDIO_SMTP_ALLOW_PRIVATE` | `0` | Send email nodes may use private SMTP hosts |
| `STUDIO_EMAIL_NODE_HOURLY_LIMIT` | `100` | Recipients per workflow owner per hour |
| `STUDIO_MCP_STDIO` | `0` | Allow stdio MCP servers (admins only) |
| `STUDIO_MCP_ALLOW_PRIVATE` | `0` | Allow HTTP MCP servers on private addresses |
| `STUDIO_MCP_TIMEOUT` | `30` | MCP call timeout (s) |

## Code mode

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_ENABLE_CODE_NODES` | `0` | Turn Code mode on |
| `STUDIO_CODE_RUNTIME` | `docker` | `docker`, or `subprocess` (runs on host: no Docker limiting its access) |
| `STUDIO_CODE_IMAGE` | `studio-code:1` | Sandbox image |
| `STUDIO_CODE_PACKAGES` | the image's | Packages shown in the editor |
| `STUDIO_CODE_MEMORY` | `256m` | Memory per call |
| `STUDIO_CODE_CPUS` | `0.5` | CPU per call |
| `STUDIO_CODE_PIDS` | `64` | Processes per call |
| `STUDIO_CODE_MAX_SECONDS` | `30` | Cap on a call's time |
| `STUDIO_CODE_CONCURRENCY` | `4` | Containers at once per process |
| `STUDIO_CODE_TEST_PER_MINUTE` | `20` | Editor tests per user per minute |

## Repo import

| Variable | Default | Meaning |
| --- | --- | --- |
| `STUDIO_ENABLE_IMPORT` | `0` | Turn import on |
| `STUDIO_IMPORT_RUNTIME` | Docker | `subprocess` only for tests (runs on host: no Docker limiting its access) |
| `STUDIO_IMPORT_DIR` | `~/.superstep/imports` | Job directories |
| `STUDIO_IMPORT_HOST_DIR` | empty | Host path of that directory under Compose |
| `STUDIO_IMPORT_IMAGE` | `python:3.12-slim` | Sandbox image |
| `STUDIO_IMPORT_MEMORY` | `1g` | Memory |
| `STUDIO_IMPORT_CPUS` | `1` | CPU |
| `STUDIO_IMPORT_PIDS` | `256` | Processes |
| `STUDIO_IMPORT_NETWORK` | `bridge` | Network of a run (`bridge` or `none`) |
| `STUDIO_IMPORT_SECRETS` | empty | Extra env names passed into the sandbox |
| `STUDIO_INSPECT_TIMEOUT` | `120` | Inspect time (s) |
| `STUDIO_IMPORT_MAX_AGE_HOURS` | `72` | Cleanup age; `0` disables |
| `STUDIO_IMPORT_MAX_BYTES` | `209715200` | Largest source tree |
| `STUDIO_DOCKER_GID` | `10001` | Compose: group id of the Docker socket |

## Notifications and approvals

| Variable | Default | Meaning |
| --- | --- | --- |
| `SMTP_HOST` | empty | Studio e-mail (notifications, reset links, e-mail approvals); empty turns mail off |
| `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | `587`, empty, empty, `studio@localhost` | SMTP settings |
| `SMTP_STARTTLS`, `SMTP_SSL` | `1`, `0` | Transport security |
| `STUDIO_NOTIFY_WEBHOOK_URL`, `STUDIO_NOTIFY_WEBHOOK_SECRET` | empty | JSON webhook for waiting and expired runs |
| `STUDIO_APPROVAL_TTL` | `86400` | Lifetime of approval buttons and links (s) |
| `STUDIO_IDENTITY_CODE_TTL` | `600` | Verification code lifetime (s) |
| `STUDIO_IDENTITY_CODE_ATTEMPTS` | `5` | Tries per code |
| `STUDIO_IDENTITY_CODE_RESEND` | `30` | Resend wait (s) |
| `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET` | empty | **Add to Slack** |
| `WHATSAPP_API_URL` | Graph API | WhatsApp Cloud API base |
| `STUDIO_TRUSTED_PROXIES` | private ranges | Proxy CIDRs for `X-Forwarded-For` |
| `STUDIO_CALLBACK_RATE_LIMIT_IP` | `60` | Public callbacks per IP per window |
| `STUDIO_CALLBACK_RATE_LIMIT_CHANNEL` | `300` | Per connection per window |
| `STUDIO_CALLBACK_RATE_WINDOW` | `60` | The window (s) |

## Tracing

| Variable | Default | Meaning |
| --- | --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty | OTLP/HTTP endpoint; empty turns tracing off |
| `OTEL_EXPORTER_OTLP_HEADERS` | empty | OTLP headers |
| `OTEL_SERVICE_NAME` | `superstep` | Service name |
| `STUDIO_TRACE_URL` | empty | **Open trace** link template with `{trace_id}` |
| `STUDIO_OTEL_METRICS` | `0` | Also export metrics |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` | empty | Export to LangSmith |
| `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` | empty | LangSmith project and endpoint |
