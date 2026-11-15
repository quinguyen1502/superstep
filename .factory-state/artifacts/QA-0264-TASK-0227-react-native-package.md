# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0264
- Task ID: TASK-0227
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: pass with follow-up

## Validation Scope

TASK-0227 `@superstep/react-native` 0.1.0, the Expo example, the CI Jest job, and the `sdk-rn-v*` publish job. Review is REV-0264. The product tree reviewed is commit `88603da3` on `factory/task-0227-react-native-package` against `origin/develop` `5624aa7c`. Finish-pr adds this record, the review, and the done move. It does not change the package source.

## Acceptance Criteria Coverage

- Criterion: Jest and React Native Testing Library tests in CI with a fake socket.
  - Result: pass
  - Evidence: `packages/react-native` `npm test -- --watchman=false` passed, 4 suites and 12 tests. The tests render `Chat` with the harness socket, cover a streamed reply, the token callback, a picked file, a question answer, and rating. `.github/workflows/ci.yml` job `React Native package (Jest)` runs `npm ci && npm test` in that package on Node 22. That job has not run on GitHub yet because the branch was not pushed when these commands ran.
- Criterion: Manual checklist with screenshots on an iOS simulator and an Android emulator attached to the pull request.
  - Result: gap
  - Evidence: `examples/react-native/MANUAL.md` is the checklist. No simulator or emulator was available. No images were produced or committed. The checklist says a missing device is an open gap.

## UX And Accessibility Coverage

- Criterion: Controls expose a role and a label, in English and Vietnamese.
  - Result: pass for the automated checks
  - Evidence: Composer, question, rating, and markdown tests query by role and name, including Vietnamese `Helpful` and `Waiting for a reviewer`. Errors use `accessibilityRole="alert"`. No VoiceOver or TalkBack pass was run.
- Criterion: The example sign-in path on a device.
  - Result: gap
  - Evidence: `examples/react-native` was not installed or booted. The sample host was not started.

## Checks Performed

- `packages/react-native`: `npm test -- --watchman=false`. 4 suites, 12 tests, passed. Pretest built `@superstep/sdk`.
- `packages/react-native`: `npx tsc -p tsconfig.json --noEmit` and `npx tsc -p tsconfig.build.json`. Both exit 0.
- Root `npm run lint`. Exit 0. 37 existing frontend warnings and 1 existing React-package warning. The new package is not a root workspace.
- Root `npm run test`. Exit 0. Frontend 177 passed, `@superstep/react` 22 passed, TypeScript SDK 102 passed.
- Root `npm run build`. Exit 0.
- `sdk/typescript`: `npm test` (102 passed), `npm run typecheck`, and `npm run build`. All exit 0.
- `sdk/python`: `.venv/bin/python -m pytest` with `PYTHONPATH` set to this worktree. 229 passed, 8 skipped, in 14.25s.
- Backend `.venv/bin/python -m pytest` with `PYTHONPATH` set to this worktree. 1492 passed, 112 skipped, in 611.10s. Exit 0. The virtualenv is the main checkout's. The worktree has no `backend/.venv`.
- `git diff --check` on commit `88603da3`. Exit 0. Repeated after the finish-pr artifact edits.
- Commands used this worktree's sources. Node was arm64 v22.12.0. `factory verify` was not launched through the x86_64 virtualenv.

## Defects

- None that fail an acceptance criterion in the automated checks.

## Gaps Or Untested Areas

- No iOS simulator screenshots and no Android emulator screenshots.
- The Expo example and the sample host were not booted.
- The new CI job and the `sdk-rn-v*` job have not run on GitHub. The publish job runs only on a `sdk-rn-v*` tag, which this delivery does not push.

## Residual Risk

- A device-only failure in the Expo example, cookie handling, or cleartext loopback setup can still show up when the checklist is run.
- GitHub Actions can still fail the new Jest job even though the same `npm test` passed locally.

## Assumptions

- The owner accepts a Ready pull request while the screenshot checklist stays open. That is not a merge approval and not permission to tag or publish.
- REQ-0082 stays incomplete.

## Required Follow-Up

- CI on the finished head. Merge only when the owner asks.
- Attach the images from `examples/react-native/MANUAL.md` to the pull request. Do not commit them.
- Publish `@superstep/react-native` only after a separate release instruction.

## QA Decision

conditionally passed with documented risk
