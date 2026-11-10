# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0283
- Task ID: TASK-0298
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Ingest with a mocked OpenAI-compatible embedder increments tokens and cost; unknown model increments unpriced only: pass (`test_embedding_tokens_and_cost_by_source`, `test_unpriced_embedding_adds_tokens_but_keeps_the_run_cost`).
- RAG run reports embedding tokens in its totals with the run panel shape unchanged: pass (`test_rag_run_counts_query_embedding_in_its_totals`).
- Mock embedder records nothing; knowledge base tests stay green: pass (`test_mock_embedder_records_nothing`, full suite). Ollama `prompt_eval_count` read: pass (`test_ollama_reports_embedding_tokens`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_model_latency.py tests/test_knowledge*.py`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
