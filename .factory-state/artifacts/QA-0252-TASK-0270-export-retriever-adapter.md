# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0252
- Task ID: TASK-0270
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Configured: one POST to `/api/knowledge-bases/kb-good/search` with `Bearer tok` and `{"query", "top_k": 1}`; hits in the final state — pass (Python, Deno; local stand-in with the studio envelope).
- Studio error `KB_NOT_FOUND` stops the run — pass.
- Unconfigured offline: `(offline mock)` naming `KNOWLEDGE_BASE_1_ID` — pass.
- Unconfigured live: run fails naming the missing variables — pass.
- Agent knowledge tools share their base's prefix; ids absent — pass.

## Checks Performed

- `tests/test_export_retriever_adapter.py` (9), `tests/test_export_service_stubs.py`, export suites, full `factory verify run`, handbook strict build.

## Gaps Or Untested Areas

- Not run against a live Superstep instance with real embeddings in this test (the studio API itself is covered by `tests/test_knowledge.py`).

## QA Decision

Pass.
