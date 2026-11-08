# Task

## Metadata

- Project: superstep
- Task ID: TASK-0227
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-08
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0080
- Phase: Phase 4 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Ship `@superstep/react-native` with `useChat` and basic native components, and an Expo example.

## Scope

### In Scope

- `useChat` binding, `Chat`, `MessageList`, `Composer`, `QuestionCard` (text and form), rating, attachments via a host `pickFile` prop, safe markdown subset, theming props.
- `examples/react-native` (Expo) with the token callback against the sample host.
- `sdk-rn-v*` publish job.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0080.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Review: `.factory-state/artifacts/REV-0264-TASK-0227-react-native-package.md`
- QA: `.factory-state/artifacts/QA-0264-TASK-0227-react-native-package.md`
- Architecture: DEC-0080
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0220

## Acceptance Criteria

- Jest and React Native Testing Library tests in CI with a fake socket.
- Manual checklist with screenshots on an iOS simulator and an Android emulator attached to the PR.

## Validation Plan

- `npm ci && npm test` in `packages/react-native` (own lockfile; not a root workspace, so the frontend React 19 install stays unchanged)
- Manual device checklist (iOS simulator and Android emulator screenshots on the PR)
- Tool-policy commands recorded in QA-0264. Review is REV-0264.

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.
- Manual screenshots are still open. The checklist is `examples/react-native/MANUAL.md`. No iOS simulator or Android emulator was available here, so no images were produced. Attach them on the PR. Do not commit the image files. QA-0264 records this as a follow-up.

## Activity Log

- 2026-11-08: Owner asked to finish through finish-pr. Tool-policy commands passed on this worktree with arm64 Node 22.12.0: root lint, test (frontend 177, React package 22, TypeScript SDK 102) and build; TypeScript SDK typecheck and build; Python SDK pytest 229 passed, 8 skipped; backend pytest 1492 passed, 112 skipped (main-checkout virtualenv, `PYTHONPATH` set to this worktree). `npm test` in `packages/react-native`: 4 suites, 12 tests. Package typecheck and `tsc -p tsconfig.build.json` passed. Review REV-0264 found no blocking issues. QA QA-0264 conditionally passed: the iOS simulator and Android emulator screenshots in `examples/react-native/MANUAL.md` are still open. Moved to done. REQ-0082 stays incomplete. No tag and no npm publish.

- 2026-11-08: Implemented `@superstep/react-native` 0.1.0, `examples/react-native`, the CI Jest job, and the `sdk-rn-v*` publish job. The package stays outside the root npm workspaces so Studio's React 19 install is unchanged. No tag, npm publish, or REQ-0082 completion. Dependencies, recorded against the selection criteria: React 18.3.1, React Native 0.76.9 and react-test-renderer 18.3.1 are the dev pin for the RN 0.76 peers (peer ranges stay `react >=18` and `react-native >=0.73`); `@superstep/sdk` ^0.2.0 is a peer and `file:../../sdk/typescript` is the dev link. `@testing-library/react-native` 13.3.3 (MIT, Callstack) is the maintained line that still accepts React 18 and RN 0.71+; v14 requires React 19 and RN >=0.78. Jest 29, babel-jest, `@babel/core`, `@react-native/babel-preset` 0.76.9, TypeScript 5.6 and `@types/react` 18 are the test toolchain. No markdown library and no `expo-document-picker` in the library (DEC-0080): the built-in renderer covers the safe subset, and the host passes `pickFile`. The example depends on Expo ~52.0.49, expo-document-picker ~13.0.3 and expo-status-bar ~2.0.1; CI does not install or boot it. `npm test` in `packages/react-native`: 4 suites, 12 tests, passed.

- 2026-11-03: Owner temporarily deferred this task and prioritised TASK-0229/0230 for 0.11.0. Remain in backlog, outside that release; resume only on owner request. This is deferral, not cancellation or completion. See PLAN-0002 and proposed DEC-0084.

- 2026-11-08: Owner resumed this task ("triển khai 227"). REQ-0082 and DEC-0077 to DEC-0080 were already Accepted on 2026-10-31, so the move-to-todo assumption holds. Moved from backlog to todo on `factory/task-0227-react-native-package` from `origin/develop` `5624aa7c`. Historical deferral notes stay as written.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0227-react-native-package` from `develop`.
- The pull request targets `develop`. It is Ready after finish-pr. Do not merge until the owner asks.
- Attach the simulator and emulator screenshots to that pull request. Do not commit the image files.
- The main checkout stays on local `develop` and is not the worktree for this task.
