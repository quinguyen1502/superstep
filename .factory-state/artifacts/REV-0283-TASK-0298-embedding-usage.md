# Review

## Metadata

- Project: superstep
- Review ID: REV-0283
- Task ID: TASK-0298
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`backend/app/engine/providers.py` (`embedding_tokens`, `embed_with_usage`), `backend/app/engine/embeddings.py` (`observe`, `collect`, sources), `backend/app/engine/usage.py` (embedding prices), `backend/app/services/knowledge_service.py`, the retriever node and knowledge tool, `backend/app/engine/runtime.py` (`embedding_usage`), `backend/app/services/telemetry.py` (`studio.embedding.*`, run summary), dashboard, handbook (en and vi), `backend/tests/test_model_latency.py`.

## Findings

### Blocking

- None.

### Non-Blocking

- Embedding usage is kept apart from model usage (`embedding_usage` on `node_finished`), so the run panel and exports keep their shape.
- An unpriced embedding model adds tokens but does not turn the run cost into NULL; it counts in `studio.embedding.unpriced`.
- Document ingestion is counted in metrics only (source `ingest`), not in any run.

## Review Decision

Approved for QA.
