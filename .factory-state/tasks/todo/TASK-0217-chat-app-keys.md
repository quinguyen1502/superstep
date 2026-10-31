# Task

## Metadata

- Project: superstep
- Task ID: TASK-0217
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0077
- Phase: Phase 1 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Add per-chat app keys (server credentials) with create, rotate and revoke, and the `app` access mode.

## Scope

### In Scope

- Alembic revision: `chat_app_keys` table; `chat_sessions.external_user`, `chat_sessions.app_key_id`, index `(trigger_id, external_user)`.
- `access` read as a set (`anonymous`, `signed_in`, `app`), backward compatible with the single string.
- Secret generated server-side (32 bytes), encrypted with the existing credential encryption, shown once, never logged; at most two active keys per chat.
- Owner/admin API to list (no secret), create, revoke; `last_used_at`; audit log entries.
- Chat settings dialog: access checkboxes, app keys list, create (copy-once dialog), revoke with ConfirmDeleteDialog, allowed origins; en and vi strings.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0077.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0077
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0215

## Acceptance Criteria

- Creating a key returns the secret once; listing never returns it; a third key while two are active fails with a catalog code.
- Non-owners get 403.
- Migration upgrades and downgrades on SQLite and Postgres.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run lint && npm test && npm run build`
- Screenshots of the app keys section (light, dark, en, vi).

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0217-chat-app-keys` from `develop`.

## Status Log

- 2026-10-31: backlog to todo. The owner approved PLAN-0002 and DEC-0077 to DEC-0080 on PR #271.
