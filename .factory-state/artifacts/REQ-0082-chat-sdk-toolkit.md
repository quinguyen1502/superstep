# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0082
- Status: Accepted on 2026-10-31 (PR #271). Phase 1 (TASK-0215 to TASK-0219) is in todo.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Source: owner request on 2026-10-31: a chat SDK and toolkit so that third-party web and mobile apps can integrate Superstep chat, with the owner decisions recorded under "Clarifications".
- Related Decision: DEC-0077 (third-party auth), DEC-0078 (API versioning, schema, transport), DEC-0079 (package layout and UI reuse), DEC-0080 (React Native approach). All Accepted on 2026-10-31.
- Related Plan: PLAN-0002

## Summary

- Third-party apps can put Superstep chat in front of **their own signed-in users** and keep anonymous visitor chat:
  - the third party's backend holds a server credential for one published chat and mints short-lived signed user tokens; no PAT and no long-lived secret ever reaches a browser or a phone;
  - sessions and history are scoped per external user.
- A **stable, versioned public Chat API** (HTTP plus a formally specified WebSocket event stream) in the public OpenAPI, documented in the handbook in English and Vietnamese.
- **Headless chat** in `@superstep/sdk` (TypeScript: browsers, Node, React Native) and the Python `superstep` package.
- A **web UI toolkit** `@superstep/react` (hook plus components) extracted from the studio's own chat UI, and a **widget JS API** (`window.Superstep`) with theming and signed-in embeds.
- **React Native** support (`@superstep/react-native`) and a **native WebView guide** with a token bridge for iOS and Android.

## Problem Or Opportunity

- Today the only ways to embed chat are the `/c/{slug}` page, its `?embed=1` iframe and `widget.js` (three data attributes, no JS API, no events, no theming).
- The chat HTTP API exists (`backend/app/api/routes/public_chat.py`) but is only in the internal `/openapi.json`; the WebSocket message format has no formal schema; the handbook `reference/api.md` lists chat endpoints without attachments and ratings.
- The public socket `/ws/public/chat/{slug}` accepts only same-origin connections (`_same_origin` in `api/deps.py`), so a third-party page or a mobile app cannot talk to it directly.
- `signed_in` access means "any account of this studio"; a third party cannot vouch for its own users, so its signed-in users chat as anonymous visitors (no history across devices, no identity for the workflow).
- `@superstep/sdk` 0.1.0 and the Python `superstep` package only start workflow runs with a workflow token; there is no chat in either.
- The chat UI lives in `frontend/src/components/chat/*` and cannot be reused outside the studio.

## Scope

### In Scope

- **Phase 1, public Chat API** (DEC-0077, DEC-0078):
  - versioned paths `/api/public/v1/chat/{slug}/...` and `/ws/public/v1/chat/{slug}`; the current unversioned paths stay as aliases of v1;
  - every chat endpoint (page, logo, sessions list/create/get, attachments upload/download/delete, ratings put/delete) in `/openapi.public.json`;
  - a formal schema of the socket messages (client and server) published as JSON Schema and an AsyncAPI document, with contract tests;
  - per-chat **app keys** (server credentials) with rotation and revocation, and short-lived **user tokens** (JWT, HS256) signed by the third party's backend, carrying an external user id and an optional name;
  - a new chat access option for third-party users, CORS and origin rules for the token flows, rate limits per external user;
  - handbook pages en and vi: Chat API reference, third-party auth guide, compatibility and deprecation policy.
- **Phase 2, headless SDKs** (DEC-0078, DEC-0079): `chat.start`, `chat.list`, `chat.get`, `chat.send` with streaming (async iterator), answer a Human node (text and form), attachments, ratings; auth helpers (server-side mint in Node and Python; client-side token refresh callback). Works in browsers, Node 18+ and React Native.
- **Phase 3, web toolkit** (DEC-0079): `@superstep/react` with `useChat` and components (`Chat`, `MessageList`, `Composer`, ...), themable with CSS variables; the studio consumes the same package (no duplicate chat UI). Widget JS API `window.Superstep` (`open`, `close`, `toggle`, `identify(token)`, `logout`, `on(event)`), theming (color, logo, language) and signed-in embeds via token.
- **Phase 4, mobile** (DEC-0080): `@superstep/react-native` with `useChat` and basic native components; a native iOS and Android WebView guide with a token bridge.
- Examples (a sample third-party host app for web, an Expo app), an e2e strategy with the sample host in CI, npm and PyPI publishing through the existing `sdk-publish.yml`.

### Later (backlog)

The full list with reasons and triggers is in PLAN-0002 "Deferred / later".

- Edit a sent message (fork the conversation from that turn).
- Regenerate an answer.
- Native Swift and Kotlin SDKs.
- An SSE transport (only if a real client cannot use WebSocket; DEC-0078).

### Out Of Scope

- PATs or workflow tokens in clients.
- Third-party identity federation (OIDC login against the third party's IdP) inside Superstep; the third party's backend vouches for its users instead.
- Changes to the studio's own builder chat behaviour beyond the UI extraction.

## Stakeholders Or Users

- Third-party web and mobile developers who embed a Superstep chat.
- Their end users (signed in or anonymous).
- Workflow owners who publish chats and manage app keys.
- The operator who runs the studio.

## Current Context

- Verified on `develop` at v0.10.2 on 2026-10-31:
  - `/c/{slug}` with `access` `anonymous` or `signed_in` (DEC-0067, REQ-0074); `?embed=1` limited by `embed_origins` through `frame-ancestors` (`/api/public/chat-frame`).
  - `frontend/src/widget/widget.ts`: `data-slug`, `data-position`, `data-open` only.
  - `public_chat.py`: `GET /api/public/chat/{slug}`, `/logo`, `GET`/`POST .../sessions`, `GET .../sessions/{sid}`, attachments `POST`/`GET`/`DELETE`, ratings `PUT`/`DELETE` on `.../turns/{tid}/rating`.
  - WebSocket `/ws/public/chat/{slug}`: same origin only; one message or answer per connection (`{chat_session_id, message}` or `{chat_session_id, response}`), streams `public_event`s (`node_token`, steps, question, `run_summary`, errors), `{"type": "cancel"}` cancels.
  - Visitor identity: an HMAC token `<id>.<sig>` bound to the slug, in an HttpOnly cookie or `X-Chat-Visitor` (`new` issues one); `?visitor=` on the socket.
  - Limits: per-IP read and message limits (`public_chat_rate_*`) and a per-chat `daily_limit`.
  - `ChatSession` has `channel` (studio, web, embed), `owner` (studio user) and `visitor`.
  - `backend/app/api/openapi_public.py` builds `/openapi.public.json` from the hooks router only.
  - `sdk/typescript` (`@superstep/sdk` 0.1.0) and `sdk/python` (`superstep`): `run`, `getRun`, `wait`, `runAndWait`. Published by `.github/workflows/sdk-publish.yml` on `sdk-ts-v*` and `sdk-py-v*` tags.
  - No edit or regenerate of messages.

## Desired Behavior

1. A shop's backend stores an app key for the chat `help`. When a customer signs in, the backend calls `mintChatToken({ keyId, secret, slug: "help", userId: "cust_42", name: "Lan", ttl: 600 })` and returns the token to its web page.
2. The page renders `<Chat slug="help" baseUrl="https://studio.example.com" getToken={fetchToken} />`. The customer sees only their own past chats, from any device; the workflow sees `external_user = cust_42` and the name.
3. The token expires while the page is open; the SDK calls `getToken` again and retries once, without the user noticing.
4. The owner rotates the app key: the old and new secrets are both valid until the old one is revoked; revoking it makes new tokens signed by it fail with `CHAT_TOKEN_INVALID` at once.
5. A plain website drops `widget.js`, then calls `window.Superstep.identify(token)` after its own login; the widget switches from anonymous to that user and `window.Superstep.on("message", ...)` reports new answers.
6. A React Native app uses `useChat` from `@superstep/react-native` with the same token callback; an iOS app opens `/c/help?embed=1` in a WKWebView and passes the token through the bridge.

## Business Rules

- No long-lived secret in a client. App key secrets are shown once, stored hashed or encrypted, and only used server-side to sign user tokens.
- A user token is valid only for its chat (audience = slug), for at most 1 hour (default 10 minutes), and only while its app key is active.
- A session created with a user token belongs to `(chat, app key's app, external user id)`; other users and anonymous visitors never see it.
- Anonymous visitor chat keeps working unchanged when the chat allows it.
- Every error uses the common envelope with English codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- A public API version is supported for at least 12 months after its successor ships; breaking changes need a new version (DEC-0078).

## Constraints

- DEC-0009 layers; Alembic revision for new tables or columns; no heavy new backend dependency (JWT HS256 verification with the standard library or the existing dependency set; DEC-0077).
- The SDK packages keep zero runtime dependencies where possible (the TypeScript SDK has none today).
- English artifacts; en and vi docs; no emoji.

## Acceptance Criteria

- `/openapi.public.json` lists every v1 chat endpoint with schemas; the socket schema validates every event the server sends in the backend test suite.
- A third-party token for user A cannot read, rate or attach to a session of user B or of an anonymous visitor (403/404), proven by tests.
- An expired, wrong-audience, revoked-key or bad-signature token is rejected with a specific code; rotation keeps both secrets valid until revocation.
- The sample host app e2e in CI: mint on its server, chat from its page through `@superstep/react`, then through `widget.js` with `identify`, with streaming and a Human answer.
- The studio's chat pages use `@superstep/react` components, and the existing chat e2e and screenshots pass unchanged.
- A React Native example passes unit tests with a mocked socket; the WebView bridge is covered by a browser e2e.

## Edge Cases

- Clock skew between the third party and the studio: 60 s leeway on `exp`, `nbf`, `iat`.
- A token whose user name changes: the latest name is stored on the next session start.
- The same external user id under two app keys of the same chat: same user when both keys belong to the same chat (the key only proves the issuer).
- A chat switched from `app` access back to `anonymous`: existing external-user sessions stay readable by token holders only if the access still includes `app` (otherwise `CHAT_NOT_FOUND` as today).
- Long streaming answers when a token expires mid-stream: the socket is authenticated at open; expiry does not cut a running stream.

## Clarifications

The owner decided on 2026-10-31 (final):

1. Support chat for third-party apps' signed-in users: the third party's backend issues tokens for its users; no PAT in clients. Anonymous visitor chat stays.
2. Mobile: React Native first; native iOS and Android through a WebView of `/c/{slug}` with a guide and a token bridge. Native Swift and Kotlin SDKs are out of scope for now.

The owner approved PR #271 on 2026-10-31 with all 11 recommendations of PLAN-0002 ("Duyệt plan #271 theo đề xuất cả 11 câu, merge và bắt đầu code giai đoạn 1"):

1. Third-party user tokens: per-chat app keys with HS256 tokens signed by the third party's backend now; public/private key pairs (asymmetric signing) later (DEC-0077).
2. No Superstep-issued token (token exchange) endpoint now; add it later only if a third party asks (DEC-0077).
3. Token lifetime: 10 minutes by default, 1 hour maximum (DEC-0077).
4. An empty allowed-origins list on an app key means any origin (for native apps), with a warning in the settings screen (DEC-0077).
5. Tokens may carry extra user attributes (`meta`), at most 1 KB, always treated as untrusted input (DEC-0077).
6. In v1 the stream event `node_token` is renamed to `token`, and one message is sent per socket connection (DEC-0078).
7. No SSE transport for now (DEC-0078).
8. Headless chat lives inside `@superstep/sdk` under the `/chat` subpath (DEC-0079).
9. The repository moves to npm workspaces so the studio consumes `@superstep/react` (DEC-0079).
10. `@superstep/react-native` is a separate package; no device e2e in CI, manual simulator screenshots instead (DEC-0080).
11. Release grouping: phases 1 and 2 ship as 0.11.0, phases 3 and 4 as 0.12.0.

The owner also asked to keep notes of the work deferred to later ("Nhớ note các thứ sẽ làm sau lại nhé"); the list, with reasons and triggers, is in PLAN-0002 "Deferred / later".

## Open Questions

- None. All 11 open questions of PLAN-0002 were resolved on 2026-10-31 (see Clarifications).

## Planned Tasks

Proposed on 2026-10-31 in PLAN-0002 (approved on 2026-10-31; phase 1 in todo, the rest in backlog):

- Phase 1: TASK-0215 to TASK-0219.
- Phase 2: TASK-0220 to TASK-0222.
- Phase 3: TASK-0223 to TASK-0226.
- Phase 4: TASK-0227 to TASK-0228.
- Backlog: TASK-0229 (edit message), TASK-0230 (regenerate answer).

## Related Artifacts

- `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- `.factory-state/decisions/DEC-0077-chat-third-party-auth.md`, `DEC-0078-public-chat-api-versioning.md`, `DEC-0079-chat-packages-ui-reuse.md`, `DEC-0080-chat-react-native.md`
- `.factory-state/artifacts/REQ-0074-public-chat-page.md`, `.factory-state/decisions/DEC-0067-public-chat-page.md`
