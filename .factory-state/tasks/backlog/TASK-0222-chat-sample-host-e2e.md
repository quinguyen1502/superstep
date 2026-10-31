# Task

## Metadata

- Project: superstep
- Task ID: TASK-0222
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
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
- Release notes for `sdk-ts-v0.2.0` and `sdk-py-v0.2.0` (tags pushed only after the owner approves the release).

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0079
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

- The e2e job is green in CI; screenshots of the host page in the PR.

## Validation Plan

- CI `chat-host-e2e` job
- `factory verify run --profile full`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0222-chat-sample-host-e2e` from `develop`.
