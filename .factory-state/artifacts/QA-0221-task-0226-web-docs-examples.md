# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0221
- Task ID: TASK-0226
- QA Owner: Codex (advisory local QA)
- Created: 2026-11-03
- Updated: 2026-11-03
- Outcome: pass; owner accepted for Ready finalisation

## Validation Scope

REQ-0082 / PLAN-0002 / TASK-0226, accepted DEC-0077/0079 and REV-0221. Bilingual React/widget handbook, shared sample host pages, server-only token flow, built iframe fixture, browser compatibility matrix, source/locale/UI checks. Merge prerequisite #290 is integrated as 2ea51b0a; #289 was already merged. No production backend/SDK transport/schema/version change.

## Acceptance Criteria Coverage

| Criterion | Result and evidence |
| --- | --- |
| Handbook build passes | Pass. Four new en/vi pages, nav/cross-links and corrections to older auth/public-API guides. `.venv/bin/zensical build`, `.venv/bin/zensical build -f mkdocs.vi.yml`, `.venv/bin/python check_images.py site` from handbook all pass; final logs /private/tmp/superstep-0226-handbook-{en,vi,images}.log. Markdown page trees match. |
| E2e job covers React and widget pages | Pass locally with the exact CI entrypoint `scripts/chat_host_e2e.sh`, React 19 and isolated React 18. Each run passes three Node security/static tests plus all three browser scenarios: toolkit, widget and headless. CI matrix invokes this script and uploads the widget artifact directory alongside existing outputs. Exact pushed-head results remain the PR gate. |

## Functional, UX And Security Coverage

- One host serves `/`, `/react/` and `/widget.html` with navigation and shared server-owned HttpOnly demo session. React relative assets, widget HTML and encoded traversal refusals are checked by Node tests. No credential data is injected into built static bundles.
- Built Studio is served by the isolated backend. The parent embed allowlist and app-key Studio/host origins are explicit, without changing backend policy. The SDK seed's widget behavior is opt-in; other SDK fixtures retain their existing origin behavior.
- React toolkit scenario covers theme/language isolation, CSS host sentinel, streaming, Human answers, upload/download, typed-name file/rating deletion, history controls and identity changes on React 18/19.
- Widget scenario covers guest chat, two app personas, restoration of guest/app history, Human approval, persisted-turn events, no JWT/secret storage and cross-page login/history reuse. It uses the actual authenticated Node token endpoint and built widget/iframe, not route mocks or a new browser signer. Trailing-slash Studio URLs are exercised by the fixture.
- Headless scenario still covers structured Human answers, files/ratings, two-user and cross-context isolation, forbidden HTTP/socket origins and terminal key revocation with no further turns written. Revocation runs last; no host restart is required.
- New controls use shared shadcn components/tokens and canonical en/vi strings. Header controls use one size; browser alignment assertions pass in en/light and vi/dark. Host language attributes and iframe locale are set. Dark screenshot capture waits for the provider scheme and controls to inherit the page foreground. Required colour scans and the strict UI class guard have no hits. No new delete feature or catalogue code.
- Automatic auth traces are off. Screenshot content is synthetic chat UI. Credential/storage assertions use booleans to avoid printing secret/token values on failure. Real customer/provider credentials are not used.

## Checks Performed

- Full declared Factory profile passes all eight commands on source a868961e: root build 11.49s, root lint 1.17s, root tests 18.64s, backend pytest 490.35s, Python SDK pytest 14.41s, TypeScript SDK build/test/typecheck 1.58/1.21/1.51s. Command: PATH with existing backend venv, ARM Node wrapper and cached Deno runtime, STUDIO_TS_EXPORT_DENO_DIR set, `.factory/bin/factory verify run --profile full`. Log: /private/tmp/superstep-0226-verify-final.log; canonical `.factory-state/verification/latest.yaml` is passed.
- Final refinements after that full run are confined to sample URL/language/alignment, equivalent secret-safe test assertions, READMEs and lifecycle artifacts. Backend/SDK implementation remains unchanged. Both sample matrices rebuild/typecheck the exact bundles, pass all Node/browser scenarios, then root lint/tests repeat successfully. Logs: /private/tmp/superstep-0226-host-final.log, superstep-0226-host-react18-final.log, superstep-0226-root-final.log. Root suites: frontend 157, React 18 and TypeScript SDK 94 tests pass.
- Factory validate, dependency/verification validation, artifact-ID uniqueness and git diff --check are final handoff checks. No tags, publication, deployment or merge of this new task is implied.

## Initial Failures And Resolution

The first full profile passed seven commands but backend pytest was 1199 passed / 2 failed / 18 skipped: test_api_import_finalize_ws could not finish creating its venv, and test_api_upload_search_and_run returned BAD_REQUEST rather than KB_FILE_TOO_LARGE. First isolated rerun was 1 pass/1 fail. Disk headroom had dropped below 200 MB. Only known completed test-import caches from this session and ignored handbook build output were removed; product source and assertions were not changed for these failures. Both cases then pass together (27.04s), followed by the entire profile passing. The import log did not directly confirm ENOSPC, so the precise cause is not claimed proven. Logs: /private/tmp/superstep-0226-verify.log, superstep-0226-backend-retry.log, superstep-0226-backend-retry-clean.log and superstep-0226-verify-final.log.

The initial widget fixture expected one user message event after a Human approval. The existing API persists both the original message and the Human answer as user turns; the fixture now expects both. No product behavior was changed to satisfy the test. A first dark screenshot was captured during the iframe's theme transition; the final color/scheme wait and animation-disabled capture pass in both matrices.

## Evidence

Visually inspected screenshots: /private/tmp/superstep-0226-visual/widget-host-en-light.png, widget-host-vi-dark.png, react-light.png and react-dark.png. Browser outputs under ignored frontend/test-results are uploaded by CI for 14 days. No screenshot/archive/auth state is committed. Handbook output is regenerable and ignored; final successful build/media logs are retained outside Git.

## Gaps, Residual Risk And Assumptions

Chrome on the local machine plus CI React 18/19 is the browser scope; no Safari/Firefox, device WebView, real model service or production deployment claim. The host's two personas remain an explicit loopback demo. Operators must replace authentication, use approved compatible packages, configure separate parent/iframe origins and keep signing secrets server-side. Versions remain unchanged, including shared Python/CLI/server 0.10.2. The entire REQ-0082 and native TASK-0227/0228 remain incomplete.

## QA Decision

Advisory local QA passes for Draft owner review. Keep TASK-0226 in review; human acceptance and applicable final-head CI are required before done/Ready/merge. No unresolved blocking source defect remains.


## Final Screenshot And Documentation Follow-Up

The React example's own capture helper now waits for inherited foreground colors and disables screenshot animations, matching the widget capture guard. Both complete React 18/19 sample matrices pass again with this stronger color check; this is a test-only change. SDK package READMEs also link the new bilingual web UI guides. Root lint and repository checks remain passing. Product behavior, dependency versions and the fully verified backend are unchanged; final pushed-head CI is recorded on #291.


## Owner Acceptance And Ready Finalisation (2026-11-03)

The owner accepted PR #291 ("Duyệt") after reviewed head 5d2d847131051ce951a3bcaf9267160036dcd07a completed 22 successful CI checks and two expected deployment/publication skips. This includes strict en/vi handbook, both React host matrices, all Playwright shards, SQLite/Postgres backends, Factory, SDK/CLI and image/security checks. This supersedes the earlier pending-owner-acceptance/Draft-only statements.

TASK-0226 moves to done on the same PR for rebased single-commit Ready delivery. Develop remains 2ea51b0a. Product implementation, documentation and dependency versions are preserved. A minimal test-isolation correction discovered during final-head CI is recorded below. Required final validation is repeated, and exact-head CI outcomes are reported on #291. Merge, release tags and publication still require explicit instructions. REQ-0082/native work is not marked complete.


## Final-Head Rate-Limit Test Correction (2026-11-03)

Factory run 41575291204 on f8b4c7cc failed test_page_loads_are_limited_per_ip (1152 passed, 1 failed, 66 skipped); the other 21 PR checks passed. The test patched the limiter of a temporary PublicChatService, but the route constructs another service and retains its shared limiter. Earlier requests can therefore consume the test's quota. This is a test-isolation defect, not a runtime regression.

Reproduction preloads five hits on pubchat-read:testclient in the shared 3600-second window before invoking the unchanged test: it fails with initial HTTP 429 responses. The correction registers the isolated service through FastAPI's existing dependency_overrides using monkeypatch.setitem, so teardown restores the original dependency. With identical preloaded shared state, all nine tests in test_public_chat_api.py pass (2.92s). The original 200/429 expectations and all production code remain unchanged. Logs: /private/tmp/superstep-0226-rate-before.log and superstep-0226-rate-after.log. Full-profile verification repeats in superstep-0226-rate-full.log; final CI results are recorded on #291.

PR #291 temporarily returns to Draft while resolving this final CI finding; the same task/branch will carry the correction and restored done/Ready state after validation. No new task, feature, merge or release is introduced.

Final local validation after the test correction passes all eight Factory commands: build 12.16s, lint 1.20s, root tests 16.98s, backend 484.46s, Python SDK 14.16s, TypeScript SDK build/test/typecheck 1.58/1.34/1.52s. Log: /private/tmp/superstep-0226-rate-full-authorized.log. An initial sandboxed attempt could not bind test HTTP servers; the authorized rerun passes without product or assertion changes. TASK-0226 returns to done on the same approved PR; the correction is included in its single task commit, and exact-head CI is required before restoring Ready.
