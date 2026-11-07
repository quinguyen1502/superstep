# Task

## Metadata

- Project: superstep
- Task ID: TASK-0265
- Title: Export HTTP Tool safeguards and idempotency
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0088
- Architecture IDs: DEC-0087
- Plan: PLAN-0008

## Objective

Public-address check, no redirects, URL Basic auth, Idempotency-Key in generated Python and TypeScript per DEC-0087.

## Acceptance Criteria

- See REQ-0088 criteria for this item; generated code executed in Python and TypeScript (Deno).

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0248-TASK-0265-export-http-safeguards.md`
- QA: `.factory-state/artifacts/QA-0248-TASK-0265-export-http-safeguards.md`

## Activity Log

- 2026-11-07: Created.
- 2026-11-07: Generated `http_request` / `httpRequest` helpers for HTTP Tool nodes and Agent HTTP tools: http(s) only, address check (same classes as core/net.blocked) unless STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1, no redirects, URL credentials as Basic auth and stripped, Idempotency-Key = sha256(SUPERSTEP_RUN_ID or random, node, method, URL, params, body)[:32]. Not pinned to the checked IP (documented). tests/test_export_http_safeguards.py runs 4 cases × Python/Deno against a local server; export suites green.
