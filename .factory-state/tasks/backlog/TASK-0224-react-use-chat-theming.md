# Task

## Metadata

- Project: superstep
- Task ID: TASK-0224
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Make `@superstep/react` usable by host apps: `useChat`, public components and theming.

## Scope

### In Scope

- `useChat` (binding of `createChatStore`), `<Chat>`, `<MessageList>`, `<Composer>`, `<QuestionCard>`, `<Rating>`.
- Prebuilt scoped CSS (`styles.css`, `.superstep-chat`, `--ss-*` variables), `theme` prop, en and vi strings with a `locale` prop and overridable messages.
- `sdk-publish.yml`: `sdk-react-v*` tag job with provenance and a version check.

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
- TASK-0223

## Acceptance Criteria

- A Vite example app renders the chat with a custom theme; Testing Library tests for the hook and components; the CSS does not affect host elements outside `.superstep-chat` (test).

## Validation Plan

- `npm test -w packages/react && npm run build -w packages/react`
- Screenshots of the example (light, dark, custom color)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0224-react-use-chat-theming` from `develop`.
