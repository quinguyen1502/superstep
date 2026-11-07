# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0249
- Task ID: TASK-0267
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Rebind after the check cannot move the request: resolver answers 127.0.0.1 then 127.0.0.2 (a server listens on both, same port); only the checked server is reached and exactly one lookup happens — pass (Python, Deno).
- HTTPS: server sees SNI `pinned.test`, Host `pinned.test:<port>`, certificate for `pinned.test` verifies — pass (Python, Deno).
- HTTPS to the IP with a certificate for another name is refused before any request — pass.
- Private answer refused without `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`, one lookup — pass.
- TASK-0265 cases (redirects, Basic auth, Idempotency-Key, scheme) still pass.

## Checks Performed

- `tests/test_export_http_pinning.py` (8 = 4 × Python/Deno), `tests/test_export_http_safeguards.py`, export suites, full `factory verify run`, handbook strict build.

## Gaps Or Untested Areas

- IPv6-only hosts are not exercised with a live server (bracketed IP URL path covered by httpx/Node behaviour only).

## QA Decision

Pass.
