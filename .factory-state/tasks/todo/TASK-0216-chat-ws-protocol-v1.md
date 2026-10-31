# Task

## Metadata

- Project: superstep
- Task ID: TASK-0216
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

Specify the chat socket protocol v1 formally and serve it at `/ws/public/v1/chat/{slug}`.

## Scope

### In Scope

- Typed client frames (`auth`, `message`, `answer`, `cancel`) and server frames (`ready`, `run_started`, `token`, `step`, `question`, `turn`, `done`, `error`) with `v` and `seq`.
- JSON Schema files under `backend/app/api/schemas/chat_ws_v1/` and `docs/asyncapi/chat-v1.yaml`, served at `/asyncapi.public.yaml`.
- The old socket path keeps the current untyped frames and `node_token`.
- Contract tests validate every frame the server sends in the chat tests against the schema.

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

- TASK-0215

## Acceptance Criteria

- A v1 conversation (message, streaming tokens, Human question, answer, done) passes schema validation frame by frame.
- Unknown client frame types return an `error` frame with a catalog code.
- The old path is unchanged (existing e2e pass).

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run test:e2e` (chat specs)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.
- 2026-10-31: backlog to todo. The owner approved PLAN-0002 and DEC-0077 to DEC-0080 on PR #271.

## Handoff Notes

- Branch `factory/task-0216-chat-ws-protocol-v1` from `develop`.
