# @superstep/react-native

Native chat UI for the Superstep public chat API. Version 0.1.0. Peers are
`react-native` >= 0.73 and `@superstep/sdk` ^0.2.0. The package does not depend
on `react-dom`, React DOM, shadcn, or a markdown library.

`useChat` is a thin binding over `ChatClient` and `createChatStore`. `Chat`,
`MessageList`, `Composer` and `QuestionCard` render with React Native
primitives. Pass `theme` to replace the default colours. `locale` is `en` or
`vi`. `pickFile` supplies `{ uri, name, type }` for an upload; this package
does not depend on a document picker. `renderMarkdown` replaces the built-in
renderer. That renderer allows paragraphs, bold, italic, inline code, lists
and `http:` / `https:` links. Other markup stays text.

```tsx
import { Chat } from '@superstep/react-native'

<Chat
  slug="your-chat"
  baseUrl="https://studio.example"
  locale="vi"
  getToken={mintOnYourServer}
  pickFile={pickFile}
/>
```

Use either `getToken` or `visitorToken`, the same rule as the SDK. Keep the
app-key secret on your server. The Expo sample in `examples/react-native`
signs in to `examples/chat-host` and calls `POST /api/auth/chat-token`.

This directory is not an npm workspace of the Studio app. Studio stays on
React 19. Install and test here:

```sh
npm ci --workspace=@superstep/sdk --include-workspace-root=false
npm run build --workspace=@superstep/sdk
cd packages/react-native
npm ci
npm test
```

The publish workflow accepts a `sdk-rn-v*` tag only. Creating that tag is a
separate release step.

## Tests

Jest and React Native Testing Library drive `Chat` through a fake `fetch` and
a fake `WebSocket`. No device or network is required for `npm test`.
