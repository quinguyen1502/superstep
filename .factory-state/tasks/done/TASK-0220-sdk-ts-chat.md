# Task

## Metadata

- Project: superstep
- Task ID: TASK-0220
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-02
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
- Review: `.factory-state/artifacts/REV-0215-task-0220-sdk-ts-chat.md`
- QA: `.factory-state/artifacts/QA-0215-task-0220-sdk-ts-chat.md`
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

- 2026-11-02: Owner approved the reviewed phase-2 delivery ("Duyệt"). Finalise existing #285 as one commit and Ready, with this task in done; merge and publication remain unapproved. Move the already-reviewed browser fetch receiver fix and its three-runtime regression from #287 into this SDK PR, preserving the final stack source tree. Final validation and remote checks are recorded in QA-0215.

- 2026-11-02: Final full Factory rerun passed all eight declared checks on 9aeeba8 after the v1-only form correction (backend 471.48 s). REV-0215 has no unresolved blocking findings; QA-0215 passes locally. Final delivery record changes only task/review/QA evidence and the generated verification outcome. One Draft PR into develop follows; owner acceptance, merge and publishing remain pending.
- 2026-11-02: Implemented chat/client/store and server signing with no runtime dependencies. Same 19 recorded-frame contract cases pass in Node, jsdom and a native-like environment without DOM/Buffer globals; 91 SDK unit tests pass. Live integration passes Python workflow (2) and TypeScript workflow/chat (7), including user isolation, visitor persistence, files/ratings, expiry/revoke and Human text/form answers. Backend interoperability checks use shared synthetic UTF-8 HS256 vectors. No screenshots or real credentials are committed.
- 2026-11-02: Live form testing exposed a pre-existing mismatch: the accepted v1 schema permits object answers but RunService rejected them. The first full run exposed a legacy LangGraph contract regression (1200 backend passed, one failed). Restricted bounded, strict JSON forms to an explicit server-side opt-in on the v1 chat route. Studio, inbox, channels, unversioned socket and LangGraph retain text/boolean validation. Scalar/array/non-finite/oversized/malformed values remain invalid. Error catalog/docs/en/vi remain aligned. This is a v1 protocol compatibility fix, not a form builder or new UI. No database/schema change. Revalidation required after this correction.
- 2026-11-02: Dependency assessment for the required DOM contract suite: use jsdom 26.1.0 as an SDK devDependency only (official jsdom/jsdom v26.1.0 package/release, stable MIT, Node >=18). The project already uses jsdom for frontend tests; this Node-18-compatible test version allows the same client contract in Node/jsdom/native-like environments. No SDK runtime dependency is added or shipped. Source/provenance/platform/license checked at https://github.com/jsdom/jsdom/blob/v26.1.0/package.json; do not add canvas or enable script execution/network in DOM tests.
- 2026-11-02: factory ready exited 0 before implementation. Read actual v1 HTTP/OpenAPI and socket schemas, auth verifier and current SDK. Delivery includes client/chat/server entrypoints, schema-generated frame types, injected WebSocket transport, typed streams and framework-neutral store, server-side minting, meaningful cross-runtime/unit/token-vector/live integration coverage and README. Network interruption recovers persisted history without resending an ambiguous message; auth expiry retries once before execution. No new runtime dependency or backend schema change expected.
- 2026-11-02: Owner confirmed starting the recommended next task. REQ-0082/DEC-0077–0080 were accepted under #271 and TASK-0218 is merged. Dedicated branch factory/task-0220-sdk-ts-chat starts from develop 019071e. Scope is this TypeScript SDK task with tests/review/QA and one Draft PR; publishing, later-phase tasks and merging this new PR require their own authorisation. Screenshot evidence stays out of Git per owner instruction.
- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0220-sdk-ts-chat` from `develop`.
- Owner accepted the implementation on 2026-11-02. Task is done for Ready delivery on #285; merge and package publication remain pending. Node 18/20/22 matrix runs in existing CI; physical native devices and cross-origin sample-host UI belong to later PLAN-0002 tasks.
