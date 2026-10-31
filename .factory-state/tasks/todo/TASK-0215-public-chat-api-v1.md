# Task

## Metadata

- Project: superstep
- Task ID: TASK-0215
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0078
- Phase: Phase 1 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Expose the public chat HTTP API as a versioned, documented contract in the public OpenAPI.

## Scope

### In Scope

- Router prefix `/api/public/v1/chat/{slug}` for page, logo, sessions list/create/get, attachments upload/download/delete, ratings put/delete; the unversioned paths stay as aliases with the same handlers.
- New `GET .../sessions/{sid}/turns?after=<turn_id>` for incremental history.
- `openapi_public.py` includes the chat routes under a `Chat` tag with response models and documented error codes; `/openapi.public.json` regenerated.
- Tests: alias and v1 return identical bodies; the public OpenAPI lists every chat path; envelope tests pass.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0078.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0078
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- None

## Acceptance Criteria

- `/openapi.public.json` lists all v1 chat endpoints with schemas.
- Old paths behave exactly as before (existing tests unchanged).
- `turns?after=` returns only newer turns of the caller's session.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `factory validate`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0215-public-chat-api-v1` from `develop`.

## Status Log

- 2026-10-31: backlog to todo. The owner approved PLAN-0002 and DEC-0077 to DEC-0080 on PR #271.
