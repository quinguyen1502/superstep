# React chat toolkit

Use `@superstep/react` to render a published workflow's chat in your own React
application. It shares the Studio's chat components and uses
`@superstep/sdk/chat` for HTTP, streaming, files and feedback. Your backend
vouches for your users with a short-lived token; they do not need Studio accounts.
For a bubble on an existing website, see [Chat widget](chat-widget.md).

## Prepare the chat and packages

1. Publish the workflow's Chat page and enable **Third-party app users** (`app`).
2. Create an app key. Allow your application's exact origin, for example
   `https://shop.example.com`. Keep its secret on your backend.
3. Expose an authenticated token endpoint that derives the user ID from your
   server session and returns a short-lived JWT. See
   [Third-party chat authentication](chat-third-party-auth.md).
4. Use compatible approved versions of `@superstep/react` and `@superstep/sdk`
   with React/React DOM 18 or later, i18next and react-i18next as peer dependencies.

Package publication is separate from implementation. This repository prepares
TypeScript SDK 0.2.0 and React toolkit 0.1.0; this guide does not imply a new npm
release. To try the checkout before an approved package release:

```sh
npm ci
npm run build
scripts/chat_host_e2e.sh
```

The loopback sample server serves the headless portal at `/`, the React page at
`/react/` and the widget page at `/widget.html`. The acceptance script tears the
server down when tests finish. The sample READMEs explain how to run it against
your development Studio; replace its fixed Lan/Minh sign-in stub with your own
authentication before deployment.

## Render the complete chat

Import the prebuilt stylesheet once. Your host needs no Tailwind configuration.
Give the chat a container height:

```tsx
import { Chat } from '@superstep/react'
import '@superstep/react/styles.css'

async function getToken() {
  const response = await fetch('/api/auth/chat-token', {
    method: 'POST', credentials: 'same-origin',
  })
  const body = await response.json()
  if (!response.ok || !body.success) throw new Error('Token request failed')
  return body.data.token
}

export function Support({ user }: { user: { id: string } }) {
  return <Chat
    slug="support"
    baseUrl="https://studio.example.com"
    identityKey={user.id}
    getToken={getToken}
    locale="en"
    theme={{ colorScheme: 'system', radius: 12 }}
    style={{ height: 640 }}
  />
}
```

The sample token endpoint uses the standard `{success, data, error}` envelope.
Adapt the return expression if your own endpoint has a different response shape.
Never return an app secret, PAT or workflow token to this callback. Its request
uses your host's cookie; the SDK sends only the resulting Bearer token to Studio
and omits cookies on its HTTP requests.

`Chat` includes history/new conversation controls, streamed replies, Human
answers, attachment upload/download, feedback and error notices. Reviewer-owned
questions remain read-only. Restored Human history has its saved prompt and
text/approve/reject controls; structured fields/options render when available
in the streamed question.

## Identity, history and failures

- Change `identityKey` when the person changes, or remount the chat. Changing
  only `getToken` refreshes credentials while keeping the current conversation.
- `getToken` may return a string or a promise. The SDK calls it for operations
  and retries an expired credential once. It does not replay an ambiguous write;
  reconnecting recovers persisted history.
- Undefined `sessionId` restores the latest chat; `null` starts empty; a string
  loads that chat. Changing the prop resets the resource and draft.
- On host logout, unmount the app-user chat. If anonymous access is enabled,
  render a separate instance with `visitorToken` and `onVisitorToken`. Persist
  that anonymous HMAC in host storage if desired. Do not combine it with `getToken`.
- Async controller methods reject and expose `chat.error`; handle their promises
  in custom layouts. SDK errors have codes such as `CHAT_TOKEN_EXPIRED`,
  `CHAT_APP_KEY_REVOKED` and `CHAT_ORIGIN_FORBIDDEN`. A refused cross-origin request
  can appear as a network error. See [authentication errors](chat-third-party-auth.md#errors-and-limits).
- Switching identity cancels old work and clears the old messages/draft/dialogs.
  Unmounting releases subscriptions and aborts pending work; StrictMode replay
  preserves the live resource.

## Compose your own layout

```tsx
import {
  useChat, ChatProvider, MessageList, QuestionCard, Composer,
} from '@superstep/react'

function CustomSupport({ user }: { user: { id: string } }) {
  const chat = useChat({
    slug: 'support', baseUrl: 'https://studio.example.com',
    identityKey: user.id, getToken, locale: 'en',
  })
  return <ChatProvider chat={chat} locale="en"
    theme={{ colorScheme: 'dark' }} style={{ height: 640 }}>
    <MessageList />
    <QuestionCard />
    <Composer />
  </ChatProvider>
}
```

`useChat` exposes `page`, `sessions`, `turns`, `text`, `question`, `sessionId`,
`loading`, `busy`, `status`, `error`, `waiting` and `answeredBy`. Its actions are
`refresh`, `load`, `start`, `send`, `answer`, `cancel`, `upload`, `removeFile`,
`download` and `rate`. `Rating` accepts a turn from `chat.turns`. The shared
confirmation dialog requires the exact attachment/rating name before removal;
the API DELETE remains unchanged.

`MessageList` accepts an `empty` React node; `Composer` accepts `idPrefix`.
`ChatProvider` can wrap shared presentation primitives without a controller,
but controller-based components still need `chat`. `embed: true` on `useChat`
marks newly created sessions as embeds. Direct React integrations normally
leave it unset; a widget's iframe sets it automatically.

## Theme and language

`locale` accepts `en` or `vi`. Each provider owns its translations; changing it
does not change the host or another chat. Override dotted keys with
`messages={{ 'chat.placeholder': 'Ask our team' }}`.

`theme` accepts `primary`, `primaryForeground`, `radius`, `font` and
`colorScheme` (`light`, `dark`, `system`). Root CSS variables include
`--ss-background`, `--ss-foreground`, `--ss-primary`,
`--ss-primary-foreground`, `--ss-border`, `--ss-radius` and `--ss-font`.
Host variables such as `var(--brand)` can be used by the React provider.
The generated stylesheet is scoped under `.superstep-chat`, including
preflight, utilities, Markdown, variables and keyframes. Dialogs/selects/tooltips
portal into the provider root. Host styles can still inherit into the chat;
there is no Shadow DOM boundary.

## Run the examples

The repository's `examples/react-chat` consumes built packages without Studio
source aliases or a Tailwind plugin. It demonstrates both `<Chat>` and a custom
composition with independent locales/themes. The shared Node host keeps its
signing secret server-side and uses an opaque HttpOnly session.

```sh
PW_CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  scripts/chat_host_e2e.sh
```

Omit `PW_CHROME` when Playwright's Chromium is installed. CI runs the shared
React/widget/headless acceptance with React 18 and 19: streaming, Human answers,
files, feedback, identity/history isolation, logout, origin refusals and key
revocation. Screenshots are temporary CI artifacts, never Git evidence.


## Edit a sent message

Message actions reuse the shared [editing flow](chat.md#edit-a-sent-message): confirm a fresh execution in an independent conversation branch, keep the original, and use the source link to return. Human replies are not editable roots. For custom interfaces, `useChat().edit(turnId, text, operationId)` requires the same explicit rerun confirmation; retain the operation ID when recovering an interrupted attempt. See the [API contract](chat-api.md#prepare-and-execute-an-edit) for admission and recovery.
