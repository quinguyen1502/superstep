# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0050
- Status: Done (TASK-0087, PR #132)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner request in chat, 2026-10-24 (item 3 of 5: LangSmith evals, opt-in, mocked in tests).

## Summary

- Workflow test suite runs can be sent to LangSmith as a dataset + experiment (opt-in via LANGSMITH_* env and an admin setting); runs traced to LangSmith link to their LangSmith trace.

## Acceptance Criteria

- With `LANGSMITH_API_KEY` set and the admin setting on, a finished suite run is sent in the background: one dataset per workflow (examples keyed by test id, kept in sync), one experiment per suite run with one run per case and `passed` plus per-check feedback.
- The Tests panel shows **Open in LangSmith** (stored experiment URL) and, for editors, **Send to LangSmith**.
- `GET|PUT /api/admin/langsmith` (USERS_MANAGE, audited) never returns the key; `POST /api/workflows/{wid}/tests/runs/{sid}/langsmith` (editors).
- When tracing to LangSmith and `STUDIO_TRACE_URL` is unset, `trace_url` links to the LangSmith run (UUID of the root span id).
- Errors `LANGSMITH_NOT_CONFIGURED`, `LANGSMITH_PUSH_FAILED` in the catalog, docs/api-errors.md and both locales; tests use a fake client (no real key).
- Handbook en+vi, CHANGELOG Unreleased.

## Out Of Scope

- A real LangSmith account check (none available).
- Per-team settings (one studio-wide admin setting).
