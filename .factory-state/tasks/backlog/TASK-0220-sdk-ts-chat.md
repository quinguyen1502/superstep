# Task

## Metadata

- Project: superstep
- Task ID: TASK-0220
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0078, DEC-0079
- Phase: Phase 2 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Add headless chat to `@superstep/sdk` for browsers, Node and React Native.

## Scope

### In Scope

- `client.chat(slug, {getToken?, visitorToken?, fetch?, WebSocket?})` with `info`, `start`, `list`, `get`, `send` (async iterator of typed events and a final result), `answer` (text and form), `cancel`, attachments (Blob, File, Node Buffer, RN `{uri,name,type}`), ratings.
- Types generated from the JSON Schema of DEC-0078; unknown events ignored.
- Token refresh: `getToken` called on start and on `CHAT_TOKEN_EXPIRED`, one retry; reconnection resumes history with `turns?after=`.
- `createChatStore` (framework-agnostic state for UIs).
- Server helper `mintChatToken` in a `@superstep/sdk/server` entry (Node crypto; Web Crypto fallback for edge runtimes).
- Zero runtime dependencies; version 0.2.0; README.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0078, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0078, DEC-0079
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

- Unit tests with a fake socket replaying recorded v1 frames; Node, jsdom and an RN-like environment (no DOM) run the same suite.
- `mintChatToken` output verifies in the backend verifier (shared test vectors).

## Validation Plan

- `cd sdk/typescript && npm test && npm run build`
- `sdk-integration` CI job against a live backend

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0220-sdk-ts-chat` from `develop`.
