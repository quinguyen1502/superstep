# Review

## Metadata

- Project: superstep
- Review ID: REV-0221
- Task ID: TASK-0226
- Reviewer: Codex (advisory; owner approval remains separate)
- Created: 2026-11-03
- Updated: 2026-11-03
- Outcome: owner accepted; approved for Ready finalisation

## Review Scope

Branch diff from merged develop 2ea51b0a: four bilingual React/widget handbook pages, navigation/cross-links, package/example READMEs and Unreleased changelog; shared sample host static routes and widget portal; built Studio fixture, opt-in seed settings, browser acceptance and CI screenshot-artifact path. Existing React consumer is reused rather than duplicated. No production backend/SDK implementation, schema, package version, release or framework asset change.

## Reference Artifacts

TASK-0226, REQ-0082, PLAN-0002, accepted DEC-0077/0079; docs/ui-conventions.md; TASK-0224/0225 and their merged public API contracts. Task dependencies #289 and #290 are integrated. Owner instruction authorizes merging #290 and proceeding with this next task, not merging the new task PR.

## Findings

### Blocking

No unresolved blocking findings. Final local validation and QA evidence is recorded in QA-0221; owner acceptance remains pending.

The sample now serves headless `/`, React `/react/` and `/widget.html` using the same opaque HttpOnly session and protected server signer. New static route selection keeps path containment/no-store; encoded traversal and relative React assets are tested. CSP admits only self/configured Studio resources and retains frame-ancestors none for the host. No new token endpoint, browser key secret, caller-selected identity or credential-bearing URL is introduced.

The isolated fixture serves the actual built Studio and pins both parent embed admission and Studio/host app-key origins. Optional seed settings leave ordinary SDK integration behavior unchanged. React and widget acceptance run before the terminal headless key-revocation case, avoiding order-dependent revoked credentials. Both React compatibility configurations exercise all three pages without restarting the server.

### Non-Blocking

- The widget sample reuses the portal's React/shadcn shell for host controls; the shipped widget remains plain JS and has no React dependency. The handbook gives the plain-HTML integration separately.
- The fixed Lan/Minh login is explicitly a loopback demo, not deployable application authentication. Guides require deriving identity server-side, bounded JWTs, protected/no-store token responses and correct origin setup.
- Browser screenshots are Chrome and synthetic mock-provider output. Real services, Safari/Firefox, device WebViews and publication remain outside scope. Native work remains TASK-0227/0228.

## Standards And Architecture Alignment

One SDK/widget transport and one signer/session server are reused. New controls use shadcn/theme tokens; new labels are canonical en/vi dictionary keys. No hard-coded product colours, new catalogue errors, delete feature or data model. Typed-name file/rating confirmation stays with shared existing components. Temporary screenshots and fixtures are ignored/outside Git; CI uploads no auth traces. Backend layers and API policies are not changed.

## Design Alignment

Navigation makes all three examples discoverable. Existing host controls keep equal size variants. Widget open/close, visible ready state and event counts demonstrate the API; the guest/app switch exercises the same iframe UI. Guides cover identityKey, token refresh, unmount/logout, history selection, Human/file/rating behavior, theme/locales, widget queue/events and distinct parent/Studio origin rules. Package/version/publication status is stated without implying a release.

## Validation Review

Final strict en/vi handbook builds and media checks pass, including corrections to older auth/public-API pages that still described identify/toolkit as future work. Both sample matrices pass three Node security/static tests and React/widget/headless browser scenarios. An initial widget assertion counted only the original message; Human answers persist another user turn, so fixture expectations now follow the existing documented event contract. Final screenshot capture also waits for iframe dark theme/foreground before using Playwright's animation-disabled capture. The final screenshot guard passes in both matrices. The first full Factory run passed seven commands but failed two backend cases (import venv readiness and oversized Knowledge Base upload). These are unchanged backend tests; after removing completed test import caches both pass in isolation without source/assertion changes. Low disk headroom was observed, but the import log did not directly confirm ENOSPC; no definitive root cause is claimed. The complete profile rerun passes all eight commands, including the unchanged backend suite (490.35s). Final sample-only refinements normalize a trailing-slash Studio URL, set host language attributes and align navigation controls; both browser matrices and root lint/tests pass after these refinements. Details are recorded in QA-0221.

## Assumptions

Operator-provided Studio URL and build directories are trusted configuration. Hosts replace demo authentication before deployment. Python/CLI/server retain shared 0.10.2; existing npm versions and release approval gates are preserved.

## Required Follow-Up

Submit one Draft PR with QA-0221 and report exact-head CI results. Keep TASK-0226 in review until owner acceptance; do not claim all of REQ-0082/mobile complete.

## Review Decision

Approved for QA (advisory). Local QA passes for Draft owner review; owner approval remains pending.


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
