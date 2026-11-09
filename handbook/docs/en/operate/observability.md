# Observability

## Traces

OpenTelemetry emits one trace per run and one span per node, with
`gen_ai.usage.*` attributes and the cost. With no exporter configured,
tracing is a no-op. Spans go out as each node finishes; a waiting
human-in-the-loop run is traced when it ends.

| Destination | Variables |
| --- | --- |
| OTLP (Jaeger, Tempo, a collector) | `OTEL_EXPORTER_OTLP_ENDPOINT` and the standard `OTEL_*` variables (`OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`) |
| LangSmith | `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true`, plus optional `LANGSMITH_PROJECT` and `LANGSMITH_ENDPOINT` |
| **Open trace** link in the UI | `STUDIO_TRACE_URL`, for example `http://localhost:16686/trace/{trace_id}` |

When runs are traced to LangSmith and `STUDIO_TRACE_URL` is not set, **Open
trace** opens the run in LangSmith. Test results can go to LangSmith too: see
[Workflow tests](../run/tests.md#send-results-to-langsmith).

When Studio's LangSmith exporter is on, LangChain's own LangSmith tracer is
turned off, so each LLM call is exported once.

## Jaeger with Compose

```bash
# in .env
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
STUDIO_TRACE_URL=http://localhost:16686/trace/{trace_id}
```

```bash
docker compose --profile tracing up --build   # Jaeger UI: http://localhost:16686
```

Without Compose:

```bash
docker run -p 16686:16686 -p 4318:4318 jaegertracing/all-in-one
```

and point the backend at `http://localhost:4318`.

## Metrics

`STUDIO_OTEL_METRICS=1` with an OTLP endpoint also exports:

| Metric | Kind | Meaning |
| --- | --- | --- |
| `studio.runs` | counter | Finished runs |
| `studio.run.duration` | histogram, ms | Active run time |
| `studio.tokens` | counter | LLM tokens |
| `studio.cost` | counter, USD | Estimated LLM cost |
| `studio.errors` | counter | Error events |

## Health and readiness

`GET /api/health` is **liveness**: it answers 200 while the process serves
HTTP. It does not query the database. It reports `llm_mode`, `database` (the
dialect name), `run_bus` and whether the bus answers (`run_bus_ok`),
`tracing` and `import_enabled`. The `web` container answers `/healthz`.

`GET /api/ready` is **readiness**. It needs no sign-in and:

- runs `SELECT 1` on the database and pings Redis when `REDIS_URL` is set,
  each with a 2 second timeout, and reports the latency;
- reports the queue (`ready`, `delayed` and `processing` jobs, and the age
  of the oldest queued run), the live workers (busy slots, capacity and the
  age of the newest heartbeat), the run bus kind, and
  `in_memory_in_production` when production runs without Redis.

It answers 503 `SERVICE_NOT_READY` when the database fails, or when Redis is
configured and fails, with the same report in `error.details`. A queue
backlog or a missing worker never fails readiness; alert on them instead.
Neither endpoint returns a URL, host name or secret.

The Docker `HEALTHCHECK` and the Render and DigitalOcean templates keep
`/api/health`: restarting a container does not fix a dead database. Point a
load balancer or a rolling deploy at `/api/ready` when you want traffic held
back from an instance that cannot reach its database.

## Logs

The API logs to stdout. Errors in events are one line, with `sk-…`,
`Bearer …` and `api_key=…` redacted, and `?token=` shows as `token=***` in
uvicorn's access log.
