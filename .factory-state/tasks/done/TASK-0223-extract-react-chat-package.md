# Task

## Metadata

- Project: superstep
- Task ID: TASK-0223
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-02
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Extract the chat UI into `packages/react` (`@superstep/react`) in an npm workspace, consumed by the studio, with no visual change.

## Scope

### In Scope

- Root npm workspace (`frontend`, `packages/react`, `sdk/typescript`); CI and Dockerfile updated.
- Move thread, composer, attachments, rating, steps, confirmation, markdown, logo into the package; studio-only parts stay in `frontend`.
- The studio public page moves to the v1 paths.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0079
- Review: `.factory-state/artifacts/REV-0218-task-0223-extract-react-chat-package.md`
- QA: `.factory-state/artifacts/QA-0218-task-0223-extract-react-chat-package.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0216

## Acceptance Criteria

- Existing chat e2e (en, vi) pass unchanged; screenshots match before and after (4 variants).
- Frontend bundle size grows by at most 5 percent.

## Validation Plan

- `npm run lint && npm test && npm run build` at the root
- `npm run test:e2e` at the root (delegates to the existing frontend `e2e` script)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-02: Owner accepted the reviewed implementation and explicitly requested merging existing #288 ("Ok merge"). Move this task to done on this PR, squash to one commit against current develop 221df9a, push with lease, wait for exact-head CI, mark Ready and merge. Approved source 46e001a6 already passed all 20 CI checks (one expected publication skip); finalisation changes lifecycle records only. No package/tag release is authorised. Earlier pending-approval entries are historical.

- 2026-11-02: Factory npm-workspace compatibility was required by the accepted migration. Upstream main commit ce00ad0 (quinguyen1502/sw-ai-factory) passed all 146 tests before push; copied the same dependency service/test files byte-for-byte into .factory. Declared workspace members now share one locked root install; hoisted/nested dependencies remain validated, unrelated packages remain independent. No skill template changed. Initial extraction: 8 chat components, 16 shadcn primitives, shared pure helpers/highlighter; Studio child-run/navigation capabilities stay in a small host provider. Public HTTP/socket move to v1; legacy logo asset URLs remain compatible with existing e2e assertions.

- 2026-11-02: Final local delivery passes full Factory rerun 8/8 (backend 484.14 s), root build/lint/tests (152 frontend, 4 React, 94 TypeScript SDK), unchanged chat e2e 16, TypeScript export 39 and clean-install two-origin sample host (3 Node + 1 Chrome). Aggregate JS/CSS is 3712776 bytes versus baseline 3711598 (+0.03174%). Four screenshot variants were inspected: dark frames identical, light frames differ only by 19 avatar-corner pixels. No images committed. REV-0218 has no blocking findings; QA-0218 passes with documented limits. Move to review for one Draft PR into develop; exact-head CI and owner acceptance follow. No merge/publication of this new task authorised.

- 2026-11-02: Full verification exposed a Deno-test setup assumption: the new root package.json enabled manual npm resolution. Tests now explicitly use the isolated Deno cache for check/run (no-config/no-lock/node-modules-dir=none); no exporter/runtime logic or assertion changed. All 39 TypeScript export tests pass. Corrected mixed local Node architectures by installing with the same arm64 wrapper used for verification; no dependency version changes. The failed full run is preserved in QA-0218 and is followed by a full rerun.

- 2026-11-02: Phase-2 merges completed in owner-requested order: #285 (81e1ddf, 20 checks), #286 (ed197b2, 19 checks after retarget/rebase), #287 (221df9a, 21 checks after retarget/rebase). This task is rebased onto final develop 221df9a. Root build/lint/tests pass: frontend 151, React package 3, TypeScript SDK 94. Browser history snapshots load in all four variants; initial JS/CSS comparison grows 0.029 percent (3711598 to 3712691 bytes). Existing chat e2e and clean installation are being verified before review.

- 2026-11-02: factory ready exited 0 before implementation. Start context: extract the existing presentation and its shadcn dependency closure into packages/react, leave settings/session/run ownership and Studio navigation in frontend, migrate public HTTP/socket transport to v1, and keep en/vi light/dark rendering unchanged. Capture baseline bundle/snapshots before source edits, then validate unchanged chat e2e and <=5 percent bundle growth. Owner already authorised the full task, so proceed through implementation and verification without a second start gate.

- 2026-11-02: Owner requested executing the recommended merge and TASK-0223 sequence. Branch starts from develop 81e1ddf after #285 merged; TASK-0216 dependency and DEC-0079 acceptance are satisfied. #286/#287 merge separately while this independent extraction is prepared; rebase onto final develop before delivery. Scope includes implementation, regression/visual/bundle validation, review/QA and a Draft PR, not merging this new task or publishing packages. Screenshots remain outside Git. No new external dependency versions are planned; existing approved UI dependencies move with their components.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0223-extract-react-chat-package` from develop, rebased onto 221df9a. Review/QA: REV/QA-0218. Existing PR #288 into develop is owner-approved for finish/merge after final-head checks; package publication remains pending separate approval. Python shared version remains 0.10.2. Screenshots are temporary files / CI artifacts only.
