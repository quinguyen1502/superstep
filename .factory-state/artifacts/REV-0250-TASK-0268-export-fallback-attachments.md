# Review

## Metadata

- Project: superstep
- Review ID: REV-0250
- Task ID: TASK-0268
- Reviewer: Grok (advisory; owner authorised, "Làm đi" 2026-11-07)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (`fallback_files` use flag), `call_llm_files(..., provider)` / `callLlmFiles(..., provider)`, new `call_llm_files_fallback` / `callLlmFilesFallback`, LLM node emission, `tests/test_export_fallback_files.py`, handbook rows.

## Findings

### Blocking

- None.

### Non-Blocking

- Same failover predicate as TASK-0264 (`fails_over` / `failsOver`); provider-specific error classes beyond those names fall into the "stop" side (safe direction).
- Agent nodes with attachments have no model fallback in Studio either; unchanged.

## Standards And Architecture Alignment

Matches `nodes.py`: the same `files` are passed to both attempts of `model_policy.run`. No credential ids emitted (asserted).

## Review Decision

Approved for QA.
