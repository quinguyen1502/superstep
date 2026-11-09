# Review

## Metadata

- Project: superstep
- Review ID: REV-0215
- Task ID: TASK-0220
- Reviewer: Codex self-review, advisory; owner accepted 2026-11-02
- Created/Updated: 2026-11-02
- Outcome: approved for QA; full regression verification passed, owner accepted 2026-11-02

## Scope And References

Diff against develop 019071e: TypeScript SDK client/chat/server exports, transport, generated socket types, stream/store, token signing, tests/fixtures, package/dev dependencies, README and CI integration. The backend change is limited to bounded JSON answers opted into by the chat v1 route, with common error text/locales. No schema, migration or UI controls.

References: TASK-0220 in done, REQ-0082, PLAN-0002, DEC-0077–0080, DEC-0009/0010, QA-0215.

## Findings

- No unresolved blocking implementation findings.
- Resolved: the backend rejected forms allowed by its v1 schema. A first broad validator change also accepted forms on legacy APIs; the full suite caught that LangGraph regression. An explicit server-side opt-in now restricts forms to v1 chat. The original LangGraph/studio assertions remain unchanged and pass; forms remain objects through validation, execution and persistence, with strict JSON/Unicode/size bounds.
- Resolved: aborting while reading the HTTP body now preserves the host's abort reason; the regression runs in all three runtime contracts.
- Non-blocking: actual native devices and a cross-origin browser host are later tasks (TASK-0227/TASK-0222); current native coverage is simulated, and Node 18/20/22 matrix validation is delegated to existing CI.

## Standards And Architecture

HTTP workflow/chat share the envelope parser and typed errors. Backend routers call services; form handling is in RunService, never in a router, and the opt-in is server context rather than an untrusted request flag. Error catalog/docs/en/vi match. No raw SQL, new tables, runtime dependency, vendor node, or duplicated UI. jsdom 26.1.0 is test-only, documented in the task and compatible with the package's Node 18 baseline.

Browser/native entries do not export the signing helper or import server crypto. JWTs use literal UTF-8 app-key secrets, bounded claims and backend-compatible audience/issuer. Shared synthetic vectors verify Web Crypto and Node fallback output against the real backend verifier; no real credentials are committed. Headers/auth frames carry tokens, redirects/cookies are omitted, and workflow credentials are not forwarded to chat.

Only explicit pre-execution expiry permits one resend; revocation/origin refusals never refresh. A dropped connection uses bounded read-only history recovery and only confirms a new assistant turn for the known run ID. Queue/text/frame limits, cancellation, listener cleanup, stale store work and identity bootstrap concurrency are covered. No automatic replay of ambiguous writes.

## Validation And Follow-Up

91 SDK unit cases (19 shared contract cases in Node/jsdom/native-like), generated types, typecheck, ESM/CJS exports and pack contents passed. Corrected targeted backend suite: 40 passed, including legacy LangGraph/studio/inbox, v1 schema, layers and envelope. Corrected live integration: Python workflow 2 passed; TypeScript workflow/chat 7 passed. Full Factory verification after the correction passed all eight checks on 9aeeba8 (backend 471.48 s; frontend build/lint/test 6.38/0.88/5.28 s; Python SDK 13.44 s; TypeScript build/test/typecheck 1.25/1.10/1.38 s). No screenshots are required for this headless change and no evidence images are committed. Owner approval is separate from this review.

## Owner Approval And Finalisation

Owner approved the reviewed phase-2 stack on 2026-11-02 ("Approve"). The task moves to done in the existing #285, to be squashed and marked Ready after final gates. This does not authorise merging or package publication. The browser fetch binding correction discovered and reviewed in TASK-0222 is included here with its existing default/explicit-fetch regression: 20 shared contract cases, 94 total SDK unit tests. No new behaviour is added beyond the reviewed final stack. Earlier pending-acceptance entries above are historical. Final-head CI remains the delivery gate.
