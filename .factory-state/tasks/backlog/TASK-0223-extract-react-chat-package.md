# Task

## Metadata

- Project: superstep
- Task ID: TASK-0223
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
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
- `cd frontend && npm run test:e2e`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0223-extract-react-chat-package` from `develop`.
