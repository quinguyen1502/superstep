# Cross-origin chat host

A local third-party host using the built `@superstep/sdk` headless client/store
and `@superstep/sdk/server` signer. Its browser calls Superstep directly on a
different origin. The Node server holds the app-key secret and derives the
signed user ID from its own opaque HttpOnly session.

This is an opt-in, loopback-only **demonstration**, not an account system. Its
two sign-in personas are fixed sample users. Replace that stub with your own
authenticated session before adapting it to a deployed application. No real
customer/provider data or package publication is part of this example.

## Run the complete acceptance example

From the repository root, with Node 22 and the backend Python environment:

```sh
npm ci --prefix frontend
npm ci --prefix sdk/typescript
node frontend/node_modules/@playwright/test/cli.js install chromium
scripts/chat_host_e2e.sh
```

On a Mac with an existing Chrome:

```sh
PW_CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' scripts/chat_host_e2e.sh
```

The script builds the SDK/sample, runs the Node session/security tests, starts
a temporary mock backend on `127.0.0.1:8131`, creates an origin-restricted chat
and ephemeral app keys, and serves the host on `localhost:5188`. A second host
on port 5189 proves forbidden-origin behavior. Different hostnames also keep
the demo's host cookie separate from the studio's hostname; HTTP SDK calls
omit credentials independently.

Playwright covers sign-in for two customers, session/history isolation,
streaming frames, a sample Human approval form, upload, rating, restoring the
same customer on a new browser context, HTTP/socket origin refusals and key
revocation with no further turns written. A spare key keeps the allowed-origin
CORS policy active after the actual key is revoked, so the browser can display
the typed refusal. No request is re-sent after an ambiguous write.

Override `BACKEND_PYTHON`, `CHAT_HOST_API_PORT`, `CHAT_HOST_PORT` and
`CHAT_HOST_SECOND_PORT` to avoid port conflicts. Backend DB/key files and host
sessions are ephemeral. Teardown removes temporary credentials and processes.

## Run the sample against your development studio

Publish a workflow with app access, attachments enabled and an optional Human
node. Create an app key allowed on exactly `http://localhost:5188`. Inject
`CHAT_KEY_SECRET` through your development secret manager/environment, then run:

```sh
npm --prefix sdk/typescript run build
node frontend/node_modules/typescript/bin/tsc -p examples/chat-host/tsconfig.json
node frontend/node_modules/vite/bin/vite.js build --config frontend/vite.chat-host.config.ts

CHAT_HOST_DEMO=1 CHAT_STUDIO_URL='http://127.0.0.1:8000' \
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
The approval form is an example of host-owned controls passing a JSON object,
not a new studio form builder or the future React UI package.

## Screenshots and release scope

CI job `chat-host-e2e` uploads `chat-host-screenshots` for 14 days, including
en/vi, light/dark, mobile and revoked-key states. Screenshots stay under ignored
`frontend/test-results/chat-host/`; link CI artifacts from the PR instead of
adding images to Git. Auth traces are disabled because they capture tokens.

TASK-0220 supplies TypeScript SDK 0.2.0. Python chat keeps the SDK/CLI/server's
shared version (currently 0.10.2); the owner selected a later shared release
rather than the task's obsolete 0.2.0 downgrade. CHANGELOG Unreleased records
both. Release tags/package publication require separate owner approval.
