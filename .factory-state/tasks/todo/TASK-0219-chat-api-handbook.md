# Task

## Metadata

- Project: superstep
- Task ID: TASK-0219
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0077, DEC-0078
- Phase: Phase 1 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Document the public Chat API, the socket protocol, third-party auth and the compatibility policy in the handbook (en, vi).

## Scope

### In Scope

- `reference/api.md` chat section complete (attachments, ratings, turns), linking the OpenAPI and AsyncAPI documents.
- New `run/chat-api.md` (socket protocol with examples), `run/chat-third-party-auth.md` (app keys, minting in Node, Python, Go and PHP snippets, rotation, security checklist), `reference/compatibility.md` (versioning, deprecation).
- CHANGELOG entry.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0077, DEC-0078.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0077, DEC-0078
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

- Pages exist in en and vi with the same structure; handbook build passes; no emoji.

## Validation Plan

- `handbook` build in CI
- `factory validate`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.
- 2026-10-31: backlog to todo. The owner approved PLAN-0002 and DEC-0077 to DEC-0080 on PR #271.

## Handoff Notes

- Branch `factory/task-0219-chat-api-handbook` from `develop`.
