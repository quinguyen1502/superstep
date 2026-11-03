# Third-party chat authentication

Let people signed in to your application chat under their own identity.
Your backend signs a short-lived user JWT with a per-chat app key; the
browser or mobile app receives only that JWT. Superstep verifies it locally.
No token-exchange endpoint is needed.

## Set up an app key

1. Save the workflow and enable **Chat** in its settings. Enable the access
   option for third-party app users (`app`) and choose the published slug.
   You can also allow `anonymous` or `signed_in` studio users.
2. As the workflow owner or an admin, create an app key in Chat settings.
   Give it a label and, for web apps, explicit allowed origins such as
   `https://shop.example.com` (scheme, host and optional port; no path).
3. Copy `key_id` and the one-time `secret` into your backend's secret manager.
   Listing keys shows metadata, never the secret. If lost, create another key.
4. In your backend, authenticate the person with your own login system, then
   derive a stable user id and sign a token for that person. Return only the
   user JWT from a private endpoint protected by your application's session,
   with `Cache-Control: no-store`.
5. Send the JWT using the [Chat API](chat-api.md). For browser requests use
   `credentials:'omit'`; sockets send an `auth` frame before the message.

The owner/admin management endpoints are separate from the public Chat API:

```text
GET    /api/workflows/{wid}/chat/app-keys
POST   /api/workflows/{wid}/chat/app-keys
DELETE /api/workflows/{wid}/chat/app-keys/{key_id}
```

Create body: `{"label":"Shop backend","origins":["https://shop.example.com"]}`.
The creation response's `data.secret` is shown once. Revoking in the UI
requires typing the item's displayed name; the DELETE API has no confirm
field. Creation and revocation are audited.

## Token contract

The header is `{"alg":"HS256","typ":"JWT","kid":"<key_id>"}`. The
signature is HMAC-SHA256 over `base64url(header).base64url(claims)`, using
the **UTF-8 bytes of the secret exactly as shown**. Do not base64-decode the
secret. Encode all JWT segments as base64url without `=` padding.

| Claim | Value |
| --- | --- |
| `iss` | The app's `key_id`, identical to header `kid` |
| `aud` | Exactly `superstep-chat:<slug>` |
| `sub` | Stable external user id, 1–128 characters, always a string |
| `name` | Optional display name, at most 80 characters |
| `iat` | Issued-at Unix seconds, numeric |
| `exp` | Expiry Unix seconds; later than `iat`, no more than 3,600 seconds after it |
| `nbf` | Optional not-before Unix seconds |
| `jti` | Optional identifier; there is no per-token denylist in this version |
| `meta` | Optional JSON object, at most 1,024 bytes when compact UTF-8 encoded; untrusted workflow input |

The examples issue 10-minute tokens. Keep clocks synchronized: verification
allows 60 seconds of skew for `iat`, `exp` and `nbf`. Only HS256 is accepted;
`none`, other algorithms, unknown keys, wrong audiences and bad signatures
are rejected. The entire token is at most 8,192 characters. Optional metadata
must fit both its own limit and that token limit.

## Mint on your server

These standard-library examples are standalone helpers. The SDK source also
provides `mintChatToken` from `@superstep/sdk/server` and Python `mint_chat_token`;
use a compatible approved package version or the built checkout. Call a helper
on your server using a key/secret from secret storage and `sub`/name from your
**authenticated** application user. Never
accept an arbitrary user id supplied by the browser as the identity to sign.
Each helper returns a token; your private HTTP handler returns it to that
user. Keep secrets and returned tokens out of logs.

=== "Node.js (18+)"

    ```javascript
    --8<-- "handbook/snippets/chat/mint-token.mjs"
    ```

=== "Python (3.9+)"

    ```python
    --8<-- "handbook/snippets/chat/mint-token.py"
    ```

=== "Go (1.18+)"

    ```go
    --8<-- "handbook/snippets/chat/mint-token.go"
    ```

=== "PHP"

    ```php
    --8<-- "handbook/snippets/chat/mint-token.php"
    ```

For example, the Node helper's arguments are
`{keyId, secret, slug:'support', userId:currentUser.id, name:currentUser.name}`.
Keep ids stable across devices and name changes. All keys of one chat share
the same external-user namespace: the same `sub` has the same history through
either rotation key. Include a tenant prefix in `sub` if your application
needs to separate otherwise identical customer ids.

## Transport, origins and refresh

HTTP sends `Authorization: Bearer <jwt>`. For WebSocket v1, wait for `ready`,
then send `{"type":"auth","token":"<jwt>"}` before one `message` or
`answer`. `?token=` is a compatibility fallback; prefer the frame because
URLs may reach proxy logs. Never put the app **secret** in a URL or client.

For cross-origin browser HTTP, the preflight must request Authorization;
the actual request's signed token and origin are checked against the key.
CORS never allows credentials. Cross-origin sockets also need a valid app
token and an allowed Origin; the legacy socket stays same-origin.

An empty key origins list allows any origin, including a native/server
client with no Origin. A nonempty list requires a matching Origin and
rejects a request that has none. Use explicit origins for web-only keys.
These origins govern direct API/socket callers; the separate chat
`embed_origins` setting governs which sites may frame `/c/{slug}`.

Fetch a fresh JWT before its expiry or when `CHAT_TOKEN_EXPIRED` is returned,
using your private authenticated endpoint. Retry authentication once with
the fresh token; avoid an unbounded retry loop. The socket verifies the
token before its operation and does not cut a running stream when it expires.
A new connection or HTTP request verifies again. After an interrupted stream,
recover history before sending the message again.

The [widget API](chat-widget.md) supports `identify` through a checked parent/frame
bridge. Its app-key origin is the Studio iframe origin; `embed_origins` separately
allows the parent website. Direct [React toolkit](chat-react.md) and headless SDK
clients instead allow their own application origin.

## Workflow identity and history

Declare a state field named `chat` with type **object** in the workflow to
retain the injected input. A new app-user message provides:

```json
{"chat":{"user":{"id":"cust_42","name":"Lan","kind":"app"},"meta":{"plan":"standard"}}}
```

For example `{{state.chat.user.name}}` reads the display name. Both name and
metadata are untrusted data: do not turn them into system instructions or
authorization decisions. Runs still use the workflow owner's credentials.
Human answers resume the existing run; they do not create a new message input.

History, files and ratings are scoped by `(chat, external user id)`, not by
the device or active key id. Other app users, anonymous visitors and studio
users cannot access that history through public session endpoints. A valid
app token takes priority over an anonymous cookie; it does not convert or
merge anonymous history. Changing `sub` changes the user's history scope.

## Rotate and revoke

Up to **two active keys per chat** allow rotation without a gap:

1. Create a second key with the intended origins; store its secret securely.
2. Deploy your token issuer to sign using its new `kid` and secret.
3. Let clients refresh; both active keys work for the same user history.
4. Revoke the old key in Chat settings. Revoke immediately on a suspected leak.

Keys are checked on every verification without a cache; revocation rejects
the next verification. An already authenticated stream is not reauthenticated
mid-run. Disable Chat or remove `app` access to reject all app-user operations.
There is no individual-token revoke endpoint; use short lifetimes, or revoke
the key when necessary.

## Errors and limits

| HTTP | Code | Action |
| --- | --- | --- |
| 401 | `CHAT_TOKEN_REQUIRED` | Supply an app token for the requested access/origin |
| 401 | `CHAT_TOKEN_INVALID` | Check signing configuration, audience, identity and clock; do not blindly retry |
| 401 | `CHAT_TOKEN_EXPIRED` | Refresh using your authenticated backend |
| 401 | `CHAT_APP_KEY_REVOKED` | Switch to an active key; investigate unexpected revocation |
| 403 | `CHAT_ORIGIN_FORBIDDEN` | Correct the allowed origins or caller origin |
| 404 | `CHAT_NOT_PUBLISHED` | Chat disabled, unpublished or unavailable |
| 404 | `CHAT_SESSION_NOT_FOUND` | Unknown session or it belongs to another identity |
| 429 | `RATE_LIMITED` | Back off using `Retry-After` or socket `error.details.retry_after` |

Cross-origin browsers can read an expired/revoked error only after signature
and origin validation. Other rejected credentials/origins can appear as a
CORS network failure; inspect server-side status/code without logging the JWT.

Per-IP read/message limits and the chat daily cap remain. The external-user
message limit is `STUDIO_PUBLIC_CHAT_RATE_USER`, defaulting to the IP message
limit (30 per 60 seconds by default). Uploads consume this quota; failed token
verifications count against the IP message limit. See
[Configuration](../reference/configuration.md) and [Error codes](../reference/errors.md).

## Security checklist

- Keep app secrets in backend secret storage; never ship them, PATs or
  workflow tokens in browser/mobile bundles, screenshots, URLs or logs.
- Protect your mint endpoint with your application's authentication and
  CSRF controls; derive identity server-side and return `Cache-Control: no-store`.
- Use HTTPS/WSS, short lifetimes and explicit web origins. Hold user JWTs in
  memory where practical; clear them on logout and avoid shared caches.
- Rotate keys, audit unexpected use, and revoke a leaked secret promptly.
  A leaked key can impersonate any user of that chat until revoked.
- Treat `name`/`meta` as untrusted data and apply the chat's spending limits.
- Use stable, tenant-scoped user ids; changing keys alone does not split history.


Continue with the [React toolkit](chat-react.md) or [Widget API](chat-widget.md). The widget guide explains why its app key allows the Studio iframe origin, separately from the parent embed allowlist.
