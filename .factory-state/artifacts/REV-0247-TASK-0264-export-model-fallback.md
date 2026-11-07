# Review

## Metadata

- Project: superstep
- Review ID: REV-0247
- Task ID: TASK-0264
- Reviewer: Grok (advisory; owner authorised the fixes and green merge)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (refusal removed, `fallback` use flag), `python_export.py` / `typescript_export.py` (model section, LLM node emission, reserved names), `tests/test_export_model_fallback.py`, `tests/test_model_fallback.py`, handbook en/vi rows.

## Findings

### Blocking

- None.

### Non-Blocking

- Status classification is heuristic across LangChain providers (status_code/status/response.status, named connection errors); unknown error shapes do not fail over, which errs toward Studio's "stop on non-failover errors".
- LLM nodes with attachments plus fallback keep the primary only, with a TODO and a documented row.
- `MODEL_POLICY_EXPORT_UNAVAILABLE` stays in the error catalog (no longer raised) to avoid frontend/catalog churn.

## Standards And Architecture Alignment

Credential ids are not emitted (asserted). Provider and keys come from the environment only.

## Review Decision

Approved for QA.
