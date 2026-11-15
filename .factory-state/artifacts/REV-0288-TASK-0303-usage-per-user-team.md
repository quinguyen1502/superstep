# Review

## Metadata

- Project: superstep
- Review ID: REV-0288
- Task ID: TASK-0303
- Reviewer: Grok (advisory; owner authorised the implementation, pt280u)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: approved for QA

## Review Scope

`repositories/usage.py` (`users`, `teams`, `shared_members`), `usage_service.summary`, `schemas/usage.py`, Users and Teams cards in `UsageSection.tsx`, en and vi locales, `frontend/e2e/usage.spec.ts`, tests.

## Findings

### Blocking

- None.

### Non-Blocking

- Top 20 by the same runs or cost choice as the workflows, with a total row from the window totals.
- Anonymised accounts show as "Deleted user" and their e-mail is not returned.
- A member of several teams counts toward each; the API returns how many such members exist and the page shows a note.

## Review Decision

Approved for QA.
