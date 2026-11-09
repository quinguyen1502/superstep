# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0088
- Status: Owner-authorised 2026-11-07 ("Fix it" on the code-export gap audit at develop a8471f0b); remaining design gaps proposed, not accepted
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-07
- Related: DEC-0087, PLAN-0008, TASK-0263..0266; REQ-0043/0047 (exports); browser export (REQ-0086, TASK-0251/0252/0261/0262) excluded

## Summary And Scope

Fix code-export gaps confirmed by the audit, in Python and TypeScript, without faking success:

1. Studio-service stubs (Retriever / Agent knowledge, MCP / Agent MCP, Send email) must not silently succeed in a real run.
2. Missing targets at export time (subgraph, workflow tool, registered function) must fail when reached, naming the target.
3. LLM model fallback policies export instead of being refused, keeping Studio order and failover rules.
4. Exported HTTP Tool (node and Agent HTTP tool) keeps Studio safeguards: public-address check, no redirects, `user:pass@` auth, idempotency key.

Out of scope (TASK-0266, proposal only): running another language's code nodes, approval channels/deadlines/AI review outside Studio, per-node provider credentials, real MCP/retriever/SMTP adapters, browser export.

## Business Rules

- No credential, connection, server, channel or secret value is written to an exported file; external configuration is read from environment variables.
- Offline example mode (no `LLM_PROVIDER`) keeps the Studio mock results so examples and parity tests stay runnable, and announces each mocked service on stderr.
- With `LLM_PROVIDER` set, an unimplemented service stops the run with an actionable error.
- Security behaviour in generated code is never weaker than Studio's.

## Acceptance Criteria

- Generated Python and TypeScript files are executed in tests (Deno for TypeScript): offline mock announced, live run refused, missing subgraph fails naming the target.
- Model fallback export: primary then fallback model, failover only on unreachable/bad-response/model-not-found errors, at most two calls; executed in both languages with a fake provider.
- HTTP export: private/loopback targets refused unless `STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1`, redirects not followed, URL credentials sent as Basic auth, stable `Idempotency-Key`; executed in both languages.
- en/vi handbook support matrix updated; full Factory verify/validate, REV/QA, all required CI green before merge.
