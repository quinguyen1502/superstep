# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0236
- Task ID: TASK-0246
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-05
- Updated: 2026-11-06
- Outcome: scoped pass; full declared verification passed

## Validation Scope

TASK-0246 exact-target human receipts, live waiting-resume handoff, queue crash windows and uncertain effect refusal. References: REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006, REV-0236 and `docs/browser-approvals.md`. Explicit unmerged stack on TASK-0245 #310 and its prerequisites.

## Acceptance Criteria Coverage

- Potential-effect approval: passed focused tests and real Chromium. Click/fill always require a verified human receipt; configurable read approvals also bind intent. Authenticated owner/listed inbox reviewer can grant, stranger cannot. AI/deadline/public-chat/model text cannot grant; no bounded-policy exemption implemented.
- Live authorised target: passed actual old-fence denial, same-page renewal, changed-target no-effect and expiry during review. UI→queue and queue→queue epochs, concurrent binders and deliberately reordered siblings are covered. Profile/proxy/config/access checks remain service-owned; private grants are exact command/target and absolute-expiry bound.
- Unknown outcomes never repeated: passed a real fixture POST followed by injected lost acknowledgment; result unknown, zero repeated POSTs. Unit/integration retry/fork/recovered-page refusal and generic ledger bypass pass. Missing receipt in a closed inbox rejects; valid unconsumed receipt repairs a lost enqueue. Final wave-ready recovery was applied in e7f1ab8d; two independent browser approvals recover through the existing wave-ready path, with no repeated click. A missing final receipt permits only the other verified action.
- Visible transitions/no false promise: structured rejected/expired/stale/unknown/confirmed/already_completed outcomes; acknowledgment carries no cached observation. Existing approval prompt has bounded redacted target, not raw form value/query. Full trace UI remains TASK-0250.

## Checks Performed

- Focused final contracts/runtime/remote/approval/session/migration/layers/envelope: 92 passed, 4 optional skips on c7cb3af7.
- Earlier generic approval/parallel/channel/public-chat regression: 70 passed, 1 optional skip before final additions.
- Disposable PostgreSQL 17 Alpine + SQLite: 9 passed; migration 0057 downgrade/upgrade preserves existing session/command/wait records without inventing old receipts/proof. Container/data removed.
- Actual `scripts/test-browser-remote.py`: passed verified pinned HTTPS, renewal with old-context refusal, six operations, three proxy modes/no fallback, host/origin profile boundaries, redaction, anonymous fresh context and own-label restart cleanup.
- Actual `scripts/test-browser-approval.py --skip-build`: passed worker grant expiry/no effect, same-page handoff, old fence and old supervisor, target mutation/no effect, lost acknowledgment/unknown, exactly two intended POST effects and zero repeated effects, session expiry during review. Disposable resources removed; screenshots written to Git: 0.
- Generated contracts, Node syntax, compile/whitespace and Factory validate passed. Full declared eight-command profile passed on c7cb3af7 (backend 483.79 s). The final wave/purge fix is undergoing its own full profile on isolated 2d0d6159, identical backend source to task e7f1ab8d.

## UX And Accessibility Coverage

Existing approval/inbox and reviewer-only chat presentation reused; en/vi backend prompts and safe trace arguments inspected. No new UI component. TASK-0249/0250 own complete settings/trace/mobile/accessibility acceptance.

## Defects, Gaps And Residual Risk

REV-0236 wave gap is resolved and tested. Final committed-source full declared verification passed. Runtime remains experimental/default off; live credentials, third-party deployment, recipes/UI/export and release acceptance are not claimed. Site effects after dispatch may be unknown and cannot be undone; the conservative outcome closes rather than retries. Janitors retain minimal encrypted cleanup authority through infrastructure outages, with capacity held. Exact-context reattachment requires the same local Docker daemon or approved HTTPS controller. Self-QA does not replace owner approval.

## Required Follow-Up And QA Decision

Conditionally passed for scoped review with final committed-source full verification passed; owner approval pending. Remain review; no done/Ready/merge authority inferred.

- 2026-11-06 final source verification: canonical full profile on isolated 2d0d6159 passed all 8 commands, backend 481.74 s, Python SDK 14.29 s, root build/lint/test 16.03/2.14/19.28 s, TS SDK build/test/typecheck 1.66/1.47/1.52 s. Root final approval/child/restart/parallel/deadline regression: 47 passed (76.24 s). Final backend source is identical to task e7f1ab8d; only workflow evidence/docs followed. Isolated workspace now uses its own exact lockfile dependencies; the earlier shared-node_modules resolution failure did not require source or lock changes. Factory verification metadata records all eight passes. Draft PR #311; no done/Ready/merge approval.
