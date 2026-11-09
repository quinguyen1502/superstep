# QA Report

- Project: superstep
- QA ID: QA-0217
- Task ID: TASK-0222
- Created/Updated: 2026-11-02
- QA Owner: Codex, advisory
- Outcome: pass; owner accepted 2026-11-02; rewritten-head CI required before Ready
- References: REQ-0082, PLAN-0002, DEC-0077–0080, REV-0217, TASK-0222 in done

## Acceptance Coverage

| Criterion | Verification / evidence |
| --- | --- |
| chat-host-e2e green in CI | Required automated gate: `Chat host e2e (two origins)` on this task's Draft PR; the latest-head check and PR description record the CI result. Its exact local equivalent `scripts/chat_host_e2e.sh` passes three Node cases and the complete real-browser scenario. Check the gate before promotion. |
| Host screenshots in PR | Six UI-only images attached by Playwright: en/vi light/dark, mobile and revoked key. CI uploads `chat-host-screenshots` for 14 days and the PR links that artifact. Per owner amendment images are never committed. Local review copies are under `/private/tmp/superstep-chat-host-0222-screenshots/`. |

## Functional, UX And Security Evidence

- Actual Chrome communicates from localhost:5188 to 127.0.0.1:8131; no API/socket proxy hides CORS. Positive preflight and bearer reads pass; localhost:5189 receives HTTP 403 and socket CHAT_ORIGIN_FORBIDDEN. Socket URLs contain no query token and HTTP requests have no cookie.
- Two browser contexts sign in as different fixed demo customers. The other customer cannot list/read the first session (404); another context for the same customer restores its history/rating. No arbitrary user ID is accepted by sign-in/minting.
- Upload a text document, send, receive a Human question, answer with a JSON form, observe token/done frames and persisted answer, save rating. Revoking the actual key produces an error and the owner view proves no extra turn was written. All calls use temporary data and mock models.
- shadcn controls and existing theme/i18n are reused. en/vi keys match, field/button labels and keyboard controls are standard components, log/status/error announcements exist, responsive 390px layout has no horizontal overflow. All four desktop theme/locale variants and mobile were inspected through screenshots. File controls use localised labels rather than browser-native English text.
- Node tests cover sign-in/tamper/origin rejection, server-derived JWT identity/HS256 signature/TTL, HttpOnly/SameSite/no-store, logout invalidation, explicit demo startup, secret-safe failure, locale parity, static traversal refusal and CSP. Test scripts refuse occupied ports before seeding and pin DB attachment storage so ambient external-service configuration is not used.
- Real-browser testing exposed and resolved the SDK fetch receiver issue; the updated 20-case shared contract runs in Node/jsdom/native-like environments (94 total unit tests), including default and explicit native-fetch receivers.

## Checks

- Full Factory profile on committed 80116c2: eight passed. Backend 480.53 s; frontend build/lint/test 6.91/0.94/5.89 s; Python SDK 14.53 s; TypeScript build/test/typecheck 1.31/1.23/1.43 s. Final script-only isolation guard was then rechecked by the host/SDK scripts and an actual occupied-port refusal.
- Final local host acceptance after cleanup/guards: Node 3 passed, Playwright 1 complete scenario passed (2.7 s test, 3.5 s total), including mobile and six screenshots; no console page errors. Final sample oxlint and strict UI class checks pass.
- SDK integration after final guards: Python 8 passed (2.00 s), TypeScript 7 passed (1.05 s total). TypeScript unit 94 passed; typecheck/gen:check and build pass.
- Handbook en/vi builds pass (1.64/1.97 s) and all images resolve. Source changes add no images or dependency package. Final Factory/ID/whitespace checks precede push; CI results remain attached to the PR's exact head.

## Limits And Handoff

This sample deliberately uses a local sign-in stub, not production authentication/deployment. No real customer/provider/device test was performed; mobile is a browser viewport, not React Native. React toolkit/widget/native packages remain later tasks. Python retains the shared SDK/CLI/server version until a separate release approval; TypeScript target remains 0.2.0. Source CI and owner acceptance are required before merge/publication; task stays in review, stacked on #286 then #285.

## Owner Approval And Finalisation

Owner accepted the reviewed phase-2 stack on 2026-11-02 ("Approve"). This task moves to done on existing #287, restacked onto finalised #286 and squashed for Ready delivery after final gates. The reviewed fetch binding change and shared regression have moved to #285; no final stack source behaviour changes. Original head ae16a7c passed the host gate and all 19 successful checks (one deployment skip), with screenshots at https://github.com/quinguyen1502/superstep/actions/runs/41434119564/artifacts/13134549352. Rewritten-head CI must pass and its fresh screenshot artifact must be linked before Ready. Earlier review/pending entries are historical. Merge and publication remain unapproved; no images are committed.

Finalisation rerun on the squashed stack: Node host security/locales/static tests 3 passed; actual Chrome cross-origin scenario passed (2.7 s, 3.6 s total), including six screenshots and mobile layout. Isolated SDK integration passed Python 8 (1.95 s) and TypeScript 7 (1.12 s total). Comparison with owner-reviewed ae16a7c shows only lifecycle/review/QA/roadmap differences across the complete stack; no implementation source difference. A final full profile is also running on the squashed stack, with exact-head CI required before Ready.
