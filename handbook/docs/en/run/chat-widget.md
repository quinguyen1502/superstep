# Chat widget

Add a bubble to an existing website with `widget.js`. It loads the published
chat in a Studio iframe; the script does not add React to your host page.
For a chat rendered directly by your React application, see
[React chat toolkit](chat-react.md).

## Publish and allow the website

Publish the Chat page, enable anonymous and/or third-party (`app`) access, and
add the website's exact origin under **Sites that may embed this chat**.
For example, allow `https://shop.example.com`; localhost HTTP origins are also
accepted for development. Other origins cannot frame the page.

```html
<script src="https://studio.example.com/c/widget.js"
  data-slug="support" data-language="en" data-position="right" async></script>
```

The original `data-slug` snippet remains valid. The bubble keeps the anonymous
visitor HMAC on your website, under `superstep-chat:<slug>`. Other scripts on
that website can access that identity, so embed it on sites you trust.
Blocked storage limits persistence to the current page. A plain iframe instead
uses its own browser-partitioned storage, which can be cleared by the browser.

## Queue calls before the script loads

```html
<script>
  window.Superstep = { q: [
    ['init', { slug: 'support', open: true, language: 'en', position: 'right' }],
    ['on', 'ready', function (event) { console.log(event.slug) }]
  ] }
</script>
<script src="https://studio.example.com/c/widget.js" async></script>
```

An array of tuples also works: `window.Superstep = [['init', { slug: 'support' }]]`.
The queue runs once in order; register handlers before the event you need.
Use at most 100 queued commands, then the live API. Repeated script loads reuse
the installed API. Data attributes initialize before queued commands.
For an inline queue, apply your site's CSP nonce/hash policy as usual.

## Sign in your own users

Your backend signs a short-lived JWT from its authenticated session. The app
secret stays on the server. See [Third-party authentication](chat-third-party-auth.md)
for claims, signing helpers, rotation and errors.

There are two separate origin settings:

| Setting | Example for this widget | Purpose |
| --- | --- | --- |
| Chat `embed_origins` | `https://shop.example.com` | Allow the parent website to frame the chat and use the checked bridge |
| App key allowed origins | `https://studio.example.com` | Allow HTTP/socket requests made inside the Studio iframe |

A key allowing only the parent website refuses the iframe's requests. Direct
React/headless clients instead allow their own application's origin. Empty key
origins retain the unrestricted/native policy. Same-origin GETs that omit
`Origin` need same-origin Fetch Metadata and an own-origin referrer; configure
`STUDIO_PUBLIC_URL` correctly behind a proxy and preserve that request metadata.

After the live API is installed and your host login succeeds:

```js
await window.Superstep.identify(async function () {
  const response = await fetch('/api/auth/chat-token', {
    method: 'POST', credentials: 'same-origin',
  })
  const body = await response.json()
  if (!response.ok || !body.success) throw new Error('Token request failed')
  return body.data.token
})

// On host logout, clear the widget's app identity too:
await window.Superstep.logout()
```

The sample endpoint uses an envelope; adapt the return expression for your own
endpoint. It must authenticate and protect the mint request, derive user identity
server-side and return `Cache-Control: no-store`. Never put a secret, PAT or
workflow token in HTML, a Vite variable, browser storage or a public token endpoint.

`identify` accepts a JWT string or a function returning a JWT/promise. Prefer
a provider so the SDK can obtain fresh credentials and retry an expired token
once. Call `identify` again whenever the signed-in person changes. Its promise
resolves after that person's history loads, and rejects with a safe `code` on
failure. `logout` cancels the previous identity and restores this host's anonymous
history when anonymous access is enabled. Pending providers cannot restore the
previous user's messages after logout/switch. Provider/bridge waits time out after
10 seconds with `HTTP_ERROR`; catch identity promises in your application.
JWTs and callbacks stay in memory and never enter URLs, storage or public event
metadata. The private bridge validates origin, exact window, document channel
and identity epoch; do not send tokens with your own wildcard postMessage bridge.

## API and appearance

| API | Result |
| --- | --- |
| `init(options)` | Create or update the widget; changing slug/baseUrl clears app identity |
| `open()`, `close()`, `toggle()` | Control the panel; the bubble remains available |
| `identify(tokenOrGetToken)` | Switch to an app user and await history |
| `logout()` | Clear app identity and await anonymous history |
| `on(event, handler)` | Subscribe; returns an unsubscribe function |
| `off(event, handler)` | Remove that subscription |

`init` requires `slug`. `baseUrl` defaults to the script's HTTP(S) origin.
Options and data attributes are:

| Option | Attribute | Values |
| --- | --- | --- |
| `open` | `data-open` | `true` starts open |
| `language` | `data-language` (`data-lang` alias) | `en`, `vi`; otherwise browser language |
| `position` | `data-position` | `left`, `right` |
| `color` | `data-color` | A CSS color usable in the iframe and host |
| `logo` | `data-logo` | HTTP(S) image URL or PNG/JPEG/WebP base64 data URL, up to 350,000 characters |

Appearance changes keep the current chat. Empty color/logo values restore
defaults; invalid appearance values are ignored. Unlike the React provider,
a host CSS variable does not cross the iframe: pass a concrete color. The
iframe follows the browser's light/dark preference. Image/script/frame/style
loading must be allowed by your host's CSP; the bubble uses scoped inline styles.

## Events

| Event | Payload and timing |
| --- | --- |
| `ready` | `{ slug }` after history initialization and successful identity changes |
| `open`, `close` | `{ slug }` when visibility changes; initial `init({open:true})` sets visibility without an event |
| `message`, `answer` | `{ slug, sessionId, turn: { id, role, text, status? } }` for new persisted user/assistant turns after a send or Human answer |
| `error` | `{ slug, code }` on transport/identity initialization failures |

Restored history does not replay new-turn events. Payloads exclude auth frames,
user metadata and attachment credentials. A throwing subscriber cannot break
another handler. Example:

```js
const unsubscribe = window.Superstep.on('answer', function (event) {
  console.log(event.sessionId, event.turn.id)
})
// Later:
unsubscribe()
```

## Try the sample host

Run `scripts/chat_host_e2e.sh` from the repository root. The shared loopback
server serves `/` (headless SDK), `/react/` and `/widget.html`. The widget page
reuses the demo portal's host controls and opaque login session; its bubble and
iframe come from the built Studio's `widget.js`. Replace the demo sign-in stub
before deploying your own application. Package publication is separately approved.

The e2e job covers anonymous chat, server-issued tokens, two users/history,
Human answers, streaming events and logout restoring the guest identity. The
headless terminal revocation case runs last on a fresh fixture. It also checks
origin refusals, files and ratings. Screenshots en/vi/light/dark remain temporary
CI artifacts. The `/c/<slug>?embed=1` page exposes the API inside its frame for
future native wrappers; platform-specific guides remain separate work.


## Edit a sent message

Message actions reuse the shared [editing flow](chat.md#edit-a-sent-message): confirm a fresh execution in an independent conversation branch, keep the original, and use the source link to return. Human replies are not editable roots. For custom interfaces, `useChat().edit(turnId, text, operationId)` requires the same explicit rerun confirmation; retain the operation ID when recovering an interrupted attempt. See the [API contract](chat-api.md#prepare-and-execute-an-edit) for admission and recovery.


Regeneration uses the same confirmed revision flow: **Regenerate answer** on the latest terminal answer opens an independent branch and asks Human/reviewer questions again. `useChat().regenerate(answerId, operationId?)` returns the normal chat result. See [chat usage](chat.md#regenerate-the-latest-answer) and [API admission/recovery](chat-api.md#prepare-regeneration).
