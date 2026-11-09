# Task

## Metadata

- Project: superstep
- Task ID: TASK-0224
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-03
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Make `@superstep/react` usable by host apps: `useChat`, public components and theming.

## Scope

### In Scope

- `useChat` (binding of `createChatStore`), `<Chat>`, `<MessageList>`, `<Composer>`, `<QuestionCard>`, `<Rating>`.
- Prebuilt scoped CSS (`styles.css`, `.superstep-chat`, `--ss-*` variables), `theme` prop, en and vi strings with a `locale` prop and overridable messages.
- `sdk-publish.yml`: `sdk-react-v*` tag job with provenance and a version check.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0079
- Review: `.factory-state/artifacts/REV-0219-task-0224-react-toolkit.md`
- QA: `.factory-state/artifacts/QA-0219-task-0224-react-toolkit.md`
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
- TASK-0223

## Acceptance Criteria

- A Vite example app renders the chat with a custom theme; Testing Library tests for the hook and components; the CSS does not affect host elements outside `.superstep-chat` (test).

## Validation Plan

- `npm test -w packages/react && npm run build -w packages/react`
- Screenshots of the example (light, dark, custom color)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-02: factory ready exited 0 before source edits. Use task-start preparation and the installed validation/review/QA workflows through delivery; the owner already authorised implementation and tests, so no second start confirmation is needed. UX: existing shadcn chat layout, history/new conversation, streaming/cancel, Human question answers, files, ratings, en/vi and per-instance light/dark/custom theme. Public CSS must be isolated from host content; portals remain inside that same scope. Tests include StrictMode/identity cleanup, CSS leakage and real-browser screenshots outside Git.

- 2026-11-02: Owner explicitly requested implementing the recommended TASK-0224 through tests/screenshots and one Draft PR. TASK-0220/#285 and TASK-0223/#288 are merged; branch starts from develop 7c7348bc. REQ-0082/DEC-0079 remain accepted. Scope: public useChat binding over the existing store, shared public components, isolated prebuilt CSS/theme/locales, Vite example and release pipeline preparation. No merge/tag/package publication authorised. Screenshots stay outside Git; preserve Python shared 0.10.2.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0224-react-use-chat-theming` from `develop`.

- 2026-11-02: Dependency assessment before manifest changes: Testing Library is explicitly required by the accepted task. Registry/official docs verify @testing-library/react 16.3.3 and @testing-library/dom 10.4.2, stable MIT, official testing-library repositories, no deprecated flag, Node >=18 and React 18/19 peers. Dev-only; no new public runtime dependency. Reuse already-locked Tailwind 4.3.3/node/oxide, PostCSS 8.5.30 and selector-parser 7.1.6 for a parsed/scoped build, and existing jsdom for DOM tests. Sources: https://testing-library.com/docs/react-testing-library/intro/ and the official npm metadata. CSS publishes ss-prefixed selectors plus scoped compatibility selectors so the extracted shadcn markup has one source; variables/keyframes are namespaced and portals stay in scope.

- 2026-11-02: Peer compatibility assessment: official registry metadata verifies react/react-dom 18.3.1, MIT, no deprecated flag and matching React DOM peer. Install only in an isolated temporary test fixture; app/package manifests retain existing React 19. Browser matrix aliases all React entries to that fixture and asserts the actual runtime version. Button/InputGroupButton forward refs for Radix asChild on React 18.

- 2026-11-02: Implementation checkpoint: hook/controller, composed/shared components, per-provider locale/theme and portals, namespaced CSS build, Vite consumer, React 18/19 browser matrix and tag-only provenance job. Testing Library/CSS suite passes 15 tests. Chrome React 18 and 19 flows pass with mock Human/files/ratings and identity changes; final React 18 rerun adds actual download and console checks. No screenshots tracked. Dependency state is refreshed using the same ARM64 runtime used for validation. Full declared checks follow on the committed checkpoint.

- 2026-11-02: Full checkpoint validation on ed434764 passed 7/8 checks. Backend: 1199 passed, 18 skipped, one unchanged timing assertion failed (Human pause elapsed 0.347 s vs <0.2 s); isolated rerun passes without changing backend or assertions. Source review also found SDK-turn typing for Rating, session-load input state, and stale destructive dialogs on identity switches; these are corrected with regressions and a compiled public-contract probe. Ambient host data-color-scheme no longer activates another provider's dark variant. Final unit suite has 17 tests; React 19 browser acceptance passes after these corrections. Re-run the full profile on the clean final implementation; record its actual outcome in QA-0219.

- 2026-11-02: Final source full Factory profile passes all 8 checks on clean 3e6e8f69, superseding the recorded initial timing failure without weakening its assertion. Final metadata-only provenance repository declaration is followed by dependency-state refresh and canonical root build/lint/tests/pack checks. React 18/19 browser acceptance and 17 toolkit tests pass. REV-0219 / QA-0219 record advisory source review/QA and residual limits. Move to review for one Draft PR; no Ready/done/merge/tag/publication approval. Screenshots stay outside Git.

- 2026-11-03: First-head CI exposed a cold-start gap: general Playwright started Vite directly, without generated package locales/SDK dist. Clean npm ci reproduction confirms the overlay; moving package build to frontend predev and routing root/dev.sh/Playwright through npm dev fixes cold startup (email form visible, no overlay/page errors). No chat/backend runtime or dependency-version change. REV/QA-0219 retain the initial CI gap and upcoming canonical/targeted rerun; old CI run cancelled to avoid known-failing timeouts.

- 2026-11-03: Bootstrap follow-up validation passes: canonical root build/lint/tests (152 frontend, 17 toolkit, 94 SDK), 16/16 chat regressions on a fresh npm-ci checkout with missing SDK/toolkit dist/generated locales, and 4/4 repetitions of the two initially unstable cases. UI fixture isolates shared-IP read quota; dedicated backend rate-limit test still passes and daily-cap assertions are retained. Settings dialog is settled and asserted visible before scroll. Review/QA updated on the same Draft PR #289; push updated head and wait for CI.

- 2026-11-03: Owner accepted the reviewed implementation on PR #289 ("Approve"). Reviewed head b0c21ab65da49d28e120c57fb13b2d28b19614c7 passed 21 CI checks with one expected GHCR skip, including all three general Playwright shards after the cold-start correction. Move to done on the same PR, rebase/squash to one commit, rerun required final validation and promote that PR to Ready. Preserve the accepted implementation tree. This is implementation acceptance; merge, release tag, package publication and deployment remain unauthorised. Final rewritten-head verification/CI results are reported on #289.
