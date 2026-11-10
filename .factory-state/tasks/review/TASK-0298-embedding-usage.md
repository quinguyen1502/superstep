# Task

## Metadata

- Project: superstep
- Task ID: TASK-0298
- Title: Embedding usage: tokens and cost
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: M

## Objective

Count embedding calls (knowledge ingestion and RAG queries) the same way as chat model usage.

## Owner-Facing Outcome

Operators see embedding tokens and cost per model in Grafana, and the run totals and Usage page include embedding cost made during runs, with unknown prices counted as unpriced.

## Scope

### In Scope

- Providers' `embed` returns a usage record (provider-reported tokens when available, estimated otherwise) through `engine/embeddings.py`; the mock embedder reports nothing.
- Prices for common embedding models in `engine/usage.py`, overridable with `STUDIO_PRICES` / `STUDIO_PRICES_FILE` like chat models.
- `studio.embedding.tokens`, `studio.embedding.cost`, `studio.embedding.unpriced` with labels `model`, `provider`, plus `source` (`ingest` or `query`).
- Embedding usage inside a run (RAG node, knowledge tools) adds to that run's `tokens_in` and `cost_usd` and appears as a usage event so TASK-0301 can store it with kind `embedding`.
- Ingestion outside a run is reported in metrics only. New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Attributing ingestion cost to a user on the Usage page (follows from TASK-0301 if wanted later).

## Dependencies

- None (TASK-0287 merged).

## Acceptance Criteria

- Ingesting a document with a mocked OpenAI-compatible embedder increments embedding tokens and cost; an unknown embedding model increments `studio.embedding.unpriced` only.
- A run with a RAG node reports embedding tokens in its totals; the run panel and existing exports are unchanged in shape.
- Mock embedder (no credential) records nothing; knowledge base tests stay green.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.
- 2026-11-10: Embedding token counts from provider responses (OpenAI usage, Ollama `prompt_eval_count`, estimate otherwise); prices for the OpenAI embedding models. Counters `studio.embedding.tokens`, `studio.embedding.cost`, `studio.embedding.unpriced` (model, provider, source). Runs add query embedding tokens to their totals.
- 2026-11-10: Deviation: embedding usage is a separate `embedding_usage` field on node events; ingestion is metrics only.
- 2026-11-10: Review REV-0283 and QA-0283. Moved to review.

## Handoff Notes

- Use branch `factory/task-0298-embedding-usage` from `develop` when implementation begins.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0283-TASK-0298-embedding-usage.md`
- QA: `.factory-state/artifacts/QA-0283-TASK-0298-embedding-usage.md`
