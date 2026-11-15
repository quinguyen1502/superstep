# Task

## Metadata

- Project: superstep
- Task ID: TASK-0221
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-02
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0078
- Phase: Phase 2 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Add headless chat and `mint_chat_token` to the Python `superstep` package.

## Scope

### In Scope

- `Superstep(...).chat(slug, token=...)` sync and async: start, list, get, send (iterator and async iterator), answer, cancel, attachments, ratings.
- `mint_chat_token(key_id, secret, slug, user_id, name=None, ttl=600, meta=None)` with the standard library.
- Socket support through the optional extra `superstep[chat]` (`websockets`).
- Preserve the shared Python SDK/CLI/server version; README (owner amendment 2026-11-02; no downgrade to the obsolete 0.2.0 target).

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0078.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0078
- Review: `.factory-state/artifacts/REV-0216-task-0221-sdk-python-chat.md`
- QA: `.factory-state/artifacts/QA-0216-task-0221-sdk-python-chat.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0218

## Acceptance Criteria

- Tests share the token vectors with TASK-0220; a live integration test streams an answer.

## Validation Plan

- `cd sdk/python && pytest -q`
- `sdk-integration` CI job

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-02: Owner explicitly requested executing the next steps, including merging #285 then #286 then #287 into develop. #285 merged as 81e1ddf; this PR is rebased/retargeted to develop and must pass its final-head CI before merge. No package/tag release is included.

- 2026-11-02: Owner approved the reviewed phase-2 delivery ("Approve"). Move this task to done on existing #286, rebase onto finalised #285, squash to one commit and mark Ready after final gates. Python remains 0.10.2; merge, release and publication remain unapproved. Earlier review/pending entries are historical.

- 2026-11-02: Main CI now also runs for PRs targeting `factory/task-*`, so authorised stacked task PRs receive the same SDK/backend/e2e checks before retargeting develop; push triggers remain main/develop only. Package wheel source and metadata verified against final code, including chat extra, typing marker and bundled CLI changelog.
- 2026-11-02: Full Factory profile passed all eight checks on 0c7c5b4 (backend 481.00 s; Python SDK 14.71 s). Final review added a four-case sync/async pre-dispatch close regression; focused checks now 62 passed and final complete Python suite 217 passed, 8 live tests skipped without the isolated backend. Live SDK run passed Python 8 and TypeScript 7. Python sdist/wheel build under the unchanged 0.10.2 shared version; no release/publication. Enters review with REV-0216 / QA-0216 and one Draft PR stacked on #285.
- 2026-11-02: Implemented sync/async HTTP+socket clients, lazy context-managed streams/final results, strict stdlib minting, one expiry refresh, bounded read-only interruption recovery, file/rating APIs and parent-client cleanup. Recorded-frame and shared-vector focused regression: 58 passed; isolated live integration: Python 8 passed and TypeScript 7 passed. No base runtime dependency added; chat reuses the exact websockets 15.0.1 already approved for CLI, retaining Python >=3.9. Syntax compatibility checked for the four new modules. Full declared verification and package build follow on a committed tree. The unchanged CLI/server version is 0.10.2 pending the owner's later release.
- 2026-11-02: factory ready exited 0 with this task in todo before source edits. task-start preparation complete; owner already authorised implementation and tests of both tasks, so proceed through delivery without a second start confirmation. Owner selected keeping the shared Python version and releasing later; the old standalone 0.2.0 target is superseded. Use installed task-validation/review/QA workflows for final evidence.
- 2026-11-02: Owner explicitly requested TASK-0221 and TASK-0222. This task is stacked on TASK-0220 / #285 at 1a45311 (unmerged), reusing shared token vectors and the v1 form correction. Separate Draft PR targets the TASK-0220 branch until its merge, then develop. No merge/publication is authorised. Existing Python Client/AsyncClient APIs and Python >=3.9 support are preserved; websockets 15.0.1 is reused as the optional chat extra (already used by CLI). The task's old 0.2.0 version conflicts with the current CLI/server-shared 0.10.2; owner preference requested while implementation proceeds. Screenshot evidence stays outside Git.
- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0221-sdk-python-chat`, explicitly stacked on `factory/task-0220-sdk-ts-chat` / #285 after its owner-approved final squash; retarget develop only after dependency merge. Task is done for Ready delivery; merging remains pending explicit approval.
