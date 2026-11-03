# React toolkit example

Standalone Vite consumer of the built `@superstep/react` package and prebuilt CSS. No Tailwind plugin, Studio component import or source alias is needed. The left panel uses `<Chat>`; the right panel composes `useChat`, `ChatProvider`, `MessageList`, `QuestionCard` and `Composer` with an independent language/theme and a message override. The host sentinel deliberately uses utility-like class names to detect CSS leakage.

Run from the repository root:

```sh
npm ci
npm run build
node node_modules/typescript/bin/tsc -p examples/chat-host/tsconfig.json
node node_modules/vite/bin/vite.js build --config frontend/vite.chat-host.config.ts
node node_modules/typescript/bin/tsc -p examples/react-chat/tsconfig.json
node node_modules/vite/bin/vite.js build --config examples/react-chat/vite.config.mts
CHAT_HOST_DEMO=1 CHAT_STUDIO_URL=http://127.0.0.1:5173 CHAT_SLUG=your-chat \
CHAT_KEY_ID=your-key-id CHAT_KEY_SECRET=your-secret \
node examples/chat-host/server.mjs
```

Open http://localhost:5188/react/ and choose Lan or Minh. Navigation also opens headless `/` and `/widget.html` on the same host/session. Allow the exact host origin on the key for direct React calls. For the widget page also allow the Studio origin on the key and the host on the chat's embed origins. Enable anonymous access alongside app access to try guest chat and logout restoration. The shared loopback-only Node host mints short-lived tokens from its HttpOnly demo session; its signing secret never enters browser assets. Replace the sign-in stub with real application authentication before deployment. Change `identityKey` on account switches. Runtime credentials should come from your secret manager/environment, never a committed file or a client-side Vite variable.

`scripts/chat_host_e2e.sh` seeds a temporary backend with fake credentials/mock responses, builds this example and the older headless sample, tests React, widget and headless flows sequentially on the same allowed origin, then removes its temporary database/processes. Light, dark and custom screenshots are stored under ignored `frontend/test-results/react-chat/` and uploaded as short-lived CI artifacts. No real model service or package publication is involved.

Handbook: [React en](../../handbook/docs/en/run/chat-react.md) / [React vi](../../handbook/docs/vi/run/chat-react.md), [widget en](../../handbook/docs/en/run/chat-widget.md) / [widget vi](../../handbook/docs/vi/run/chat-widget.md). No package publication is implied by these checkout instructions.
