# React toolkit example

Standalone Vite consumer of the built `@superstep/react` package and prebuilt CSS. No Tailwind plugin, Studio component import or source alias is needed. The left panel uses `<Chat>`; the right panel composes `useChat`, `ChatProvider`, `MessageList`, `QuestionCard` and `Composer` with an independent language/theme and a message override. The host sentinel deliberately uses utility-like class names to detect CSS leakage.

Run from the repository root:

```sh
npm ci
npm run build --workspace=@superstep/react
node node_modules/typescript/bin/tsc -p examples/react-chat/tsconfig.json
node node_modules/vite/bin/vite.js build --config examples/react-chat/vite.config.mts
CHAT_HOST_DEMO=1 CHAT_HOST_DIST="$PWD/examples/react-chat/dist" \
CHAT_STUDIO_URL=http://localhost:8000 CHAT_SLUG=your-chat \
CHAT_KEY_ID=your-key-id CHAT_KEY_SECRET=your-secret \
node examples/chat-host/server.mjs
```

Open http://localhost:5188 and choose Lan or Minh. Add that exact host origin to the chat app key's allowed origins. The shared loopback-only Node host mints short-lived tokens from its HttpOnly demo session; its signing secret never enters browser assets. Replace the sign-in stub with real application authentication before deployment. Change `identityKey` on account switches. Runtime credentials should come from your secret manager/environment, never a committed file or a client-side Vite variable.

`scripts/chat_host_e2e.sh` seeds a temporary backend with fake credentials/mock responses, builds this example and the older headless sample, tests both sequentially on the same allowed origin, then removes its temporary database/processes. Light, dark and custom screenshots are stored under ignored `frontend/test-results/react-chat/` and uploaded as short-lived CI artifacts. No real model service or package publication is involved.
