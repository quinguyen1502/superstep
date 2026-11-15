# Task

## Metadata

- Project: superstep
- Task ID: TASK-0222
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-02
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0079
- Phase: Phase 2 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Add a sample third-party host app and an e2e job that proves the token flow end to end.

## Scope

### In Scope

- `examples/chat-host`: a small Node server (sign-in stub, mints tokens with `@superstep/sdk/server`) and a page using the headless SDK, served on a different origin.
- CI job: start the studio with a seeded chat and an app key, run Playwright against the host origin: sign in as two users, stream an answer, answer a Human form, rate, upload an attachment, prove isolation between users, revoke the key.
- Release notes for TypeScript SDK 0.2.0 and Python chat under its shared SDK/CLI/server release version (owner amendment 2026-11-02; no Python downgrade to 0.2.0). No tags/publication without release approval.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0079
- Review: `.factory-state/artifacts/REV-0217-task-0222-chat-sample-host-e2e.md`
- QA: `.factory-state/artifacts/QA-0217-task-0222-chat-sample-host-e2e.md`
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
- TASK-0221

## Acceptance Criteria

- The e2e job is green in CI; host screenshots are linked from the PR as CI artifacts and shown from temporary local files, never committed (owner requested removing screenshot evidence from Git).

## Validation Plan

- CI `chat-host-e2e` job
- `factory verify run --profile full`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-02: Owner explicitly authorised merging #285, #286 and #287 into develop and continuing TASK-0223. #285/#286 are merged; this PR is rebased/retargeted to develop and must pass all final-head CI before merge. No package/tag release is authorised.

- 2026-11-02: Owner approved the reviewed phase-2 delivery ("Approve"). Move this task to done on existing #287, restack onto finalised #286, squash to one commit and promote to Ready after final gates. The already-reviewed fetch correction/regression now belongs to #285; final stack source is unchanged. Final-head host CI and screenshot artifact remain required. No merge/publication approval is implied; earlier pending entries are historical.

- 2026-11-02: Rebased onto TASK-0221/#286 at bc1cd9f. Final full Factory profile passed all eight on 80116c2 (backend 480.53 s); TypeScript 94 unit tests/gen/typecheck and sample oxlint/UI conventions passed. Final Chrome acceptance includes mobile overflow, all four theme/locale variants, real CORS/WS, file/form/rating, two-user isolation, history restore and revoke with no new turns. Three Node security/locales/static-serving tests pass; both SDKs' live integration passes Python 8 / TypeScript 7. Added fixture occupied-port refusal and pinned DB storage, then reran both scripts successfully. Local screenshots are kept outside Git and auth traces disabled. REV/QA-0217 record local evidence; latest Draft PR CI is the required automated acceptance gate. No merge/publication authorised.
- 2026-11-02: Implemented isolated Node demo/session/token server, existing-shadcn en/vi light/dark page using the headless store, restricted-origin seeding, shared build/security/e2e script, CI chat-host-e2e job and bilingual guide/release notes. Actual Chrome acceptance passed full form/file/rating/isolation/origin/revoke flow; three Node security/locales/static-serving cases pass. Browser testing exposed a default-fetch receiver bug not caught by injected mocks: bind platform fetch to globalThis in both SDK constructors, with a three-runtime regression (94 TS unit tests pass). Final responsive pass and full Factory verification follow. Screenshots remain ignored/local and CI artifacts; no secret-bearing auth trace is retained.
- 2026-11-02: factory ready exited 0 in this worktree with TASK-0222 in todo before source edits. Use the existing frontend React/shadcn/i18n dependencies and built TypeScript SDK via a dedicated Vite config; no workspace/package migration or new dependency. Node host uses standard-library HTTP/crypto and the SDK server entry.
- 2026-11-02: Owner explicitly requested implementation of TASK-0221 and TASK-0222. This task is explicitly stacked on TASK-0221 at 0c7c5b4, which itself includes unmerged TASK-0220/#285. Task-0221's recorded/shared-vector tests and live sync/async integration pass; full verification runs separately. A dedicated temporary worktree isolates the sample host while those checks run. No merge/release is implied. Owner chose preserving Python's shared CLI/server version and releasing later.
- 2026-11-02: UX scope: loopback-only demonstration host with explicit demo opt-in, two fixed sign-in personas, server-owned opaque sessions and server-only minting; browser calls studio directly on a second origin using the headless store. Cover session history, sending/streaming, a sample approval form, attachment upload, rating and key-revocation errors. Reuse shadcn controls/theme tokens and project error localisation; all sample strings in matching en/vi dictionaries. No public account/password system, general form builder, UI package extraction, or production deployment.
- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0222-chat-sample-host-e2e`, stacked on TASK-0221/#286 after its owner-approved squash (which stacks on TASK-0220/#285); retarget only after dependency merges. Task is done for Ready delivery; merge remains pending explicit approval. Python retains shared version 0.10.2 until owner-approved release. Screenshots are downloadable CI artifacts/temporary local files, not repository evidence images.
