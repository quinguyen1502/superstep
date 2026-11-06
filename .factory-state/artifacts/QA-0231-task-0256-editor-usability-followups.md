# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0231
- Task ID: TASK-0256
- QA Owner: Codex
- Created/Updated: 2026-11-05
- Outcome: pass with follow-up (documented native-device / Redis-version coverage gaps)

## Latest QA And Decision

Owner has now approved merge/release 0.11.2. All 22 executing remote checks on reviewed head 763432b2 passed, including the production-version Postgres 17/Redis 7 backend suite; the prior local Redis-version gap is therefore covered by CI, not by relabelling local RESP2 evidence. All three Playwright shards also pass. Done/merge of this source task remains gated by final squashed-head checks; actual release publication is verified separately.

Final implementation 7c7fc06a, documentation checkpoint 8abb6ac4, re-reviewed in REV-0231. Owner explicitly authorised same-task fixes after the earlier failed validation. No blocking defect remains; the historical failed report below is preserved, not erased.

### Current Acceptance Coverage

- Rounded drag preview: clipped, shadow-free dedicated snapshot inspected; native OS pixels remain a manual follow-up, not a claimed automated pass.
- Time travel: approved both-theme preview; existing inspect/edit/fork regression passes.
- Empty dropdowns / useful General: visible empty state, existing connections and shared keyboard behaviour pass in en/light and vi/dark. Lookup loading/errors are distinct in the inspected MCP/Retriever/Subgraph flows.
- Shared alignment / Restore / attached tabs: approved preview plus all selected alignment, Versions and panel-layout tests pass. No visible tab shadow; keyboard outline asserted. Source uses theme tokens; checklist colour scans find no prohibited colours outside documented logo exclusions.
- Fixed dialog header/footer: new short mobile viewport regression scrolls only DialogBody and asserts unchanged header/footer position plus visible Save; existing panel layout tests pass.
- State quick actions: named/typed explicit creation, duplicate error, immediate selection and Undo pass; read-only guard inspected and existing template viewer regression passes. Saved-chat creation/save disclosure remains preview/source evidence rather than a dedicated automated save-together scenario.
- Studio/public/other-tab realtime: socket observer integration inspected; actual anonymous public browser produces a persisted running row and selected running→completed trace in an already-open Studio with zero navigations. Gated backend socket test asserts run start/node progress before completion. Active duration is nonnegative. Selection/filter/workflow guards inspected.
- Access / cleanup / recovery: auth denial, per-run visibility, revoked-share closure, reconnect resnapshot, memory subscriber cleanup, non-replay orphan handling and separate-process Redis publisher all pass. Queue recovery/layer/envelope regressions pass.

### Current Validation Evidence

- Canonical Factory full: **8/8 passed**, root build/lint/test, backend full, Python SDK test, TS SDK build/test/typecheck. Backend command 447.23s, below unchanged 900s policy. /private/tmp/superstep-0256-fix-factory-final.log; tracked latest.yaml records this green run.
- Independent full backend: **1194 passed / 66 skipped**, 463.23s. /private/tmp/superstep-0256-fix-backend-final.log.
- Current focused backend/service/layers/envelope/chat/recovery: **56 passed / 1 skipped**, 13.23s.
- Local Redis 5.0.5 with protocol=2 URL: **8 passed / 1 skipped**, 4.57s. Includes a separate Python publisher; memory-registry assertion is transport-conditionally skipped.
- Current selected Playwright editor-followups/canvas-menu/alignment/versions/time-travel/template-editor/panel-layout: **22 passed**, 1.8m. Passed public running/completed captures moved to /private/tmp/superstep-0256-final-ui-results, outside Git.
- Runtime cancel/timeout/validation Playwright: **3 passed**, 23.5s. Two handbook capture cases skip without HANDBOOK_SHOTS; no handbook image regeneration was requested. /private/tmp/superstep-0256-fix-e2e-extra-final.log.
- `factory verify validate`, `factory validate`, ID check against origin/develop, `git diff --check`: pass. Existing dependency receipt/no-todo warnings are not bypassed readiness gates; task-start ready originally passed.

### Diagnostic Rounds Retained

The first fix-stage full Factory attempt on superseded 181f0071 passed 7/8 but backend timed out at 900s. Snapshot writes were then limited to chat, preserving editor/ad-hoc behaviour; the final exact-source full runs above pass without a timeout increase. Earlier UI attempts exposed test focus/animation assumptions and one Vite/SDK-build race; these are not counted as passing evidence. The final UI run was serialised apart from npm builds. The separate independent backend and Factory runs use isolated test databases.

### Remaining Risk And Follow-Up

Redis 7 deployment acceptance, native OS drag image and physical phone keyboard remain manual/environment follow-ups. No blanket production resilience claim: display-only socket snapshots do not introduce durable queue replay or a new distributed orphan sweeper. Standard conditional Docker/Deno/Postgres/Redis skips remain visible in the full suite. The original 27 approved previews remain in the external superstep-review-0256 gallery; no screenshots/traces/logs/binaries are committed.

**QA decision:** pass with the documented follow-ups; prepare a Draft for owner review. No merge, Ready/done promotion, version bump, tag, deployment or release is implied by QA. The prior failure history follows.

## Historical QA (Before Owner-Authorised Fixes)

## Validation Scope

Checkpoint ce9c8128, approved two-batch source plus new backend/live-history and UI regression coverage. Review: .factory-state/artifacts/REV-0231-task-0256-editor-usability-followups.md. No implementation fixes during validation/review/QA.

## Acceptance Criteria Coverage

- Rounded native drag ghost: source inspected; native OS pixels not verified. Gap remains.
- Time-travel aligned columns: approved both-theme screenshots; existing time-travel E2E passes in the 21-case run.
- Visible empty dropdowns: preview and the new UI tests reach/past the visible-empty assertion; passed to that point.
- Icon/text alignment: 8 existing alignment cases pass across en/vi light/dark and panel/header widths. Alert previews inspected. No claim that every UI call site was manually exercised.
- Fixed dialog header/footer: approved desktop/mobile screenshots and existing panel-layout coverage. The new automated scrolling checks are not reached because the earlier shadow assertion fails.
- Restore spacing: approved Versions screenshots; Versions E2E passes.
- Shadow-free attached tabs: approved appearance; computed-style assertion incorrectly rejects zero-alpha/zero-size Tailwind layers. Automated criterion not green.
- Useful General: preview plus new E2E connection-name assertions pass before the shadow failure.
- Explicit state creation/selection/Undo/read-only: preview approved; new automated creation/Undo checks not reached. Backend settings schema rules unchanged. Coverage incomplete.
- Public/tab-independent realtime: new public-chat E2E passes with zero Studio navigations, and preview records one document load plus runs_changed frames. However it only checks eventual waiting/completion; static review proves no immediate running-row publication for non-checkpointing socket plans. Fails immediate-start acceptance.
- Subscription access boundary: new denial and revocation backend tests pass; per-run visibility assertions execute, but three normal close/reconnect contexts fail CancelledError on both transports. Not an overall pass.

## UX And Accessibility Coverage

27 approved source previews outside Git in the existing superstep-review-0256 gallery; desktop/mobile and both themes. Existing alignment tests cover en/vi × light/dark. Actual device keyboard/native drag rendering and full keyboard-create/focus regression remain gaps.

## Checks Performed

- Root npm run build: pass (including TypeScript and widget build).
- Root npm run lint: pass; strict UI class check no hits, warnings recorded in /private/tmp/superstep-0256-lint.log.
- Root npm run test: pass, frontend 157 + React 21 + TypeScript SDK 102 = 280.
- Targeted Playwright editor-followups/alignment/versions/time-travel/template-editor/panel-layout: 19 passed, 2 failed in 1.8m. /private/tmp/superstep-0256-e2e.log; traces/screenshots moved to /private/tmp/superstep-0256-e2e-results, never Git.
- Backend tests/test_live_run_history.py (memory): 2 passed, 3 failed in 3.98s. /private/tmp/superstep-0256-memory-history.log.
- Same tests on Redis 5.0.5 with protocol=2 URL: 2 passed, 3 failed in 4.76s. /private/tmp/superstep-0256-redis-history-resp2.log. Initial default-protocol attempt failed HELLO because the installed Redis is too old; retained separately, not presented as a product failure.
- Factory full declared 8-command profile: failed, 3 passed / 5 failed. Full backend: 1188 passed / 65 skipped / 3 failed in 469.46s (472.67s runner). SDK Python, SDK TS build and typecheck pass. Four npm checks fail environment-native bindings under x64 Node (lightningcss/oxlint/rollup), while the same root build/lint/unit commands invoked directly run on arm64 and pass. Probe: direct node process.arch=arm64; node spawned by backend/.venv Python reports x64. Do not claim a green canonical run or repair/reinstall dependencies under this validation-only step. Full log: /private/tmp/superstep-0256-factory-full.log; .factory-state/verification/latest.yaml reflects the failed run.
- Factory validate: pass with warnings about dependency installation receipts and no new todo (active task is already doing). Artifact ID check against origin/develop: unique. No ready gate was bypassed; original task-start ready check passed before implementation.
- git diff --check: pass before writing review/QA records.

## Defects

See blocking findings 1–3 in REV-0231. Do not mark Ready/done or push a validated delivery while these remain.

## Gaps Or Untested Areas

Redis 7 and separate worker/API processes, missed-message/revocation races, slow public run visibility before completion, automated state creation/Undo/dialog scrolling beyond the failing assertion, OS drag image and physical keyboard. The local Redis/RESP2 test is same-process transport evidence only, not multi-process proof. Factory's x64/arm64 runner mismatch must be addressed with a task-local runtime configuration before its next full rerun; do not change committed dependencies to mask the mismatch.

## Residual Risk

Preview acceptance is not equivalent to backend lifecycle correctness or full regression QA. The current public-chat log implementation can wait until the run is paused/completed before appearing in another tab. Subscription cleanup is not regression-clean.

## Assumptions

Owner preview approval authorises validation/PR preparation but not merging or publishing. Screenshots, logs, databases and Redis data remain disposable and outside Git.

## Required Follow-Up

Fix the same-task findings, rerun relevant/full checks, refresh exact-head review/QA and only then prepare a Draft/Ready PR according to the Factory lifecycle.

## Historical QA Decision

Failed to development. Keep TASK-0256 doing; no PR Ready, merge or release.
