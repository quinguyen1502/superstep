# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0077
- Status: Accepted on 2026-10-31. The owner approved PR #271 with all 11 recommendations of PLAN-0002 ("Duyệt plan #271 theo đề xuất cả 11 câu, merge và bắt đầu code giai đoạn 1").
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Related Requirements: REQ-0082, REQ-0074
- Related Tasks: TASK-0217, TASK-0218, TASK-0219, TASK-0220, TASK-0221, TASK-0225, TASK-0228
- Related Architecture: DEC-0067 (public chat page), DEC-0071 (CLI, PAT), DEC-0076 (CLI sign-in hardening), DEC-0010 (envelope), DEC-0009 (layers)

## Context

- Owner decision: third-party apps' signed-in users chat with their own identity; the third party's backend issues the tokens; no PAT in clients; anonymous chat stays.
- Today a chat's `access` is `studio`, `anonymous` or `signed_in` (a studio account). Anonymous visitors carry an HMAC token `<id>.<sig>` bound to the slug (cookie or `X-Chat-Visitor`).
- The public socket accepts only same-origin connections, and a cross-site iframe or a mobile app cannot rely on third-party cookies.
- Prior art: Intercom and Zendesk messenger "identity verification" (the host backend signs a JWT or HMAC of the user id with a per-app secret); Stream Chat and Sendbird (the backend mints a JWT with an API secret, the client passes a token provider callback); OAuth 2.0 Token Exchange (RFC 8693); RFC 8725 (JWT best current practices).

## Options

### A. Per-chat app key, JWT signed by the third party (recommended)

- The owner creates an **app key** on a published chat: `key_id` (public, e.g. `ck_...`) and a secret (32 random bytes, shown once). Optional label and allowed origins.
- The third party's backend signs a JWT (HS256) locally, with no call to Superstep:
  - header `{alg: "HS256", typ: "JWT", kid: <key_id>}`;
  - claims `iss` = key_id, `aud` = `superstep-chat:<slug>`, `sub` = external user id (1 to 128 chars), `name` (optional, at most 80 chars), `iat`, `exp` (at most 1 hour after `iat`), optional `jti`, optional `meta` (small JSON object, at most 1 KB, passed to the workflow as untrusted input).
- Superstep verifies: `alg` exactly HS256 (no `none`, no algorithm from the token), `kid` known and active for this chat, signature in constant time, `aud`, `exp` and `iat` with 60 s leeway, lifetime cap.
- Pros: no extra round trip; the pattern developers know from Intercom, Stream and Sendbird; the mint helper is a few lines in any language; works offline of Superstep.
- Cons: the third party holds a symmetric secret (a leak lets anyone impersonate any of its users in that chat until rotation); revoking a single token needs a denylist (short lifetimes instead).

### B. Token-exchange endpoint (server credential to Superstep-issued token)

- The third party's backend calls `POST /api/public/v1/chat/{slug}/tokens` with the app secret and `{user_id, name}`; Superstep returns a short-lived opaque or signed token.
- Pros: Superstep controls issuance (audit, per-user revocation, rate limits at issuance); the secret could be asymmetric.
- Cons: an extra network hop per refresh on the third party's server; Superstep becomes a dependency of the third party's login path; more endpoints to secure.

### C. Asymmetric keys (the third party registers a public key or a JWKS URL; RS256 or EdDSA)

- Pros: Superstep never holds a signing secret; a database leak cannot forge tokens.
- Cons: more setup (key generation, JWKS hosting or upload); a JWKS URL adds outbound fetches (SSRF surface, caching); harder for small users.

### D. Reuse `signed_in` (studio accounts) or PATs

- Rejected by the owner: third-party users are not studio accounts, and a PAT in a client leaks full API access.

## Decision (recommended)

1. **Option A now, with room for C.** App keys are per chat, HS256 JWTs signed by the third party. The verifier is written behind a small `ChatTokenVerifier` port so that EdDSA public keys (option C) can be added later without a client change (`kid` selects the key).
2. **Access model.** A chat's `access` becomes a set rather than one value: `anonymous`, `signed_in` (studio accounts, unchanged) and new `app` (third-party users with a valid token). The stored value stays backward compatible (a single string is read as a one-element set). The page accepts a request if any allowed mode matches; a valid app token wins over the visitor cookie.
3. **Identity and scoping.** `ChatSession` gains `external_user` (text) and `app_key_id` (the key that created it, for audit). Sessions are looked up by `(trigger, external_user)` for app users, by `visitor` for anonymous visitors, by `owner` for studio users; the three never mix. The workflow receives `chat.user = {id, name, kind: "app"}`; `meta` is passed as untrusted input.
4. **Transport of the token.** HTTP: `Authorization: Bearer <jwt>` (no cookie, so no CSRF). Socket: the first client frame is `{"type": "auth", "token": ...}` (not the URL, to keep it out of proxy logs); `?token=` stays accepted for clients that cannot send a first frame. The socket is authenticated at open; expiry does not cut a running stream.
5. **Origins and CORS.** Cross-origin HTTP and WebSocket are allowed only for requests carrying an app token (Bearer) and only from the key's allowed origins (or any origin when the list is empty, for native apps that send no `Origin`). Cookie-based anonymous and studio access stay same-origin or iframe-only. CORS responses never set `Access-Control-Allow-Credentials`.
6. **Lifetime, rotation, revocation.**
   - Token lifetime: default 10 minutes in the helpers, hard maximum 1 hour, 60 s leeway.
   - Up to two active keys per chat at once for rotation; revoking a key rejects its tokens at once (keys are looked up on every request, cached at most 30 s per process).
   - Optional `jti` denylist is not in the MVP (short lifetimes instead).
   - Disabling the chat or removing `app` from its access rejects all app tokens.
7. **Secret storage.** The secret is needed to verify HMAC, so it cannot be hashed: it is stored encrypted with the existing credential encryption (the same mechanism as provider credentials), shown once at creation, never returned again, never logged.
8. **Rate limits.** The existing per-IP limits stay; add a per-external-user message limit (`public_chat_rate_user`, default equal to the per-IP message limit) and keep the per-chat `daily_limit`. Failed token verifications count toward the per-IP limit.
9. **Error codes** (common envelope): `CHAT_TOKEN_REQUIRED`, `CHAT_TOKEN_INVALID`, `CHAT_TOKEN_EXPIRED`, `CHAT_APP_KEY_REVOKED`, `CHAT_ORIGIN_FORBIDDEN`. Responses never say which claim failed beyond these codes.
10. **Who manages keys.** The workflow owner and admins create, rotate and revoke app keys in the chat settings dialog; each action is in the audit log.

## Security Analysis

- **Secret leak** (third party): impersonation of any of its users in that chat only (audience-bound), until revocation. Mitigations: per-chat scope, rotation, revocation that takes effect within 30 s, audit of key use (last used at), the handbook says the secret must live only on a server.
- **Token theft** in the browser (XSS on the host site): the attacker can chat as that user for at most the token lifetime; no access to other chats or to Superstep APIs. Short default lifetime.
- **Algorithm confusion and `none`**: the verifier pins HS256 per key and ignores the header `alg` except to check it equals the pin (RFC 8725 section 3.1).
- **Replay across chats**: `aud` is bound to the slug; `kid` must belong to that chat.
- **CSRF**: app requests use a Bearer header, never cookies; CORS without credentials.
- **Cross-user access**: every session read and write checks `(trigger, external_user)`; tests prove A cannot touch B's sessions, attachments or ratings.
- **Prompt injection via `name` or `meta`**: passed as untrusted data, length-capped, never as instructions.
- **Denial of wallet**: per-user, per-IP and daily limits; failed verifications are rate-limited.
- **Database leak**: secrets are encrypted at rest with the studio key; option C (public keys) removes this risk later.

## Relation To Existing Access

- `signed_in` stays for studio accounts (internal tools); `app` is for third-party users; `anonymous` for anyone. A chat may allow several.
- The PAT and workflow-token APIs are unchanged and stay server-side only.

## Rationale

- Option A matches the owner decision (the third party's backend issues tokens), is the industry pattern for embedded messengers, needs no Superstep call in the third party's login path, and keeps the client contract identical if asymmetric keys are added later.

## Alternatives Considered

- Option B is kept as a possible addition (useful for languages without a JWT library), not needed because the mint helpers are tiny.
- Option C is the planned upgrade if a user asks for it or a security review requires it.

## Impacts

- Alembic revision: `chat_app_keys` table (`id`, `trigger_id`, `key_id`, `secret_enc`, `label`, `origins`, `created_by`, `created_at`, `revoked_at`, `last_used_at`) and `chat_sessions.external_user`, `chat_sessions.app_key_id` with an index on `(trigger_id, external_user)`.
- Chat settings UI, new error codes, handbook guide, SDK helpers.

## Open Questions

1. Should the MVP also ship option B (token exchange)? Recommendation: no; add later if asked.
2. Default token lifetime in the helpers: 10 minutes? Recommendation: yes, maximum 1 hour.
3. Should an empty origin list allow any origin (needed for native apps without an `Origin` header)? Recommendation: yes, with a warning in the UI; web-only apps should set origins.
4. Should `meta` (custom user attributes) be in the MVP? Recommendation: yes, capped at 1 KB and treated as untrusted.

## Approval

- Approved By: pending
- Approved On: pending

## Review Or Revisit Trigger

- A request for asymmetric keys, a key-leak incident, or a need for per-token revocation.
