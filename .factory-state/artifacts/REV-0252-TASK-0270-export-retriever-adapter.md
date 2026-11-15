# Review

## Metadata

- Project: superstep
- Review ID: REV-0252
- Task ID: TASK-0270
- Reviewer: Grok (advisory; owner authorised, "Do it" 2026-11-07)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (`_knowledge_base` key, `kb_prefix`), Retriever adapter blocks and call sites in both exporters, `tests/test_export_retriever_adapter.py`, updated assertions in export / stub tests, handbook en/vi, DEC-0088.

## Findings

### Blocking

- None.

### Non-Blocking

- The exported file depends on a reachable Superstep server and a user token (`POST /api/auth/login` JWTs expire); it is not a standalone retriever. Documented as the chosen design.
- `SUPERSTEP_URL` is operator configuration: no private-address guard (a local studio is the common case); redirects are not followed.
- The query is sent as rendered; Studio's own validation (`KB_QUERY_REQUIRED`, embedder checks) applies server-side and its error code is surfaced.

## Standards And Architecture Alignment

Uses the documented public API and response envelope; ids and tokens are never written to the file (asserted).

## Review Decision

Approved for QA.
