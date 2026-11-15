# Review

## Metadata

- Project: superstep
- Review ID: REV-0264
- Task ID: TASK-0227
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: approved for QA

## Review Scope

`factory/task-0227-react-native-package` against `origin/develop` at `5624aa7c`. The product diff is commit `88603da3` (39 files). It adds `@superstep/react-native` 0.1.0, the Expo example, the CI Jest job, the `sdk-rn-v*` publish job, and the roadmap and PLAN-0002 notes. No backend, schema, Studio UI, or WebView-bridge change. TASK-0228 stays as already done.

## Reference Artifacts

- TASK-0227
- REQ-0082
- PLAN-0002
- DEC-0080
- DEC-0079
- `examples/react-native/MANUAL.md`

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- The manual checklist is not done. No iOS simulator or Android emulator was available, so no screenshots were produced. `examples/react-native/MANUAL.md` says a missing device is an open gap. Attach the images to the pull request later. Do not commit them.
- The Expo example was not installed or booted. Jest covers the library with a fake socket. It does not boot Expo.
- The package is outside the root npm workspaces, so root `npm run lint` does not lint it. Package typecheck and `tsc -p tsconfig.build.json` passed on their own.
- `devDependencies` still links `@superstep/sdk` with `file:../../sdk/typescript`. The publish job builds that SDK in this repo before `npm publish`. Consumers do not install devDependencies. This pull request does not publish.
- Root `oxlint` still reports existing warnings and exits 0. None of those warnings are in the new package.

## Standards And Architecture Alignment

- DEC-0080 option A: a separate package, React Native primitives, no `react-dom`, a thin `createChatStore` binding, and a host `pickFile` prop. The safe markdown subset is built in, with a `renderMarkdown` override. No Swift or Kotlin SDK, and no device end-to-end job.
- The package does not use Studio shadcn tokens. Hosts override the default colours through the `theme` prop.
- The hook does not wrap edit or regenerate. That stays outside this task.
- Historical PLAN-0002 and roadmap sentences that say native work was deferred are unchanged. The new notes say this task resumed on 2026-11-08. REQ-0082 is not marked done.

## Design Alignment

- `QuestionCard` covers text, form, choices, and approval. A free-text question also shows Reject and Approve, matching `@superstep/react`.
- English and Vietnamese labels live in the package and the example. Assistant text goes through the safe renderer. User text stays plain.
- Links open only after an `http:` or `https:` check. `javascript:` stays text.

## Validation Review

- Tool-policy commands passed on this worktree with arm64 Node 22.12.0. Evidence is in QA-0264. `factory verify` was not run through the x86_64 virtualenv.
- `npm test` in `packages/react-native` passed: 4 suites, 12 tests, with a fake socket.

## Assumptions

- The owner asked to finish this pull request, including review, QA, and Ready. That is not a merge approval and not a publish approval.

## Required Follow-Up

- CI on the finished head. Do not merge until the owner asks.
- Attach the simulator and emulator screenshots. Do not tag `sdk-rn-v*` from this pull request.

## Review Decision

approved for QA
