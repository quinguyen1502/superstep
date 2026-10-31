# Task

## Metadata

- Project: superstep
- Task ID: TASK-0227
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0080
- Phase: Phase 4 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Ship `@superstep/react-native` with `useChat` and basic native components, and an Expo example.

## Scope

### In Scope

- `useChat` binding, `Chat`, `MessageList`, `Composer`, `QuestionCard` (text and form), rating, attachments via a host `pickFile` prop, safe markdown subset, theming props.
- `examples/react-native` (Expo) with the token callback against the sample host.
- `sdk-rn-v*` publish job.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0080.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0080
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

## Acceptance Criteria

- Jest and React Native Testing Library tests in CI with a fake socket.
- Manual checklist with screenshots on an iOS simulator and an Android emulator attached to the PR.

## Validation Plan

- `npm test -w packages/react-native`
- Manual device checklist

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0227-react-native-package` from `develop`.
