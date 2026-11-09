# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0220
- Task ID: TASK-0225
- QA Owner: Codex (advisory local QA)
- Created: 2026-11-03
- Updated: 2026-11-03
- Outcome: pass; owner accepted for Ready finalisation

## Validation Scope

TASK-0225 against REQ-0082, accepted DEC-0077/0079, docs/ui-conventions.md and REV-0220. Widget host API, queue, appearance, identity/token lifecycle, safe events, frame/native API, existing direct/anonymous embeds, origin restrictions and the narrow API transport normalization.

## Acceptance Criteria Coverage

| Criterion | Result and evidence |
| --- | --- |
| Another-origin host identifies a user, restores only that user's history and logs out to anonymous | Pass. widget-api.spec.ts: guest order, Lan, Minh, Lan restoration, second Lan send, logout restoring the original guest HMAC/history. Parent localhost:5999, Studio 127.0.0.1:5264. |
| Events fire and foreign postMessage is ignored | Pass. Four user/assistant event pairs with safe fields, ready/open/close events, off/unsubscribe/queue unit cases; an actual localhost:5998 iframe tries a higher-epoch identity change and Lan stays signed in. Unit tests independently reject wrong source, origin, document nonce and epoch. |
| Tokens never enter URLs/storage/public event metadata | Pass. Parent/iframe storage and frame URL assertions; sanitized payload unit tests; source inspection of all postMessage/storage paths. Only structurally validated guest HMACs persist. App secret stays in Node test fixture context; traces/screenshots are disabled for auth tests. Explicit review screenshots contain only chat UI. |
| Token callback, refresh and stale identity cancellation | Pass. Browser fixture supplies expired JWTs outside the 60-second grace period until real CHAT_TOKEN_EXPIRED responses are observed, then supplies fresh tokens; identify succeeds. Unit tests cancel a slow provider on logout, ignore stale frames and abort implicit session creation before a stale socket write. |
| Appearance/data attributes, queue and same frame API | Pass. Unit data options, localized labels, theme/reset, no-remount appearance, idempotent install and queue tests. Browser en/vi/custom primary/logo/position/dark screenshots. Plain iframe identify/send/logout via window.Superstep passes. |
| Preserve existing chat and key/auth behavior | Pass. All 16 original targeted cases pass: public chat en/vi, anonymous iframe/widget persistence/CSP, attachments, Human/reviewer behavior, key rotation/revocation and third-party token isolation. New origin-negative widget case rejects a parent-only key with CHAT_ORIGIN_FORBIDDEN. |

## Checks Performed

- Full declared profile: PATH with the existing backend venv, ARM Node wrapper and local Deno runtime/cache, STUDIO_TS_EXPORT_DENO_DIR set, `.factory/bin/factory verify run --profile full`. All eight commands pass: root build (16.82s), root lint (1.91s), root tests (25.19s), backend pytest (509.33s), Python SDK pytest (16.83s), TypeScript SDK build/test/typecheck (2.23/1.25/1.49s). Log: /private/tmp/superstep-0225-verify.log; canonical result: .factory-state/verification/latest.yaml.
- Production source was committed as 64501f99 before that full run. Later changes are test-fixture corrections and workflow artifacts only. Canonical root build/lint/tests are repeated for the final delta: /private/tmp/superstep-0225-root-final.log. Backend source remains exactly the fully verified tree.
- New boundary units: 9/9; React tests: 18/18. The final root suite includes frontend 157 tests, React 18 and TypeScript SDK tests. No assertions were weakened to accept a production failure.
- Original chat regressions: 16 pass in /private/tmp/superstep-0225-regressions-final.log. That combined attempt was 18/19 because the new expiry fixture initially required exactly one rejection even though parallel GETs legitimately both expired. The corrected new widget/native suite passes 3/3 in /private/tmp/superstep-0225-widget-final.log (16.7s), requiring at least one actual expired response and successful retries.
- First combined run was interrupted during a plain-iframe send while another verification build rewrote watched generated assets; trace shows restarted/aborted page requests. Later original regressions pass after those builds finish. Initial screenshot waits on animation promises also timed out; use Playwright animations:disabled for screenshots instead. Final dark controls inherit the foreground and images are visually inspected. No production timing or security assertion was relaxed.
- Strict UI class guard and locale parity pass; required hard-coded colour/hex scans have no hits. API layer/envelope tests are included in backend pytest. No migration is needed (no schema change).
- Built Studio JS: 3,595,247 bytes; standalone widget: 10,255 bytes / 4,228 gzip, ASCII verified. No React runtime is bundled into the host widget.

## UX And Accessibility Coverage

Bubble accessible labels, expanded/controls state and iframe title use canonical en/vi strings. Existing shared shadcn inputs, keyboard submission, dialogs, Human controls and typed-name deletion remain covered. Host appearance switches preserve history. Dark input/history controls are checked against the page foreground. This is not a manual screen-reader audit.

## Evidence

Visually inspected screenshots: /private/tmp/superstep-0225-visual/widget-en.png, widget-vi-custom.png and widget-vi-dark.png. No screenshot/archive/auth state is added to Git. Browser API fixtures keep app secrets in the Node context and disable automatic traces/screenshots.

## Defects, Gaps And Residual Risk

No unresolved blocking defect. Chrome only; no Safari/Firefox/device WebView, production proxy/CSP or real model-provider claim. Widget restricted keys must allow Studio's origin; parent allowlisting remains separate. Own-origin GET fallback requires same-origin Fetch Metadata and a verified referrer, so deployment referrer/proxy policy matters. Browser partitioning may limit plain-iframe guest persistence. TASK-0226 handbook/examples and TASK-0228 platform bridges/guides remain separate tasks; this task does not complete the whole requirement.

## Assumptions And Required Follow-Up

The host authenticates its token endpoint and keeps signing secrets server-side. Review the exact pushed head's CI before acceptance; local QA is not owner approval. Preserve Python/CLI/server 0.10.2 and existing npm versions until a separately approved release.

## QA Decision

Advisory local QA passes for Draft owner review. Keep TASK-0225 in review. Ready/done/merge and publication require the owner's separate approval and applicable passing CI.


## Owner Acceptance And Ready Finalisation (2026-11-03)

The owner accepted PR #290 ("Approve") after head e6b2f7c85b22eaae3d2428abb4f665ee5b0e4260 completed 21 successful CI checks and one expected GHCR publication skip. This includes all three Playwright shards, both backend databases, Factory full verification, React 18/19 host acceptance, SDK/CLI and image/security checks. This supersedes the earlier pending-owner-acceptance/Draft-only statements.

TASK-0225 moves to done on the same PR for a rebased, single-commit Ready delivery. Current develop remains 6218d840; production source, tests, API contract and dependency versions are preserved. Required validation is repeated on the rewritten head; its actual CI outcome is reported on #290 before delivery. Merge/tag/publication remains outside this acceptance.
