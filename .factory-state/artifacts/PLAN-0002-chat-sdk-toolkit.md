# Plan

## Metadata

- Plan ID: PLAN-0002
- Requirement: REQ-0082 (chat SDK and toolkit for third-party web and mobile apps)
- Decisions: DEC-0077 (third-party auth), DEC-0078 (API versioning, schema, transport), DEC-0079 (package layout and UI reuse), DEC-0080 (React Native approach). All Accepted on 2026-10-31.
- Tasks: TASK-0215 to TASK-0230 (plan accepted 2026-10-31; phases 1–3 merged through #291; TASK-0229 merged (#292, 42333ffc); TASK-0230 merged (#293, d2119965); TASK-0238 done for owner-authorised 0.11.0 release; TASK-0230 follows its merged foundation; native tasks deferred)
- Date: 2026-10-31
- Delivery: one PR per task into `develop`, branch `factory/task-NNNN-<slug>`; a task starts only when its dependencies are merged.

## Phase 1 delivery (2026-11-01)

| Task | PR | Delivery |
| --- | --- | --- |
| TASK-0215 Public Chat HTTP v1 | [#273](https://github.com/quinguyen1502/superstep/pull/273) | Merged |
| TASK-0216 Socket protocol/schema v1 | [#274](https://github.com/quinguyen1502/superstep/pull/274) | Merged |
| TASK-0217 App keys | [#275](https://github.com/quinguyen1502/superstep/pull/275) | Merged after final CI passed |
| TASK-0218 Third-party user tokens | [#276](https://github.com/quinguyen1502/superstep/pull/276) | Merged after final CI passed |
| TASK-0219 Handbook/compatibility | [#277](https://github.com/quinguyen1502/superstep/pull/277) | Owner-approved; task moved to done on this PR; all final-head CI required before merge |

Phase-1 review and QA evidence lives in the corresponding done tasks (TASK-0217: REV/QA-0205, TASK-0218: REV/QA-0206, TASK-0219: REV/QA-0207). The complete REQ-0082 remains Accepted because later phases are incomplete. No app/SDK release or package publication is implied by completing phase 1.

## Phase 2 progress (2026-11-02)

Owner explicitly authorised merging #285–287 and continuing TASK-0223 on 2026-11-02. All three PRs are merged into develop after rebase/retarget and final-head checks (20 / 19 / 21 passed). Phase 2 is integrated; no SDK/app publication or tag is authorised. TASK-0223 starts phase 3 with shared UI extraction and regression checks; hooks, theme, widget and native work remain later tasks.

Owner amendment on 2026-11-02: Python now shares version 0.10.2 with CLI/server, so preserve that version until the next approved shared release (phase grouping still proposes 0.11.0). Do not downgrade Python to the obsolete 0.2.0 target. TypeScript keeps its independent 0.2.0 package target.

## Order and dependencies

| Task | Phase | Size | Depends on | Main pieces |
|---|---|---|---|---|
| TASK-0215 public chat API v1 | 1 | M | none | `/api/public/v1/chat`, aliases, `turns?after=`, public OpenAPI |
| TASK-0216 socket protocol v1 | 1 | M | 0215 | typed frames, JSON Schema, AsyncAPI, contract tests |
| TASK-0217 app keys | 1 | L | 0215 | `chat_app_keys`, access set, encrypted secrets, rotate and revoke, settings UI |
| TASK-0218 user tokens | 1 | L | 0216, 0217 | HS256 verifier, per-user scoping, CORS, limits, error codes |
| TASK-0219 handbook (API, auth, compatibility) | 1 | M | 0218 | en and vi pages, CHANGELOG |
| TASK-0220 TypeScript SDK chat | 2 | L | 0218 | `client.chat`, async iterator, refresh, `createChatStore`, `mintChatToken`, 0.2.0 |
| TASK-0221 Python SDK chat | 2 | M | 0218 | sync and async chat, `mint_chat_token`, `superstep[chat]`, shared SDK/CLI/server version |
| TASK-0222 sample host and e2e | 2 | M | 0220, 0221 | `examples/chat-host`, cross-origin Playwright job |
| TASK-0223 extract `@superstep/react` | 3 | L | 0216 | npm workspace, move chat UI, no visual change |
| TASK-0224 `useChat`, components, theming | 3 | M | 0220, 0223 | public components, scoped CSS, `sdk-react-v*` publish |
| TASK-0225 widget JS API | 3 | M | 0218, 0223 | `window.Superstep`, events, theming, `identify` |
| TASK-0226 web docs and examples | 3 | S | 0224, 0225 | handbook pages, e2e pages |
| TASK-0227 `@superstep/react-native` | deferred | L | 0220 | RN components, Expo example, `sdk-rn-v*` publish |
| TASK-0228 native WebView guide and bridge | deferred | M | 0225 | bridge protocol, Swift and Kotlin guide, browser e2e |
| TASK-0229 edit message | 0.11.0 priority | L | 0216 | DEC-0084 Accepted; shared branch foundation + edit merged (#292, 42333ffc) |
| TASK-0230 regenerate answer | 0.11.0 priority | M | 0229 | DEC-0084 Accepted; regeneration merged (#293, d2119965) |

Critical path: 0215, 0216, 0217 (parallel with 0216), 0218, 0220, 0224 or 0227. TASK-0223 can run in parallel with 0217 and 0218.

## Shared rules

- Planning first: no task moves to todo before the owner accepts the DECs (or amends them).
- Every API error uses the common envelope; new codes in CATALOG, `docs/api-errors.md`, en and vi.
- The v1 contract is additive only once TASK-0219 ships (DEC-0078 compatibility policy).
- Secrets are never in URLs, logs, fixtures or screenshots.
- Publishing: tags `sdk-ts-v*`, `sdk-py-v*`, `sdk-react-v*`, `sdk-rn-v*` through `sdk-publish.yml` (environment `npm` or `pypi`); tags are created only on the owner's release approval.

## Verification strategy

- Backend: pytest on SQLite and Postgres; security tests for every token failure mode and for cross-user isolation; contract tests of the socket schema.
- SDKs: unit tests with recorded v1 frames in Node, jsdom and a no-DOM environment; shared token test vectors between Node, Python and the backend; the existing `sdk-integration` job extended to chat.
- E2E: `examples/chat-host` served on a second origin in CI (Playwright): headless page, React page, widget page, two users, Human form answer, attachment, rating, key revocation.
- UI: screenshots in 4 variants (light, dark, en, vi) for settings and toolkit; the extraction task compares screenshots before and after.
- Mobile: RN unit tests in CI; a manual iOS simulator and Android emulator checklist with screenshots.
- `factory verify run --profile full` and `factory validate` on each task PR.

## Open questions (resolved)

All 11 were approved as recommended by the owner on 2026-10-31 (PR #271); see REQ-0082 "Clarifications".

1. App key JWT (HS256) as the MVP, asymmetric keys later (DEC-0077)? Recommended: yes.
2. Also ship a token-exchange endpoint now? Recommended: no.
3. Default token lifetime 10 minutes, maximum 1 hour? Recommended: yes.
4. Empty allowed-origin list means any origin (for native apps)? Recommended: yes, with a UI warning.
5. `meta` user attributes in the MVP (1 KB, untrusted)? Recommended: yes.
6. Rename `node_token` to `token` in v1 and keep one message per socket? Recommended: yes and yes.
7. No SSE transport for now? Recommended: yes, revisit on demand.
8. Headless chat inside `@superstep/sdk` (`/chat` subpath) rather than a new package? Recommended: inside.
9. Move the repository to npm workspaces so the studio consumes `@superstep/react`? Recommended: yes.
10. Separate `@superstep/react-native` package, no device e2e in CI for now? Recommended: yes.
11. Release grouping: ship phases 1 and 2 as 0.11.0, phases 3 and 4 as 0.12.0? Recommended: yes.

## Deferred / later

Work the owner asked to keep on record (2026-10-31, "Nhớ note các thứ sẽ làm sau lại nhé"). Each item has a reason and a trigger that brings it back.

| Item | Reason deferred | Trigger to pick it up |
|---|---|---|
| Asymmetric (public/private key pair) token signing, e.g. ES256 or RS256 with a registered public key or JWKS URL | HS256 app keys cover the MVP with less setup (decision 1, DEC-0077) | A third party cannot share a symmetric secret with its signing service, or asks for JWKS or key rotation without secret exchange |
| Superstep-issued token endpoint (token exchange: app key in, user token out) | Third parties can sign locally with no network call (decision 2, DEC-0077) | A third party without a signing library asks for it, or a hosted SDK flow needs it |
| SSE transport for chat streaming | WebSocket works in browsers, Node and React Native (decision 7, DEC-0078) | A real client cannot use WebSocket (proxy or platform limit) |
| Native Swift and Kotlin SDKs | React Native and the WebView guide cover mobile for now (REQ-0082 clarification 2, DEC-0080) | Demand from native-only apps that the WebView bridge cannot serve |
| Device e2e for React Native in CI | Simulators in CI are slow and flaky; manual simulator screenshots instead (decision 10, DEC-0080) | Repeated RN regressions not caught by unit tests, or a stable hosted device farm is available |
| Edit a sent message (TASK-0229, backlog) | Needs a conversation fork model; a DEC comes first | Owner request after phase 2; write the DEC before moving the task to todo |
| Regenerate an answer (TASK-0230, backlog) | Needs a rule for replacing turns and run history; a DEC comes first | Owner request after phase 2; write the DEC before moving the task to todo |
| Investigate why the first progress write of a queue job took about 12.6 s on CI (seen in TASK-0212) | Cause not proven: SQLite write lock or thread pool start-up | The delay shows up again in CI or in a user report; profile lock waits and the executor first |
| Unit test for a chunked upload over about 51 MB on a `File(...)` route | Left out of TASK-0208 | Next change to upload handling or the request size limit |

## TASK-0220 owner acceptance (2026-11-02)

Owner approved the reviewed phase-2 stack. TASK-0220 moves to done for single-commit Ready delivery on #285, including the already-reviewed browser fetch binding correction from TASK-0222. This is acceptance of the implementation, not merge or release approval. Dependent PRs are finalised in stack order.

## Phase 3 extraction progress (2026-11-02)

Owner accepted TASK-0223 and requested merging existing #288 on 2026-11-02. Task is done for single-commit Ready delivery, with final-head checks required before merge. Previous validation includes full Factory 8/8, root tests, unchanged chat e2e, clean workspace install, four screenshot variants and a +0.03174 percent bundle comparison. REV/QA-0218 record source review, resolved Deno/runtime setup failures, host i18next/icon compatibility, residual raster differences and no screenshots in Git. TASK-0225–0228 remain backlog; TASK-0224 implementation is authorised on 2026-11-02 and moves through review on its own PR; the new package is not published and release approval remains separate.


## TASK-0224 Draft Delivery (2026-11-02)

Public React toolkit is in review on its own branch/PR. Hook/shared components, scoped CSS, per-instance theme/locales, standalone Vite example and React 18/19 browser matrix are implemented. REV-0219 / QA-0219 record passing source/acceptance checks, the resolved first-run timing failure, package contents and release-only provenance preparation. No Ready/merge/tag/package release is approved. TASK-0225–0228 remain later work.


## TASK-0224 Owner Acceptance (2026-11-03)

Owner accepted the implementation on existing PR #289 ("Duyệt") after reviewed head b0c21ab6 passed 21 CI checks and one expected GHCR skip. TASK-0224 moves to done for rebased single-commit Ready delivery on that same PR. REV-0219 / QA-0219 retain source review, resolved bootstrap/quota/timing failures and acceptance evidence. Final rewritten-head checks are required. This approval does not authorise merge, release tags, npm publication or deployment; TASK-0225–0228 remain later work.


## Web toolkit documentation progress (2026-11-03)

Owner approved and merged TASK-0224 #289 and TASK-0225 #290; #290 integrated as 2ea51b0a after 21 successful checks. TASK-0226 starts from that integration base and is now in review with bilingual React/widget guides and all three shared-host examples. REV-0221 / QA-0221 record strict handbook, React 18/19 matrix and full Factory validation, including the resolved local retry evidence. No images are added to Git. TASK-0227/0228 remain backlog; the full REQ-0082 is still incomplete and package publication/version changes remain separate approvals.


## TASK-0226 Owner Acceptance (2026-11-03)

Owner accepted PR #291 ("Duyệt") after head 5d2d8471 passed 22 checks with the expected handbook-deployment and GHCR skips. TASK-0226 moves to done for a rebased, one-commit Ready delivery on the same PR. REV-0221 / QA-0221 preserve the source review, validation/retry history and screenshots outside Git. Final-head checks are required. Phase 3 is not yet claimed integrated until this PR merges; native TASK-0227/0228 and the overall REQ-0082 remain incomplete. No merge or release approval is inferred.

- Final-head CI follow-up: a pre-existing public-chat rate-limit test used a temporary service instead of the route dependency. TASK-0226 carries a minimal dependency-override test correction and repeated validation on #291; product scope and native backlog remain unchanged. See REV/QA-0221.


## Owner Priority And 0.11.0 Amendment (2026-11-03)

The owner requested temporarily deferring TASK-0227/0228 and focusing TASK-0229/0230 for version 0.11.0. This supersedes the earlier phase grouping: include already integrated phases 1–3 and the two approved chat revision features; exclude native delivery. TASK-0226 #291 is merged at 02361fbd after 22 successful checks and two expected deploy/publication skips.

DEC-0084-chat-edit-regenerate.md is Proposed, with concrete semantics, risks and an acceptance matrix. The existing planning-first rule still applies: owner acceptance of this new decision comes before moving the implementation tasks to todo. TASK-0229 delivers a single shared branch/admission foundation and editing on its own PR; TASK-0230 follows its merged foundation on a separate PR. Current priority is authorised, while these newly proposed execution/UI semantics remain pending acceptance.

Release preparation follows integration of both features: reconcile changelog/docs and additive schemas, verify migrations and compatibility, bump the shared server/Python SDK/CLI version to 0.11.0 with install/runtime pins, validate package contents and full CI, then present the release result. Preserve the independent TypeScript/React version scheme. No tag/publication/deploy is performed by this planning change, and overall REQ-0082 remains incomplete while native work is deferred.


## DEC-0084 Accepted (2026-11-03)

The owner accepted PR #292 ("Duyệt") and authorised implementing the proposed edit/regenerate semantics. DEC-0084 is Accepted; this supersedes its earlier pending-architecture statements. Start TASK-0229 on its existing branch/PR from develop 02361fbd; TASK-0230 follows its shared foundation separately. Native tasks remain deferred. No merge/release instruction is inferred.

## Revision Delivery Progress (2026-11-03)

Owner approved #292 merge and continuing TASK-0230. TASK-0229 merged at 42333ffc after single-commit head 85f8e21e passed all 22 checks and two expected skips. TASK-0230 builds on that integration; REV-0223/QA-0223 track its shared API/SDK/UI and file/admission acceptance. Final full verification/CI and separate owner acceptance remain required before its merge, then 0.11.0 preparation.

- Owner accepted TASK-0230 implementation and explicitly instructed merging #293 (2026-11-03). Reviewed 922ea6a8 passes 22 checks/two expected skips. Final lifecycle-only commit must also pass CI before integration; then proceed to approved shared 0.11.0 preparation.

## 0.11.0 Preparation (TASK-0238, 2026-11-03)

Both revision tasks are integrated: #292 at 42333ffc and #293 at d2119965, each after 22 final checks/two expected skips and explicit owner merge instruction. TASK-0238 prepares shared server/Python SDK/CLI/frontend/install version 0.11.0, consolidated release notes and packaged/migration validation; TypeScript 0.2.0 and React 0.1.0 remain independent. Local full profile, artifact installs/imports, backup/restore and en/vi handbook pass (REV/QA-0224); exact PR-head CI and owner acceptance gate integration. Release/main merge, tag and registry publication still require explicit instruction on the concrete candidate. Native is deferred and REQ-0082 remains incomplete.

## Owner 0.11.0 Release Instruction

After reviewing candidate #294 and its feature summary, the owner explicitly instructed “Phát hành đi”. This accepts TASK-0238 and authorises #294 integration, develop-to-main release merge, v0.11.0 and independent SDK tags, GitHub Release and configured registry publication. Reviewed e8b21129 has 22 successful checks/two expected skips; local full 8/8, artifact/migration/handbook checks pass. Final lifecycle-only head must pass exact-head CI before merging; publication outcomes are checked separately. This supersedes pending-owner/release statements for this candidate, while native TASK-0227/0228 and overall REQ-0082 remain incomplete.
