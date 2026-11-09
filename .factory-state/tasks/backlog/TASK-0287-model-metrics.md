# Task

## Metadata

- Project: superstep
- Task ID: TASK-0287
- Title: Model metrics, distinct 429 and unpriced usage
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: M

## Objective

Give Grafana per-model visibility and make provider failures and unknown prices visible without changing run behaviour.

## Scope

### In Scope

- `studio.llm.tokens` (`direction`) and `studio.llm.cost` per node usage with labels `model`, `provider`, `workflow_id`; recorded when a node or AI review reports usage.
- `studio.llm.unpriced` counter (tokens or calls whose `cost_usd` is None) with `model`, `provider`, so missing `STUDIO_PRICES` entries are visible.
- `studio.llm.errors` counter by `code`, `provider`, `model`.
- New provider error code `PROVIDER_RATE_LIMITED` for HTTP 429 in `engine/providers.py` (both the httpx path and the SDK exception mapping), message in `core/errors.py` and the en/vi frontend locale catalogs; added to `FAILOVER_CODES`; HTTP status to clients stays 502.
- `studio.llm.fallbacks` counter when the fallback model is used (labels: primary and fallback `provider`, `code` of the primary failure).
- Run-level `studio.cost` keeps its meaning; document that it skips unpriced runs.

### Out Of Scope

- Per-call latency and time to first token, embedding usage (phase 2); usage table (phase 3).

## Dependencies

- TASK-0285 merged.

## Acceptance Criteria

- A mocked 429 raises `PROVIDER_RATE_LIMITED`, triggers fallback exactly like today's `PROVIDER_BAD_RESPONSE`, and is counted separately from 5xx.
- Unknown-model usage increments `studio.llm.unpriced` and not `studio.llm.cost`.
- No metric carries `user_id` or `run_id`; label set checked in tests.
- Existing run, export and provider tests stay green; en/vi locale parity passes.

## Validation Plan

- Targeted backend tests (`pytest`) and, where touched, frontend `npm run lint`, `npm run build`, `npm test`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
