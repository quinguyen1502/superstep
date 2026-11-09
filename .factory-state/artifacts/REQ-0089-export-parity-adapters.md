# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0089
- Status: Owner-authorised 2026-11-07 ("Do it" on the recommended next sequence after REQ-0088: 1 HTTP pinning and fallback with attachments, 2 split TASK-0266 and implement real MCP / Retriever / email export adapters, 3 honest factory metadata cleanup). Steps 1 and 2 are merged, including PR #333 (`bbbd23b2`) for TASK-0271. Step 3 is TASK-0272 (REV-0258, QA-0258) and is not merged. REQ-0089 is not marked done.
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-07
- Related: REQ-0088, DEC-0087, DEC-0088, PLAN-0009, TASK-0266 (split by this requirement); browser export (REQ-0086, TASK-0251/0252/0261/0262) and native TASK-0227 excluded

## Summary And Scope

1. Exported HTTP Tool requests connect to the address they checked (no DNS-rebinding window), keeping Host, TLS SNI and certificate checks on the name; private/redirect rules unchanged.
2. An exported LLM node with both a fallback model and attachments applies the fallback as Studio does: same prompt and files, same failover rules, at most one fallback call.
3. TASK-0266 is split; real MCP, Retriever and Send email adapters are exported in Python and TypeScript, configured only from environment variables, never pretending success when not configured.
4. Factory metadata: a real review of done TASK-0253, distinct REV/QA ids, merged task statuses reconciled, `factory validate` passing without suppression.

Out of scope: cross-language code nodes, approval channels/deadlines/AI review outside Studio, per-node provider credentials, managed connections, browser export, native mobile.

## Business Rules

- No Studio credential, server secret or connection value is written to an exported file.
- Offline example mode (no `LLM_PROVIDER`, adapter not configured) keeps the announced Studio mock results; a live run with an unconfigured adapter stops with an error naming the missing variable.
- Generated security behaviour is not weaker than Studio's.

## Acceptance Criteria

- Generated Python and TypeScript (Deno) are executed in tests against local servers or local fakes only (no external or paid calls).
- HTTP: a rebind after the check cannot move the request (one lookup); HTTPS uses SNI and verifies the certificate for the name; private targets refused unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`; redirects not followed.
- Fallback with attachments: fallback receives the same files; failover only on unreachable / 5xx / 404; at most two calls; offline only the primary mock.
- Adapters: configured → real call to a local test server; unconfigured live → error; unconfigured offline → announced mock.
- Metadata: validate passes on the real repository state; no fabricated evidence.
- en/vi handbook updated; full Factory verify/validate; REV/QA; all required CI green before merge.
