# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0237
- Task ID: TASK-0247
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped pass; full declared verification passed

## Validation Scope And References

REQ-0086, DES-0004, ARCH-0002 URL/web refinement, DEC-0085, PLAN-0006, REV-0237 and `docs/browser-web-tools.md`. TASK-0247 delta 01b3727e; explicit unmerged stack on TASK-0246 #311. Parent final canonical full verification passed separately; no integration/merge approval inferred.

## Acceptance Criteria Coverage

- Chat/model/workflow/fixed runtime URLs: passed actual Agent/RunService fake-worker integration. Model parameters expose URL only in model mode. Fixed/state values are resolved once before tickets; forged override is refused; model template text is not rendered. Existing standalone MCP state binding works. Empty/blank/absent URLs return missing_input with zero worker/network calls and the model can ask the existing chat question.
- Search-first/missing context: passed controlled SearXNG JSON request/normalisation and actual Agent search→navigate sequencing. Unconfigured provider is unsupported, empty results are empty, malformed/refused provider responses stop explicitly. Empty query makes no request. No fallback destination is generated. Ambiguous business identity is not inferred from an order number; valid public URL alone is not identity attestation.
- Fetch-only without browser state: passed actual Agent workflow with separate web connection and zero browser workers/actions. Fresh-client transport tests verify numeric pin, Host/SNI, verified TLS, no environment proxy/cookie reuse, no search-header forwarding, public-only destination policy despite MCP private override, no redirect following, response limits/content types/compression refusal, bounded text and query-free result metadata.
- Authority/disabled-tool protection: passed API owner vs stranger, encrypted/masked headers, discovery enabled-tool filter, forged disabled search refusal, extra proxy argument rejection, feature gate and offline dry-run. Existing public-chat, browser approvals, MCP and managed tools regressions pass. Untrusted search text is returned as data and does not mutate saved origins/transport.

## Checks Performed

- URL/web/Agent/browser approval/layers: 84 passed, 18.00 s on final source before commit.
- Existing MCP/managed/parallel/approval/workflow-tool/public-chat/envelope: 121 passed, 38.97 s.
- Generated browser contracts, compile and whitespace passed; Factory ready passed before implementation.
- Full eight-command Factory profile running on committed 01b3727e. No frontend source/dependency/schema changes. No screenshots or live account/provider setup.

## UX And Accessibility Coverage

No UI component changed. Backend metadata and existing Agent/MCP/approval surfaces only. TASK-0249/0250 own labels, binding controls, trace/chat filtering and full keyboard/mobile/locale/theme acceptance. Existing typed-name delete confirmation/API behavior retained.

## Defects, Gaps And Residual Risk

No blocking scoped finding. Full declared verification passed. Search quality/availability and an operator-provisioned JSON-enabled public HTTPS SearXNG instance are not exercised by fake-provider tests. Network policy is enforced at actual candidate use; the model remains responsible for asking about ambiguous business context, constrained by saved origins/fixed bindings when configured. Shared OS resolver has no absolute timeout promise. GET is the exposed read method; no browser login/proxy is inherited. UI/recipes/executable export/release acceptance remain their assigned tasks and default-off scope.

## QA Decision

Conditionally passed for scoped review with full committed-source verification passed; owner approval pending. No done/Ready/merge approval.

- Final canonical verification on committed 01b3727e (only documentation/evidence followed): all eight commands passed. Root build/lint/test 12.68/1.20/17.97 s; backend 478.82 s; Python SDK 13.73 s; TypeScript SDK build/test/typecheck 1.59/1.36/1.45 s. No backend/Node source changed during the run. Factory verify validation/IDs follow before publication; no owner merge approval.
