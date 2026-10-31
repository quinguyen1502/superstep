# Plan

## Metadata

- Plan ID: PLAN-0002
- Requirement: REQ-0082 (chat SDK and toolkit for third-party web and mobile apps)
- Decisions: DEC-0077 (third-party auth), DEC-0078 (API versioning, schema, transport), DEC-0079 (package layout and UI reuse), DEC-0080 (React Native approach). All Proposed.
- Tasks: TASK-0215 to TASK-0230 (all in backlog until the owner approves; then phase 1 moves to todo)
- Date: 2026-10-31
- Delivery: one PR per task into `develop`, branch `factory/task-NNNN-<slug>`; a task starts only when its dependencies are merged.

## Order and dependencies

| Task | Phase | Size | Depends on | Main pieces |
|---|---|---|---|---|
| TASK-0215 public chat API v1 | 1 | M | none | `/api/public/v1/chat`, aliases, `turns?after=`, public OpenAPI |
| TASK-0216 socket protocol v1 | 1 | M | 0215 | typed frames, JSON Schema, AsyncAPI, contract tests |
| TASK-0217 app keys | 1 | L | 0215 | `chat_app_keys`, access set, encrypted secrets, rotate and revoke, settings UI |
| TASK-0218 user tokens | 1 | L | 0216, 0217 | HS256 verifier, per-user scoping, CORS, limits, error codes |
| TASK-0219 handbook (API, auth, compatibility) | 1 | M | 0218 | en and vi pages, CHANGELOG |
| TASK-0220 TypeScript SDK chat | 2 | L | 0218 | `client.chat`, async iterator, refresh, `createChatStore`, `mintChatToken`, 0.2.0 |
| TASK-0221 Python SDK chat | 2 | M | 0218 | sync and async chat, `mint_chat_token`, `superstep[chat]`, 0.2.0 |
| TASK-0222 sample host and e2e | 2 | M | 0220, 0221 | `examples/chat-host`, cross-origin Playwright job |
| TASK-0223 extract `@superstep/react` | 3 | L | 0216 | npm workspace, move chat UI, no visual change |
| TASK-0224 `useChat`, components, theming | 3 | M | 0220, 0223 | public components, scoped CSS, `sdk-react-v*` publish |
| TASK-0225 widget JS API | 3 | M | 0218, 0223 | `window.Superstep`, events, theming, `identify` |
| TASK-0226 web docs and examples | 3 | S | 0224, 0225 | handbook pages, e2e pages |
| TASK-0227 `@superstep/react-native` | 4 | L | 0220 | RN components, Expo example, `sdk-rn-v*` publish |
| TASK-0228 native WebView guide and bridge | 4 | M | 0225 | bridge protocol, Swift and Kotlin guide, browser e2e |
| TASK-0229 edit message | backlog | L | 0216 | DEC first |
| TASK-0230 regenerate answer | backlog | M | 0216 | DEC first |

Critical path: 0215, 0216, 0217 (parallel with 0216), 0218, 0220, 0224 or 0227. TASK-0223 can run in parallel with 0217 and 0218.

## Shared rules

- Planning first: no task moves to todo before the owner accepts the DECs (or amends them).
- Every API error uses the common envelope; new codes in CATALOG, `docs/api-errors.md`, en and vi.
- The v1 contract is additive only once TASK-0219 ships (DEC-0078 compatibility policy).
- Secrets are never in URLs, logs, fixtures or screenshots.
- Publishing: tags `sdk-ts-v*`, `sdk-py-v*`, `sdk-react-v*`, `sdk-rn-v*` through `sdk-publish.yml` (environment `npm` or `pypi`); tags are created only on the owner's release approval.

## Verification strategy

- Backend: pytest on SQLite and Postgres; security tests for every token failure mode and for cross-user isolation; contract tests of the socket schema.
- SDKs: unit tests with recorded v1 frames in Node, jsdom and a no-DOM environment; shared token test vectors between Node, Python and the backend; the existing `sdk-integration` job extended to chat.
- E2E: `examples/chat-host` served on a second origin in CI (Playwright): headless page, React page, widget page, two users, Human form answer, attachment, rating, key revocation.
- UI: screenshots in 4 variants (light, dark, en, vi) for settings and toolkit; the extraction task compares screenshots before and after.
- Mobile: RN unit tests in CI; a manual iOS simulator and Android emulator checklist with screenshots.
- `factory verify run --profile full` and `factory validate` on each task PR.

## Open questions (with recommendations)

1. App key JWT (HS256) as the MVP, asymmetric keys later (DEC-0077)? Recommended: yes.
2. Also ship a token-exchange endpoint now? Recommended: no.
3. Default token lifetime 10 minutes, maximum 1 hour? Recommended: yes.
4. Empty allowed-origin list means any origin (for native apps)? Recommended: yes, with a UI warning.
5. `meta` user attributes in the MVP (1 KB, untrusted)? Recommended: yes.
6. Rename `node_token` to `token` in v1 and keep one message per socket? Recommended: yes and yes.
7. No SSE transport for now? Recommended: yes, revisit on demand.
8. Headless chat inside `@superstep/sdk` (`/chat` subpath) rather than a new package? Recommended: inside.
9. Move the repository to npm workspaces so the studio consumes `@superstep/react`? Recommended: yes.
10. Separate `@superstep/react-native` package, no device e2e in CI for now? Recommended: yes.
11. Release grouping: ship phases 1 and 2 as 0.11.0, phases 3 and 4 as 0.12.0? Recommended: yes.
