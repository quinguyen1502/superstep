# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0027
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: project review on 2026-10-18 and the owner's reply, “No need to fix the CI billing. First finish task 0038. Then come back to the issues you raised.”

## Summary

Fix the defects and leftovers found in the 2026-10-18 project review, except GitHub Actions billing, which the owner keeps as is.

## Problem Or Opportunity

- The HTTP Tool node sends a request to any URL the author types, including loopback, private, and cloud-metadata addresses. Webhooks and MCP servers already refuse those addresses.
- A Condition node falls back to substring matching. With the labels `approve` and `disapprove`, the value `Disapprove.` can take the `approve` branch, depending on label order.
- 16 Playwright specs fail on macOS on a clean `develop`. Most press `Control+…` where the app uses `⌘` on a Mac, two fill a `textarea` that is now the CodeMirror run input, and several cannot click `⋯` or Cancel because at 1280px the editor header's info badges (LLM mode, id) cover them.
- Project records are stale: `project.md` still describes the SQLite-only MVP, and REQ-0024 and REQ-0025 are still `Approved` although their tasks are merged.
- Smaller leftovers: CORS is always `*`, JWTs in WebSocket query strings are written to the access log, `backend/studio.db.migrate.lock` is tracked, `dev.sh` keeps a `backend/.venv` that has no packages, SQLAlchemy 2.1 warns about `Result.tuples()`, oxlint reports 47 warnings (46 are React hook rules in data-loading effects, one reads a function before its declaration), and the JavaScript bundle is one 1.5 MB chunk.

## Scope

### In Scope

- SSRF guard for HTTP Tool nodes, sharing one implementation with webhooks and MCP
- Deterministic Condition matching
- Playwright specs that pass on macOS and Linux
- `project.md`, roadmap, and requirement statuses that match `develop`
- The editor header at 1280px
- CORS origins from configuration, token redaction in the access log, untracking the migration lock file, `dev.sh` repair of an empty venv, the SQLAlchemy deprecation, the `react(immutability)` oxlint warning, and route-level code splitting

### Out Of Scope

- GitHub Actions billing (owner decision)
- Changing the repository default branch on GitHub (a repository setting; the owner decides)
- Splitting `frontend/src/pages/Editor.tsx` and the 46 React hook oxlint warnings (one separate task: they need a shared data-loading hook)
- Moving the browser session token out of `localStorage`

## Stakeholders Or Users

- Workflow authors, administrators, and developers running the suite locally

## Desired Behavior

- An HTTP Tool node whose URL resolves to a loopback, private, link-local, reserved, multicast, or unspecified address fails with `HTTP_TOOL_URL_BLOCKED`, unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`. Only `http` and `https` are allowed. The request connects to the address that was checked (no DNS rebinding) and does not follow redirects.
- A Condition value picks a branch in this order: exact label match, then case-insensitive match after trimming spaces and trailing punctuation, then the longest label that appears as a whole word in the value, then the default. Two labels of the same longest length that both match as whole words are ambiguous and use the default, or fail if there is none.
- `STUDIO_CORS_ORIGINS` (comma-separated) sets the allowed origins. Unset: `*` in development and no cross-origin access in production.
- `token=` values in access-log lines are replaced by `token=***`.
- When the header is too narrow, the info badges clip. They never cover the centre actions.

## Business Rules

- New error codes go in `core/errors.py` `CATALOG`, `docs/api-errors.md`, and both locale files.
- The engine imports only `core` (DEC-0009). The shared address check lives in `core`.

## Constraints

- No new API route. No schema change.
- Existing workflows that call public URLs keep working.

## Acceptance Criteria

- An HTTP Tool node with `http://127.0.0.1/…`, `http://169.254.169.254/…`, or a hostname that resolves to `10.0.0.5` fails with `HTTP_TOOL_URL_BLOCKED` and does not send a request. A public address succeeds. `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1` allows the private address.
- With labels `approve` and `disapprove`, `Disapprove.` takes `disapprove` and `I approve` takes `approve`, in either label order. Existing condition tests pass.
- The Playwright suite has no failures caused by the platform key on macOS.
- At 1280×720 the editor's `⋯`, Run, Save, and Cancel buttons receive clicks.
- `project.md` lists the current stack, commands, and test count. REQ-0024 and REQ-0025 match their delivered state (REQ-0026 is updated by PR #41).
- `npx oxlint` reports no `react(immutability)` warning, and `vite build` emits separate Editor and Settings chunks.
- `tests/test_layers.py` and `tests/test_api_envelope.py` pass.

## Edge Cases

- A hostname with several addresses is refused if any address is blocked.
- A URL template that renders to an empty or non-http value fails with the same code.

## Assumptions

- The owner's reply approves fixing every review item except CI billing. The default-branch change and the Editor split are left for the owner to decide.

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0039-review-hardening.md`
- Architecture: `docs/backend-architecture.md`
- Errors: `docs/api-errors.md`
