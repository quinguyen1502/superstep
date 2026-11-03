# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0219
- Task ID: TASK-0224
- QA Owner: Codex (local advisory QA)
- Created: 2026-11-02
- Updated: 2026-11-03
- Outcome: pass; owner accepted for Ready finalisation

## Acceptance Criteria Coverage

| Criterion | Result / evidence |
| --- | --- |
| Public useChat and components | Testing Library + CSS/SSR suite: 17 tests pass. StrictMode, identity/socket cleanup, session restore/switch, loading submission state, Human fields/live replies, file cancellation/exact-name deletion, feedback deletion and stale dialog closure. Public Rating accepts controller turns in the Vite TypeScript contract probe. |
| Standalone Vite example / theme | Built package/declaration exports and prebuilt CSS, with no Tailwind plugin or Studio component alias. Composed and all-in-one layouts; per-instance en/vi/messages and light/dark/custom font/colour/radius. |
| CSS leaves host outside root unchanged | Parsed CSS boundary tests cover every outer selector, properties/keyframes and absence of host cascade layers. Chrome compares host font/size/padding/border/radius before/after chat activity. Ambient host dark data attribute cannot change the light provider. |
| Real-browser flow | scripts/chat_host_e2e.sh passes on React 18.3.1 and React 19: built toolkit plus original headless scenario. Human approval, uploaded/authenticated downloaded file, ratings/name confirmation, two-user isolation, language/theme independence, scoped history portal and aligned toolbars; no React page/console errors. Existing headless scenario retains origin/revocation/security coverage. |
| Publishing preparation | sdk-react-v* job only, version guard tested: 0.1.0 accepted / 0.1.1 rejected. npm environment, id-token permission, provenance, public repository metadata and pack dry-run. No actual tag/publication. |

## Checks Performed

- Full Factory profile on clean implementation 3e6e8f69: all eight declared checks pass; see .factory-state/verification/latest.yaml and /private/tmp/superstep-0224-factory-final.log. Backend, root build/lint/tests, Python SDK and TypeScript SDK build/test/typecheck are included.
- Initial checkpoint ed434764 passed 7/8 gates: 1199 backend tests passed / 18 skipped, with one unchanged Human-pause timing assertion taking 0.347 s against <0.2 s. Isolated rerun passes in /private/tmp/superstep-0224-human-timing.log, then the complete profile passes without changing backend or assertion. The initial failure is not presented as a passing run; cause of the delay is not proven.
- Repository metadata was finalised after full source verification. Factory dependency state was refreshed, and canonical root build/lint/tests plus pack dry-run were repeated for that metadata-only delta. Runtime/source/dependency versions are unchanged by this finalisation.
- React browser logs: /private/tmp/superstep-0224-browser.log and /private/tmp/superstep-0224-react18.log. Original headless sample: three Node security/localisation/static-serving tests plus its Chrome scenario pass on each matrix run.
- UI checklist: required colour/hex scans return no hits, strict shadcn class guard passes, en/vi keys and translation review pass, shared confirmation and toolbar alignment checked. No backend/schema/Python package change.
- Studio built asset bytes 3715564 vs extraction baseline 3712776: about +0.08 percent, well below the DEC-0079 revisit threshold. Screenshots are visually inspected for layout/readability and independent scopes; no pixel-identical claim.

## Evidence And Package Contents

Screenshots light/dark/custom: /private/tmp/superstep-0224-visual/. Browser output is ignored under frontend/test-results/react-chat/ and CI uploads it for 14 days with auth traces disabled. No image/archive/auth state is tracked. npm pack dry-run: 98 files, 87321 compressed bytes / 432623 unpacked bytes; contains dist/declarations/styles, README, license and package metadata; no frontend source, tests, screenshots, node_modules or fixture credentials.

## UX And Accessibility Coverage

Labelled composer/Human controls, disabled loading/busy states, keyboard submit/escape, shared Radix focus/dialog behaviour and exact-name confirmations are exercised by DOM/browser tests. Both languages and light/dark/custom themes are visually inspected. This is not a manual screen-reader audit.

## Gaps, Residual Risk And Assumptions

No real model/customer service, actual npm release, production deployment or mobile/device browser test. Host CSS inheritance and restored Human metadata limitations are documented in the package README. React 18 is an isolated temporary/CI fixture; the app stays on React 19, Python stays on shared 0.10.2. External release credentials/scope ownership and release approval remain a maintainer gate. Pre-existing/following-pattern lint warnings are non-fatal. Final PR checks are authoritative for the pushed head and are reported on that PR; local QA does not substitute for human review.

## QA Decision

Advisory local QA passes for Draft owner review. Keep TASK-0224 in review. Ready/done/merge and package publication require the owner's separate approval and applicable passing CI.


## Fresh-Checkout Bootstrap Follow-Up (2026-11-03)

The first pushed head passed Factory/backend/SDK/Docker and React-host checks, but its general e2e startup bypassed the package build. A fresh npm ci checkout reproduces a Vite overlay: provider.tsx cannot resolve messages.generated.js (and SDK build outputs are also absent). Existing local dist files had masked this gap. The old main CI run is cancelled while the fix is prepared.

Frontend predev now owns SDK/toolkit build and asset generation; root dev, dev.sh and the Playwright web-server use that same lifecycle. No duplicate root predev or direct-Vite bootstrap remains. Cold-start browser probe changes from overlay=true/email=false to overlay=false/email=true with no page errors, starting from absent SDK/toolkit dist and generated locale files. Logs: /private/tmp/superstep-0224-bootstrap-before.log and superstep-0224-bootstrap-after.log. Dependency versions are unchanged; Factory source fingerprints are refreshed. Canonical root build/lint/tests pass on the clean bootstrap-fix commit; the 16 targeted chat regressions also pass from absent build/generated outputs (1.6m); exact-head CI remains the delivery gate.

The first cold-start 16-case run was 14/16: a shared-IP read budget returned HTTP 429 during the English daily-cap case, and the app-key case attempted scrolling while the settings dialog was unstable. UI fixture now disables only STUDIO_PUBLIC_CHAT_RATE_READ; backend test_page_loads_are_limited_per_ip still passes with its explicit threshold, production defaults and daily-cap assertions are unchanged. The app-key test waits for settled motion and asserts the dialog remains visible before scrolling, preserving every key/secret/revocation/alignment assertion. Both failing cases passed twice (4/4), then all 16 chat regressions passed together. Logs: /private/tmp/superstep-0224-bootstrap-root.log, superstep-0224-bootstrap-retry-final.log, superstep-0224-bootstrap-chat-final.log and superstep-0224-read-rate-security.log. No screenshot/trace/auth material is added to Git. Updated-head CI is required before acceptance.


## Owner Acceptance And Ready Finalisation (2026-11-03)

The owner accepted the implementation ("Duyệt") after PR #289 head b0c21ab65da49d28e120c57fb13b2d28b19614c7 completed 21 successful CI checks and one expected GHCR publication skip. This includes the full Factory profile, both backend databases, all three general Playwright shards, React 18/19 host acceptance, SDKs and image/security smoke checks. Earlier setup/timing failures remain documented above and are resolved by the recorded corrections/reruns.

TASK-0224 moves to done on the same PR for a rebased, single-commit Ready delivery. This supersedes the earlier pending-human-acceptance/Draft-only statements; the implementation tree is preserved. Required validation and CI remain gates on the rewritten head and their actual final results are reported on #289. No merge, release tag, npm publication or deployment is approved.
