# Cross-origin chat host

A local third-party host using the built `@superstep/sdk` headless client/store
and `@superstep/sdk/server` signer, the React toolkit and the programmable widget.
Headless/React pages call Superstep on a different origin; the widget calls it from
its Studio iframe. The Node server holds the app-key secret and derives the
signed user ID from its own opaque HttpOnly session.

This is an opt-in, loopback-only **demonstration**, not an account system. Its
two sign-in personas are fixed sample users. Replace that stub with your own
authenticated session before adapting it to a deployed application. No real
customer/provider data or package publication is part of this example.

## Pages and shared authentication

| Page | Integration |
| --- | --- |
| `/` | Headless SDK and host-owned chat controls |
| `/react/` | Built `examples/react-chat`: `<Chat>` and custom composition |
| `/widget.html` | Portal controls plus Studio's plain-JS bubble/iframe, `identify`, events and logout |

All three use one opaque HttpOnly host session and protected `/api/auth/chat-token` endpoint. The widget
sample's portal shell reuses the existing React/shadcn host controls; `widget.js` itself does not bundle React
or require a React host. Plain HTML integration is in the [en widget guide](../../handbook/docs/en/run/chat-widget.md)
and [vi widget guide](../../handbook/docs/vi/run/chat-widget.md). React guides: [en](../../handbook/docs/en/run/chat-react.md) / [vi](../../handbook/docs/vi/run/chat-react.md).

## Run the complete acceptance example

From the repository root, with Node 22 and the backend Python environment:

```sh
npm ci
node node_modules/@playwright/test/cli.js install chromium
scripts/chat_host_e2e.sh
```

On a Mac with an existing Chrome:

```sh
PW_CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' scripts/chat_host_e2e.sh
```

The script builds SDK/toolkit, Studio and both sample bundles, runs the Node session/security tests, starts
a temporary mock backend serving the built Studio on `127.0.0.1:8131`, creates an origin-restricted chat
and ephemeral app keys, and serves the host on `localhost:5188`. Navigation links open each sample without restarting the host. A second host
on port 5189 proves forbidden-origin behavior. Different hostnames also keep
the demo's host cookie separate from the studio's hostname; HTTP SDK calls
omit credentials independently.

Playwright covers sign-in for two customers, session/history isolation,
streaming frames, a sample Human approval form, upload, rating, restoring the
same customer on a new browser context, HTTP/socket origin refusals and key
revocation with no further turns written. A spare key keeps the allowed-origin
CORS policy active after the actual key is revoked, so the browser can display
the typed refusal. The React and widget suites run before the headless terminal-revocation case. Widget tests also cover guest chat, server-issued identity, a Human answer, events and logout restoring guest history. No request is re-sent after an ambiguous write.

Override `BACKEND_PYTHON`, `CHAT_HOST_API_PORT`, `CHAT_HOST_PORT` and
`CHAT_HOST_SECOND_PORT` to avoid port conflicts. Backend DB/key files and host
sessions are ephemeral. Teardown removes temporary credentials and processes.

## Run the sample against your development studio

Publish a workflow with anonymous and app access, attachments enabled and an optional Human
node to try all three pages and logout back to guest history. Create an app key allowing `http://localhost:5188` for direct SDK/React calls and your Studio origin for iframe calls. Add `http://localhost:5188` to the chat embed origins. `CHAT_STUDIO_URL` must serve the Studio UI, widget, API and socket, not an API-only backend. Inject
`CHAT_KEY_SECRET` through your development secret manager/environment, then run:

```sh
npm run build
node node_modules/typescript/bin/tsc -p examples/chat-host/tsconfig.json
node node_modules/vite/bin/vite.js build --config frontend/vite.chat-host.config.ts
node node_modules/typescript/bin/tsc -p examples/react-chat/tsconfig.json
node node_modules/vite/bin/vite.js build --config examples/react-chat/vite.config.mts

CHAT_HOST_DEMO=1 CHAT_STUDIO_URL='http://127.0.0.1:5173' \
  CHAT_SLUG='your-published-chat' CHAT_KEY_ID='your-key-id' \
  node examples/chat-host/server.mjs
```

Open `http://localhost:5188`. The server never
returns its app-key secret or owner credentials to the page. User tokens last
120 seconds, are not stored by the page, and are obtained through the host's
authenticated, origin-checked endpoint. Cookies are HttpOnly/SameSite=Lax;
host/session/token responses use no-store. Production authentication, TLS,
session persistence/rotation and deployment are intentionally outside this demo.

UI controls reuse the project's shadcn components/theme and shared `api()` /
`errorText` localisation; the sample's own strings are in matching en/vi files.
The headless page demonstrates host-owned form controls passing a JSON answer. The React page uses the public toolkit; the widget uses the shared chat inside its iframe. These are integration examples, not a new Studio form builder.

## Screenshots and release scope

CI job `chat-host-e2e` uploads `chat-host-screenshots` for 14 days, including
en/vi, light/dark, widget, mobile and revoked-key states. Screenshots stay under ignored
`frontend/test-results/chat-host/`, `react-chat/` and `widget-chat/`; link CI artifacts from the PR instead of
adding images to Git. Auth traces are disabled because they capture tokens.

This sample targets Superstep 0.12.0 with matching Python SDK/CLI/server versions,
TypeScript SDK 0.2.0 and React toolkit 0.1.3. The npm packages keep independent
versions. See the [0.12.0 release notes](../../CHANGELOG.md) for the integrated
scope. The WebView token bridge is documented. The React Native package remains
deferred. Release tags and package publication follow the owner-approved release process.

TASK-0227 was resumed by the owner on 2026-11-08. `examples/react-native` calls
this host's `POST /api/auth/chat-token`. That example is not part of the 0.12.0
publication, and starting it does not publish `@superstep/react-native`.
