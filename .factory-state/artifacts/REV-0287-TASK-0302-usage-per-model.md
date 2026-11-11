# Review

## Metadata

- Project: superstep
- Review ID: REV-0287
- Task ID: TASK-0302
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`repositories/usage.py` (`models`, `usage_since`), `usage_service.summary`, `schemas/usage.py`, `frontend/src/lib/usage.ts`, `frontend/src/pages/settings/UsageSection.tsx` (Models card), en and vi locales, `frontend/e2e/usage.spec.ts`, tests.

## Findings

### Blocking

- None.

### Non-Blocking

- Sorting by cost, tokens or calls is done in the client with a Select; the API returns the window rows.
- The card shows the date per-model data starts (first `run_usage` row) so older windows are not mistaken for zero use.

## Review Decision

Approved for QA.
