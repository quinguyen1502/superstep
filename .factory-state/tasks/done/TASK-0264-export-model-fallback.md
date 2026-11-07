# Task

## Metadata

- Project: superstep
- Task ID: TASK-0264
- Title: Export LLM model fallback policies
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0088
- Architecture IDs: DEC-0087
- Plan: PLAN-0008

## Objective

Replace MODEL_POLICY_EXPORT_UNAVAILABLE with generated two-step fallback per DEC-0087.

## Acceptance Criteria

- See REQ-0088 criteria for this item; generated code executed in Python and TypeScript (Deno).

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0247-TASK-0264-export-model-fallback.md`
- QA: `.factory-state/artifacts/QA-0247-TASK-0264-export-model-fallback.md`

## Activity Log

- 2026-11-07: Created.
- 2026-11-07: Removed the MODEL_POLICY_EXPORT_UNAVAILABLE refusal from export_common; generated `call_llm_fallback` / `callLlmFallback` (fail over on connection errors, HTTP 5xx, 404; once; `LLM_FALLBACK_PROVIDER`). Only the fallback model name is written; credential ids never. Nodes with attachments keep the primary only (TODO comment, documented). tests/test_export_model_fallback.py executes 7 rule cases in Python and in Deno with a local fake provider call (no network). Export suites 138 passed.
