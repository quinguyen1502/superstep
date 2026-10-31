# Task

## Metadata

- Project: superstep
- Task ID: TASK-0225
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0077, DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Give the widget a JS API, theming and signed-in embeds via token.

## Scope

### In Scope

- `window.Superstep`: `init`, `open`, `close`, `toggle`, `identify(token | getToken)`, `logout`, `on`/`off` (`ready`, `open`, `close`, `message`, `answer`, `error`), with a command queue for calls before load.
- Data attributes and init options for color, logo, language, position.
- The embed page accepts the token by `postMessage` only from the parent origin in `embed_origins`; never in the URL.
- Same API exposed on `/c/{slug}?embed=1` for the native bridge (TASK-0228).

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0077, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0077, DEC-0079
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
- TASK-0223

## Acceptance Criteria

- Playwright: a host page on another origin identifies a user, sees that user's history, logs out back to anonymous; events fire; a foreign origin's postMessage is ignored.

## Validation Plan

- `cd frontend && npm test && npm run test:e2e`
- Screenshots (en, vi, custom color)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0225-widget-js-api` from `develop`.
