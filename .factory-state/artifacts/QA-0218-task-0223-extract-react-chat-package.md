# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0218
- Task ID: TASK-0223
- QA Owner: Codex, advisory; owner accepted 2026-11-02
- Created/Updated: 2026-11-02
- Outcome: pass; owner accepted 2026-11-02
- References: REQ-0082, PLAN-0002, DEC-0079, REV-0218

## Acceptance Criteria Coverage

| Criterion | Result / evidence |
| --- | --- |
| Existing chat e2e en/vi pass unchanged | 16 passed (1.6m): public-chat, chat-embed, chat-attachments, chat-user-tokens, agent-chat and chat-app-keys. No existing e2e file changed. Isolated backend/UI/mock/SMTP ports 8250/5250/8251/8252 and system Chrome. Log: /private/tmp/superstep-0223-e2e.log. |
| Four light/dark en/vi screenshots match | Same persisted synthetic sessions, 1280x900 Chrome. Both dark frames pixel-identical; each light frame has 19 differing pixels confined to avatar corners (0.00165% of the frame), with no text/layout difference on visual review. Before/after images and comparison.json: /private/tmp/superstep-0223-visual/. No images are committed. |
| Frontend bundle grows at most 5% | JS/CSS assets: 3711598 baseline bytes, 3712776 final-build bytes, +0.03174%. Includes the complete built asset set; widget output remains separate and unchanged. Logs: /private/tmp/superstep-0223-baseline-build.log and superstep-0223-icons-build.log. |

## Checks Performed

- Root workspace build/lint/unit tests passed; frontend initially 151 then 152 after the icon compatibility regression, React package initially 3 then 4 after the host-i18next regression, TypeScript SDK 94. Existing en/vi parity and markdown/file tests remain unchanged.
- Fresh checkout npm ci, npm ls --depth=0, build/lint/tests passed; checkout /private/tmp/superstep-0223-clean. Final source was switched into that checkout and build/tests rerun successfully with 4 React tests. The package's built ESM exports rendered outside Studio; pack dry-run has 73 files, 30239 compressed bytes, no frontend/test/node_modules/screenshots.
- That clean checkout also passed the full sample-host script: 3 Node security/locales/static tests and 1 actual Chrome two-origin scenario (2.7 s test / 3.6 s total), including files/form/rating, identity isolation, origin refusal and revoke. Log: /private/tmp/superstep-0223-clean-host.log.
- Factory upstream workspace fix: 146 tests passed (16.659 s), upstream main ce00ad0 pushed before byte-identical service/test vendoring. Factory deps apply passes with one locked npm-root install; tools assets synced. No external dependency version pair differs from the two previous locks.
- Local architecture correction: Factory runs under x64 Python, while the prepared Node wrapper forces arm64. Dependency installation and verification now use that same PATH. The independent clean arm64 checkout also passed build/tests; no lock/dependency version change was needed.
- First full Factory profile on a10265a9 failed 5/8 checks: four Node checks used native modules for a different architecture, and the backend had 1170 passed / 18 skipped / 30 setup errors from one Deno probe resolving through the new npm workspace. This is not a passing verification claim. Installation now uses the same arm64 Node wrapper as verification; Deno check/run use no-config/no-lock/node-modules-dir=none and keep their isolated cache. The complete TypeScript export regression passes 39 tests (32.40 s), with all original assertions retained. Corrected root build/lint/unit tests passed. The full-profile rerun on committed 77740f18 then passed all eight checks; the final icon compatibility patch was additionally followed by the complete root build/lint/test suite (frontend 152, React 4, SDK 94).

## UX And Accessibility Coverage

Original shadcn markup, labels, keyboard submit/stop, status/log regions, theme tokens and localisation are retained. Existing tests cover visitor/builder history, Human answers, files, rating, embed/widget and signed-in/app-key flows. Standalone SSR additionally covers no-router rendering, markdown sanitisation, host-owned reviewer navigation and coded errors using the host's i18next context. No new user-facing strings or resource-deletion UI.

## Gaps, Residual Risk And Handoff

No public package/tag, deployment, real provider/customer data, mobile device or React 18 matrix test. Scoped CSS/theme/public hook/widget APIs are later tasks. Two light-mode images have the explicitly measured small avatar-corner raster difference; images are available for owner review. Pre-existing lint/chunk/dependency audit warnings remain. Owner review and final CI are separate from local advisory QA; this task stops at one Draft PR until accepted.

## Final Verification

Full Factory rerun: eight passed (frontend/workspace build 8.88 s, lint 1.13 s, tests 9.19 s; backend 484.14 s; Python SDK 13.85 s; TypeScript build/test/typecheck 1.56/1.69/1.49 s). Canonical latest.yaml records passing outcomes. This supersedes the initial failed run without removing its diagnosis above. Final icon compatibility overlay passed full workspace build/lint/tests separately; exact-head CI remains attached to the Draft PR.

Factory validation, all-ref artifact uniqueness (91 refs), generated provider asset sync and whitespace gates pass. Final package dry-run: 73 files / 30239 compressed bytes. No image, auth state or native module is tracked; baseline fixture servers were stopped after review. Advisory local QA passes for owner review, without authorising Ready/merge/release.

## Owner Approval And Merge Finalisation

On 2026-11-02 the owner accepted the reviewed delivery and explicitly requested merging #288 ("Ok merge"). TASK-0223 moves to done on that same PR and is squashed to one commit. Finalisation preserves the reviewed implementation tree; only lifecycle/review/QA/plan records change. Original head 46e001a6 passed 20 CI checks (one expected GHCR skip), including full Factory, all Playwright shards, Docker and the host gate. Rewritten-head checks must pass before Ready/merge. This supersedes earlier pending-acceptance/merge statements; no package or tag publication is approved.
