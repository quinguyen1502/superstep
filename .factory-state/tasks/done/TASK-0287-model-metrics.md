# Task

## Metadata

- Project: superstep
- Task ID: TASK-0287
- Title: Model metrics, distinct 429 and unpriced usage
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-14
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
- 2026-11-09: `PROVIDER_RATE_LIMITED` (502) for HTTP 429 on the httpx path and in the SDK exception mapping (`status_code` 429 or `RateLimitError`); catalog, `docs/api-errors.md`, en/vi locales; added to `FAILOVER_CODES`. Run error events of a failed model call carry `provider` and `model`. `Telemetry.model_event` records `studio.llm.tokens` (`direction`), `studio.llm.cost` and `studio.llm.unpriced` with `model`, `provider` (`workflow_id` on tokens and cost), `studio.llm.errors` (`code`, `provider`, `model`) from failed attempts and model error events, and `studio.llm.fallbacks` (`primary_provider`, `fallback_provider`, `code`). Called for live node events in `RunService` and for AI review usage in `ApprovalService`.
- 2026-11-09: Deviation: `studio.llm.unpriced` counts calls (unit `{call}`), not tokens, with `model` and `provider` only.
- 2026-11-09: Review REV-0273 and QA-0273. Moved to review.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0273-TASK-0287-model-metrics.md`
- QA: `.factory-state/artifacts/QA-0273-TASK-0287-model-metrics.md`

## Integration

- Delivered in the bundled implementation merged into develop via PR #350 at `f4f407a8`. The lifecycle was reconciled on 2026-11-14.
