# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0248
- Task ID: TASK-0265
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Private/loopback refused unless STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1 — pass (Python + Deno, no request reached the server).
- Redirects not followed — pass (single request to /redirect).
- URL credentials as Basic auth, not in the URL — pass (`alice:p@ss` decoded from percent-encoding).
- Stable Idempotency-Key per run id and request; different run id → different key — pass.
- Non-http scheme refused — pass.

## Checks Performed

- `tests/test_export_http_safeguards.py` (8 cases), all export suites with Deno, full `factory verify run`, handbook strict build.

## Gaps Or Untested Areas

- Agent HTTP tools use the same helper (covered by generated-code assertions and existing agent export runs, not a live server call).
- DNS-rebinding window remains (no pinning).

## QA Decision

Pass.
