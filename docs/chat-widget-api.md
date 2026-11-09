# Chat widget JavaScript API

The API is part of the existing classic script. No npm installation is required. Publish the chat and add your website's exact origin to **embed origins** first.

```html
<script>
  window.Superstep = { q: [
    ['init', { slug: 'support', open: true, language: 'vi', position: 'right' }],
    ['on', 'ready', function (event) { console.log(event.slug) }]
  ] }
</script>
<script src="https://studio.example.com/c/widget.js" async></script>
```

An array of command tuples also works: `window.Superstep = [['init', { slug: 'support' }]]`. Register handlers before the event you need. The queue runs once, in order, when the script loads. Loading the script again reuses the installed API. Queue at most 100 commands; subsequent calls use the live API.

The original `<script src="…/c/widget.js" data-slug="support" async></script>` remains valid. Supported attributes are `data-open="true"`, `data-language="en|vi"` (`data-lang` alias), `data-position="left|right"`, `data-color` and `data-logo`. Attribute options initialize before queued commands.

## Methods and options

| Method | Behavior |
| --- | --- |
| `init({ slug, baseUrl?, open?, color?, logo?, language?, position? })` | Create the widget, or update appearance without replacing its conversation. `baseUrl` defaults to the script's origin and must be an HTTP(S) origin. Changing slug/baseUrl clears app identity. |
| `open()`, `close()`, `toggle()` | Control the panel. The bubble remains available with a localized accessible label. |
| `identify(tokenOrGetToken)` | Switch to a third-party user. Accept a short-lived JWT string or a function returning a JWT/promise. Resolve after that identity's history loads; reject with a safe `{ code }` error. |
| `logout()` | Remove app identity, cancel previous work and restore this host's anonymous history when anonymous access is enabled. Resolve after history loads. |
| `on(event, handler)` | Subscribe and return an unsubscribe function. |
| `off(event, handler)` | Remove that subscription. |

`slug` is required. `language` is `en` or `vi`; `position` is `left` or `right`. `color` is a CSS color usable inside the iframe as well as on the host. Host CSS variables do not cross an iframe. `logo` accepts HTTP(S) image URLs or PNG/JPEG/WebP base64 data URLs (up to 350,000 characters). Empty color/logo values restore the defaults. Invalid appearance options are ignored. Images still follow the site's content security policy.

Call identity methods again whenever the signed-in person changes. Reuse a provider for token refresh within one identity:

```js
await window.Superstep.identify(async function () {
  const response = await fetch('/my-chat-token', { credentials: 'same-origin' })
  if (!response.ok) throw new Error('Token request failed')
  return (await response.json()).token
})
// At application logout:
await window.Superstep.logout()
```

`/my-chat-token` belongs to **your backend**. It authenticates the current person and signs a bounded-lifetime user token with the app key secret. Never ship that secret in HTML, browser code or a public token endpoint. See the existing [third-party token contract](../handbook/docs/en/run/chat-third-party-auth.md) and [server-side host example](../examples/chat-host/README.md). The SDK requests tokens for operations and refreshes an expired credential once; callbacks should return the current token. Pending providers/history loads from an earlier identity cannot restore its messages after logout or a user switch. Provider/bridge waits time out after 10 seconds with `HTTP_ERROR`.

For widgets, API and WebSocket requests run **inside the Studio iframe**. An app key with restricted origins must allow the **Studio origin**, for example `https://studio.example.com`. The separate chat `embed_origins` list allows the **parent website**, for example `https://shop.example.com`. Allowing only the parent on an app key does not allow the iframe's requests. Direct SDK clients instead allow their own application's origin. Empty key origins retain the existing unrestricted/native policy.

Same-origin browser GETs may omit `Origin`: the API accepts their referrer origin only when Fetch Metadata says `same-origin` and that referrer matches the API's own origin or configured public URL. Foreign referrers, cross-site requests and absent metadata do not supply an origin for a restricted key. Explicit Origin headers retain precedence. Configure `STUDIO_PUBLIC_URL` correctly behind a reverse proxy.

## Events

| Event | Safe payload |
| --- | --- |
| `ready` | `{ slug }`, after initial history load and each successful identity change. |
| `open`, `close` | `{ slug }`, when panel visibility changes through the API or bubble. Initial `init({open:true})` sets visibility without emitting `open`. |
| `message`, `answer` | `{ slug, sessionId, turn: { id, role, text, status? } }` for newly persisted user/assistant turns after a completed send/Human answer. Restored history is never replayed. |
| `error` | `{ slug, code }`, including transport or identity initialization failures. |

Handlers receive only these fields. There are no JWTs, provider callbacks, app secrets, raw socket frames, attachment credentials or user metadata in public payloads. Identity promises also reject; catch them in your application. A throwing handler cannot break another subscriber. Tokens never enter the frame URL or browser storage. Only the anonymous visitor HMAC is saved, under `superstep-chat:<slug>`; blocked storage limits persistence to the current page.

## Iframe API and trust boundary

`/c/<slug>?embed=1` exposes the same `window.Superstep` methods **inside** the frame for a future native bridge. In that context the page is already displayed; open/close/toggle signal visibility events to the integrating wrapper. `init` may update appearance for the current slug. Native code may call `identify` with a token/provider and await the history acknowledgement.

A website parent must use `widget.js` for the checked bridge. The private protocol validates the exact parent/frame WindowProxy, the configured parent origin, a fresh document channel and an identity epoch. Sensitive replies always target an exact origin. The initial public ready handshake contains a document nonce only. Foreign windows/origins and stale channels/epochs are ignored. Do not implement an unvalidated wildcard token bridge or put tokens in URL parameters. Platform wrapper guides and a broader handbook refresh are not part of this page.
