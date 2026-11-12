# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0014
- Status: Accepted 2026-11-10 (Asia/Saigon) by the owner (pt280u, "go ahead with phase 2"); REQ-0095 accepted. Phase 2 (TASK-0294 to TASK-0305) merged through PRs #354 to #360. The owner approved starting Phase 3 (TASK-0306 to TASK-0308) on 2026-11-11.
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-10
- Related Requirements: REQ-0095 (continues REQ-0094)
- Related Design: DES-0006
- Related Architecture: DEC-0094, DEC-0095 (unchanged)
- Follows: PLAN-0013 (MVP, TASK-0284 to TASK-0293, merged to `develop` through PRs #349 to #353)

## Objective

Finish the observability work PLAN-0013 left for later: correlate logs, traces and metrics, add the missing depth (database, Redis, model latency, embeddings, integrations, rate limits), store per-call usage so the Usage page can break it down by model, user and team, then add budgets, SLOs and quality signals.

## Phase Mapping

PLAN-0013 "Later Phases" listed phase 2 (correlation, depth), phase 3 (usage data) and phase 4 (governance). This plan groups them as:

- Phase 2 here = PLAN-0013 phases 2 and 3 (TASK-0294 to TASK-0305).
- Phase 3 here = PLAN-0013 phase 4 (TASK-0306 to TASK-0308).

## Context Reviewed (develop 6047c732)

- `backend/app/services/telemetry.py`: bounded `LABELS`, counters `studio.runs`, `studio.tokens`, `studio.cost`, `studio.errors`, `studio.llm.{tokens,cost,unpriced,errors,fallbacks}`, `studio.http.server.{requests,duration}`, `studio.ws.connections`, `studio.jobs.{reaped,recovered}`; gauges `studio.ready.db[.latency]`, `studio.ready.redis[.latency]`, `studio.queue.*`, `studio.worker.*`, `studio.process.*`, `studio.run_bus.in_memory`, `studio.approvals.*`, `studio.webhooks.*`, `studio.schedules.*`. No per-call duration, no embedding, integration or rate-limit metric.
- `backend/app/core/logging.py`: plain logger helper and token redaction; no JSON format, no request id anywhere.
- No OpenTelemetry FastAPI, SQLAlchemy or Redis instrumentation in the backend.
- `deploy/observability/`: collector is `otel/opentelemetry-collector-contrib` (has `postgresql` and `redis` receivers), Prometheus, Grafana dashboards and provisioning.
- `backend/app/engine/llm.py`, `engine/providers.py`: usage reported per call; 429 is `PROVIDER_RATE_LIMITED` and counted in `studio.llm.errors`.
- `backend/app/engine/embeddings.py`: embeddings report no usage.
- `backend/app/services/rate_limit.py` and callers raising `RATE_LIMITED`; `services/email_quota.py` raising `EMAIL_RATE_LIMITED`.
- `backend/app/models/run.py`: no usage table; `ix_runs_started`, `ix_runs_status_started` from TASK-0288. `chat_message.py`: `status`, `code`, `created`, no index on `status` or `created`. `chat_session.py` `chat_ratings` (thumbs up or down). `workflow_test.py` suites with totals.
- `frontend/src/pages/settings/UsageSection.tsx`: totals, top workflows, unpriced share, product health, handbook and Grafana links.

## Decisions Made In This Plan

- **New REQ-0095** rather than amending REQ-0094: REQ-0094 lists this work as out of scope, and it is accepted and implemented.
- **Database and Redis server metrics through collector receivers** (recommended, TASK-0296), keeping DEC-0094's single Prometheus target for the app side; standalone exporters are the fallback. MVP probe gauges stay as they are.
- **Provider rate limits are already counted** (`studio.llm.errors{code="PROVIDER_RATE_LIMITED"}`); TASK-0300 adds only Superstep's own limits and a combined panel.
- **Usage table first, then UI**: per-model (TASK-0302) needs TASK-0301; per-user and per-team (TASK-0303) works from `runs.owner` and uses the table when present.
- **No deploy health-check switch task** (DEC-0095; the owner kept templates on `/api/health`) and **no handbook republish task** (happens with the next `main` release).
- **Budget warnings** at 80 and 100 percent were accepted in [DEC-0096](../decisions/DEC-0096-usage-budget-warnings.md). TASK-0307 proposes default SLO targets for owner review.

## Work Breakdown

| Order | Task | Phase | Purpose | Size | Depends |
| --- | --- | --- | --- | --- | --- |
| 1 | [TASK-0294](../tasks/done/TASK-0294-json-logs.md) | 2 | JSON logs with `request_id`, `run_id`, `trace_id` | M | acceptance |
| 2 | [TASK-0295](../tasks/done/TASK-0295-http-sql-redis-spans.md) | 2 | Opt-in HTTP, SQL, Redis spans | M | acceptance |
| 3 | [TASK-0296](../tasks/done/TASK-0296-db-redis-metrics.md) | 2 | Postgres and Redis server metrics, SQLAlchemy pool gauges | M | acceptance |
| 4 | [TASK-0297](../tasks/done/TASK-0297-llm-latency-ttft.md) | 2 | Per-call LLM latency and time to first token | S | acceptance |
| 5 | [TASK-0298](../tasks/done/TASK-0298-embedding-usage.md) | 2 | Embedding tokens and cost | M | acceptance |
| 6 | [TASK-0299](../tasks/done/TASK-0299-activity-counters.md) | 2 | Channel, MCP, browser, sandbox counters | M | acceptance |
| 7 | [TASK-0300](../tasks/done/TASK-0300-rate-limit-counters.md) | 2 | Product rate-limit hit counters | S | acceptance |
| 8 | [TASK-0301](../tasks/done/TASK-0301-run-usage-table.md) | 2 | Usage rows written at run end | M | TASK-0298 |
| 9 | [TASK-0302](../tasks/done/TASK-0302-usage-per-model.md) | 2 | Per-model table on the Usage page | S | TASK-0301 |
| 10 | [TASK-0303](../tasks/done/TASK-0303-usage-per-user-team.md) | 2 | Per-user and per-team tables on the Usage page | M | acceptance (uses TASK-0301 if merged) |
| 11 | [TASK-0304](../tasks/done/TASK-0304-channel-refusal-codes.md) | 2 | Channel refusal codes, `chat_messages` index | S | acceptance |
| 12 | [TASK-0305](../tasks/done/TASK-0305-phase2-handbook-dashboard.md) | 2 | Handbook and dashboard pass for phase 2 | S | TASK-0294 to TASK-0304 |
| 13 | [TASK-0306](../tasks/done/TASK-0306-usage-budgets.md) | 3 | Per-user and per-team budgets | L | TASK-0301, TASK-0303, DEC-0096 |
| 14 | [TASK-0307](../tasks/done/TASK-0307-slo-burn.md) | 3 | SLO targets, burn-rate alerts, error-budget card | M | TASK-0305 |
| 15 | [TASK-0308](../tasks/todo/TASK-0308-quality-signals.md) | 3 | Thumbs-down rate and workflow test results | M | TASK-0305 (scheduling) |

Each task: own branch `factory/task-NNNN-<slug>` from `develop`, own PR, REV and QA artifacts, full Factory verify and validate, all required CI including the three E2E shards green before merge. Tasks that add metrics add their dashboard panels and a short handbook entry in the same PR; tasks that add environment variables update `.env.example` and the configuration reference (en and vi).

## Sequence

1. Owner accepts REQ-0095 and this plan (or changes it); accepted tasks move from backlog to todo.
2. TASK-0294 to TASK-0300 and TASK-0304 are independent and can run in any order or in parallel.
3. TASK-0301 after TASK-0298; TASK-0302 after TASK-0301; TASK-0303 any time, preferably after TASK-0301.
4. TASK-0305 closes phase 2.
5. Phase 3: TASK-0306 after TASK-0301, TASK-0303 and DEC-0096; TASK-0307 and TASK-0308 after TASK-0305.

## New Alerts (added by the tasks that own the signal)

| Alert | Signal | Task |
| --- | --- | --- |
| Postgres connections near limit | collector `postgresql` connections over `max_connections` above 80 percent | TASK-0296 |
| Redis memory pressure | Redis used memory over `maxmemory` above 90 percent (when set) | TASK-0296 |
| Slow provider | p95 `studio.llm.duration` per provider above threshold for 10 min | TASK-0297 |
| Integration errors | error share of `studio.channel.messages`, `studio.mcp.calls`, `studio.browser.actions` or `studio.sandbox.executions` above threshold | TASK-0299 |
| Throttling spike | `studio.rate_limit.hits` increase above threshold (warning) | TASK-0300 |
| Channel refusals | `studio.chat.refused` increase above threshold (warning) | TASK-0304 |
| SLO burn, fast and slow | multi-window burn rate on run success and API availability | TASK-0307 |
| Thumbs-down spike | thumbs-down share of `studio.chat.ratings` above threshold | TASK-0308 |

## Risks

- Label cardinality from new enums: each new label is a fixed enum in `LABELS` with a test; names of servers, connections and limiter keys are never labels.
- Span volume and overhead: instrumentation is opt-in and probe routes are excluded; SQL parameters are never recorded.
- Usage table write at run end must not fail a run: write errors are logged and counted, never raised into the run result; backfill is optional.
- Embedding prices drift: shown with the unpriced share like chat models; overrides via `STUDIO_PRICES`.
- Monthly spend can exceed advisory budgets. Notifications fire once at each threshold per budget per calendar month.

## Out Of Scope

- Switching deploy template health checks to `/api/ready` (owner kept `/api/health`, DEC-0095).
- Republishing the github.io handbook (next `main` release).
- Log shipping stacks, paging integrations, `runs.events` retention (later, if the owner asks).
