# @superstep/react

React chat toolkit shared with Superstep Studio. `useChat` binds the headless `createChatStore` in `@superstep/sdk/chat`; the public components reuse the Studio's shadcn chat presentation. Package publication requires separate owner approval.

```tsx
import { Chat } from '@superstep/react'
import '@superstep/react/styles.css'

<Chat
  baseUrl="https://studio.example.com"
  slug="support"
  identityKey={user.id}
  getToken={getShortLivedTokenFromYourBackend}
  locale="vi"
  theme={{ colorScheme: 'system', primary: 'var(--brand)', radius: 12 }}
  style={{ height: 600 }}
/>
```

Install `@superstep/sdk` and the React/React DOM, i18next/react-i18next peers in your host. Keep one instance of each. The app key secret stays on your backend. `getToken` is called by the SDK for each operation and refreshed on expiry. Change `identityKey` (or remount the chat) whenever the signed-in person changes; replacing a token callback alone preserves the current conversation. For anonymous chat, use `visitorToken` plus `onVisitorToken` to save the returned identity on the host; never mix it with `getToken`.

For a custom layout:

```tsx
const chat = useChat({ baseUrl, slug, identityKey: user.id, getToken, locale: 'en' })
return <ChatProvider chat={chat} locale="en" theme={{ colorScheme: 'dark' }}>
  <MessageList />
  <QuestionCard />
  <Composer />
</ChatProvider>
```

`Chat` includes history selection, refresh/new conversation, messages, Human answers, attachments, ratings and an error notice. `Rating` accepts a turn directly from `chat.turns` and renders its feedback. Identity/session switches also close destructive dialogs. `QuestionCard` accepts streamed fields/options when supplied by the workflow; a restored waiting turn exposes its saved prompt and text/approve/reject controls. Reviewer questions stay read-only. Custom layouts can read `chat.error` to provide their own error notice.

The controller exposes `page`, `sessions`, `turns`, `text`, `question`, `sessionId`, `status`, `loading`, `busy`, `error`, `waiting` and `answeredBy`, plus async `refresh`, `load`, `start`, `send`, `answer`, `upload`, `removeFile`, `download`, `rate`, and synchronous `cancel`. Async calls reject as the SDK does, and record failures in the controller. Callers should handle the returned promises. Undefined `sessionId` restores the latest history; null leaves a new instance empty; a string loads that session. Changing this prop or `identityKey` resets the resource and local draft. Unmounting releases subscriptions and aborts pending work; StrictMode's effect replay does not destroy a live resource.

Import `styles.css` once. No host Tailwind setup is required. Generated utilities (including `ss-` aliases), preflight and typography are scoped under `.superstep-chat`; CSS properties/keyframes are namespaced. Dialogs, selects and tooltips portal inside the provider root. The stylesheet does not set a host body font or modify host cascade layers. Set container height explicitly. Host CSS can still cascade into the chat; a Shadow DOM boundary is outside this task.

`theme` supports `primary`, `primaryForeground`, `radius`, `font` and `colorScheme` (`light`, `dark`, `system`). CSS token overrides belong on the root: `--ss-background`, `--ss-foreground`, `--ss-primary`, `--ss-primary-foreground`, `--ss-border`, `--ss-radius`, `--ss-font`. `locale` accepts `en` or `vi`; `messages` overrides dotted translation keys, for example `{ 'chat.placeholder': 'Ask our team' }`. Each provider owns its i18next instance; host language and other chats are unaffected. Source translations and theme tokens are generated from the existing Studio files to avoid a second source of truth.

`ChatThread`, `ChatComposer`, `ChatRatingBar`, `ChatSteps`, `ChatConfirmation`, `ChatMarkdown`, `ChatLogo` and attachment primitives remain shared with Studio. `ChatPresentationProvider` supplies optional host capabilities for child-run content and reviewer navigation. `./ui/*` and helper subpaths serve that shared implementation and can change before the first public toolkit release.

From the repository root:

```sh
npm ci
npm run build
npm run lint
npm test
# Isolated backend + built Vite toolkit and headless examples, UI screenshots as CI artifacts:
scripts/chat_host_e2e.sh
```

The root lockfile owns all three npm workspaces. Development uses the `source` export condition; normal ESM consumers receive built code/declarations. See [the Vite example](../../examples/react-chat/README.md). The `sdk-react-v<version>` workflow checks the package version, tests/builds and prepares npm provenance publishing; branches and PRs do not publish. Screenshots remain temporary files/CI artifacts, never package files or Git evidence.
