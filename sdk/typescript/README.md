# @superstep/sdk (TypeScript SDK)

Headless chat and workflow runs for Superstep. Version 0.2.0 adds chat v1,
typed streaming events, a framework-neutral store and server-side token signing.
Zero runtime dependencies; ESM and CommonJS; HTTP types generated from OpenAPI
and socket types generated from the backend JSON Schemas. Chat uses `fetch` and
an injectable WebSocket in browsers, Node 18+ and React Native.

- Guide: <https://quinguyen1502.github.io/superstep/run/public-api/>
- API reference: <https://quinguyen1502.github.io/superstep/reference/public-api/>
- Spec: [`docs/api/openapi.public.json`](../../docs/api/openapi.public.json)

## Install

```bash
npm install @superstep/sdk
```

The examples below describe 0.2.0; installing from npm requires that version to
have been published by the owner. Building this repository does not publish it.

## Chat

For a web UI, see the [React toolkit guide](../../handbook/docs/en/run/chat-react.md) and [widget guide](../../handbook/docs/en/run/chat-widget.md), also available in [Vietnamese](../../handbook/docs/vi/run/chat-react.md).


Publish a workflow with app access, then create an app key in Chat settings.
Keep its secret in your application's backend. After authenticating your user,
mint a short-lived token there:

```ts
// Your server only. Never put an app key in browser or native code.
import { mintChatToken } from '@superstep/sdk/server'

const token = await mintChatToken({
  keyId: process.env.CHAT_KEY_ID!,
  secret: process.env.CHAT_KEY_SECRET!,
  slug: 'support',
  userId: authenticatedUser.id,
  name: authenticatedUser.name,
  meta: { locale: 'vi' }, // Untrusted attributes; never grants permissions.
  ttl: 600,             // Seconds, 1..3600; default 600.
})
```

The helper uses HS256 with the secret's literal UTF-8 bytes and the audience
`superstep-chat:<slug>`. Metadata must be JSON and at most 1024 UTF-8 bytes.
Signing uses Web Crypto, with Node crypto as a fallback. Only the `/server`
entry exports this helper. Your token endpoint must authenticate the user and
derive `userId` itself. An origin-restricted key requires a matching browser
origin; native/server callers need a key configured for their deployment.

```ts
import { Superstep } from '@superstep/sdk'

const client = new Superstep({ baseUrl: 'https://superstep.example.com' })
const chat = client.chat('support', {
  getToken: async () => {
    const response = await fetch('/my-app/chat-token')
    if (!response.ok) throw new Error('Cannot authenticate chat')
    return (await response.json()).token
  },
})

const page = await chat.info()
const session = await chat.start()
const stream = chat.send(session.id, 'Hello', { locale: 'vi' })
for await (const event of stream) {
  if (event.type === 'token') processToken(event.delta)
  if (event.type === 'question') showQuestion(event)
  // ready, run_started, step, turn, done, error, history and result are typed too.
}
const result = await stream.result
if (result.status === 'waiting') {
  const answer = chat.answer(session.id, 'yes', { node: result.question?.node ?? undefined })
  for await (const event of answer) handleEvent(event)
  await answer.result
}
```

`answer` also accepts a JSON form object (for example `{ approved: true,
note: 'Confirmed' }`) or a boolean approval. The backend bounds text and
serialized form answers to 10000 characters. This headless SDK does not render
form controls; a host uses the question metadata and its own UI.

`chat.list()` lists the current user's sessions; `chat.get(sessionId)` reads a
session with its turns; `chat.turns(sessionId, { after: lastTurnId })` fetches
incremental history. Anonymous chats can omit `getToken`: the SDK requests a
visitor identity using `X-Chat-Visitor: new`. Save `onVisitorToken(token)` in
host-controlled storage and pass it back as `visitorToken` to restore it.
Storage is never accessed automatically. Use a separate client per identity;
`getToken` and `visitorToken` cannot be combined. Anonymous cross-origin
browser access is not enabled by the public API's app-token CORS policy.

### Streaming, refresh and cancellation

Always drain the async iterator; it yields a final `result` event as well as
exposing `stream.result`. An undrained queue is bounded to 1024 events and
rejects with `CHAT_BUFFER_FULL`. `result.status` may be `ok`, `waiting`,
`error`, `cancelled` or `timeout`; a workflow error is a terminal result, while
a protocol/authentication/transport error rejects the iterator and result.
Unknown event types are ignored for v1 compatibility.

`getToken` runs for each HTTP operation or socket connection. Only an explicit
`CHAT_TOKEN_EXPIRED` retries once (on a socket, before `run_started`). Revoked
keys and forbidden origins are not retried. Authentication uses headers and
socket frames; tokens never enter URLs. Chat requests omit studio cookies
and refuse HTTP redirects. Workflow tokens are not used for chat.

After completion or a dropped socket, the client reads `turns?after=` to recover
persisted history (20 attempts, 250 ms apart by default). An interrupted stream
is confirmed only by a new assistant turn for its known run ID. If confirmation
is unavailable, it rejects with `CHAT_STREAM_INTERRUPTED`; reload history before
deciding what to do. The SDK never automatically resends an ambiguous message.
Use `after`, `recoveryAttempts` (0..100) and `recoveryIntervalMs` to tune this.

`stream.cancel()` or `chat.cancel(sessionId?)` sends a cancellation frame and
waits for the terminal result. An `AbortSignal`, breaking iteration or disposing
a store aborts the local operation, sends cancellation when possible and releases
listeners; server completion can still race cancellation, so reload history if
needed. `timeoutMs` is the socket deadline (default 300000; `null` disables it).
Pass a signal to bound host token callbacks and HTTP requests too.

### Attachments and ratings

```ts
// Browser File/Blob, Node Buffer/Uint8Array/ArrayBuffer, or native descriptor.
const file = await chat.attachments.upload(session.id, selectedFile)
const message = chat.send(session.id, 'Read this', { attachments: [file.id] })
for await (const event of message) handleEvent(event)
const answer = await message.result
const download = await chat.attachments.download(session.id, file.id) // Response
await chat.ratings.put(session.id, answer.turnId!, 'down', { comment: 'Missing context' })
await chat.ratings.delete(session.id, answer.turnId!)
// An attachment can be deleted before it is sent:
// await chat.attachments.delete(session.id, unsentFile.id)
```

The server must enable attachments for this chat. For raw bytes pass
`{ name: 'note.txt', type: 'text/plain' }` as upload options. Native uploads
accept `{ uri, name, type }` through native FormData without fetching the URI.
Inject `FormData`/`Blob` with compatible host implementations when needed;
the SDK lets the runtime set the multipart boundary.

### Store and runtimes

```ts
import { ChatClient, createChatStore } from '@superstep/sdk/chat'

const store = createChatStore(chat)
const unsubscribe = store.subscribe(() => render(store.getSnapshot()))
await store.load(session.id) // Or store.start(); send() can start implicitly.
await store.send('Hello')
// store.answer(...), store.cancel()
unsubscribe()
store.dispose()
```

Snapshots are stable between updates. The store handles streamed text,
questions, persisted turns, errors and cancellation, and prevents overlapping
sends. Start/load switches ignore stale asynchronous results. React and native
bindings can share this store; UI components are delivered in later tasks.

Browsers and React Native use their global WebSocket. Node 18/20 callers must
provide one if unavailable (for example `new ChatClient('support', { baseUrl,
getToken, WebSocket: YourSocketAdapter })`). The adapter needs `readyState`,
`send`, `close`, `addEventListener` and `removeEventListener`; message events
must carry JSON text in `data`. `fetch`, `Blob` and `FormData` are injectable.
The SDK does not install a socket adapter or DOM polyfills. Actual device
testing and native UI belong to TASK-0227; the current contract suite simulates
a native runtime without DOM/Buffer globals.

## Configure

A workflow token (`wft_...`) starts runs of one workflow. The workflow owner
creates it in the editor under **More (⋯) → API → Create token**; it is shown
once. Keep it on the server: do not ship it to browsers you do not control.

```ts
import { Superstep } from '@superstep/sdk'

const client = new Superstep({
  workflowId: 'example',
  token: 'wft_...',
  baseUrl: 'https://superstep.example.com',
})
```

Options left out are read from `SUPERSTEP_WORKFLOW_ID`, `SUPERSTEP_TOKEN`
and `SUPERSTEP_BASE_URL` when `process.env` exists. A missing base URL throws
`ConfigError`; workflow ID/token are required when a workflow operation starts,
so chat-only clients need only `baseUrl`. Pass `fetch` to use a custom implementation.

## Run a workflow

```ts
// Start and wait: polls with a growing interval (1 s, 1.5 s, ... up to 10 s).
const run = await client.runAndWait({ message: 'where is my order A100' }, { timeoutMs: 120_000 })
console.log(run.status, run.final_state)

// Or step by step.
const started = await client.run({ message: 'hi' })   // status "queued", poll_url set
const current = await client.getRun(started.run_id)   // status, final_state, metrics ...
const done = await client.wait(started.run_id, { timeoutMs: 60_000, pollIntervalMs: 500 })

// Let the server wait (up to STUDIO_SYNC_WAIT_MAX seconds, default 30).
const quick = await client.run({ message: 'hi' }, { mode: 'sync' })
```

`isDone(run)` is true for every status except `queued` and `running`.
Finished statuses are `ok`, `error`, `cancelled`, `timeout`, `waiting`
(paused at a Human node, see `run.waiting`) and `expired`. `runAndWait`
resolves with the run whatever its final status; check `run.status`.

Options of `runAndWait` and `wait`: `timeoutMs` (default 300000, `null` waits
forever), `pollIntervalMs` (1000), `maxPollIntervalMs` (10000), `backoff`
(1.5), `signal`. `run` also takes `callbackUrl`.

### Cancel with AbortSignal

Every method takes `signal`; aborting stops the request and the polling and
rejects with the signal's reason.

```ts
const run = await client.runAndWait({ message: 'hi' }, { signal: AbortSignal.timeout(30_000) })
```

## Errors

API errors are subclasses of `SuperstepError` with `code` (the API's stable
error code), `status`, `message` and `details`.

| Class | When |
| --- | --- |
| `AuthenticationError` | Missing, invalid, expired or revoked workflow/chat authentication |
| `PermissionDeniedError` | Forbidden chat origin or HTTP 403 |
| `NotFoundError` | `404 RUN_NOT_FOUND` |
| `InvalidRequestError` | `400 RUN_INPUT_INVALID`, `CALLBACK_URL_INVALID`; `422 VALIDATION_ERROR` |
| `PayloadTooLargeError` | `413 RUN_INPUT_TOO_LARGE` |
| `RateLimitError` | `429 RATE_LIMITED`; `retryAfter` holds the seconds to wait |
| `ServerError` | `5xx` |
| `APIConnectionError` | Network failure, or a response that is not the API envelope |
| `WaitTimeoutError` | `wait` / `runAndWait` ran out of time; `err.run` is the last state |
| `ConfigError` | Missing base URL, token or workflow id |

```ts
import { RateLimitError } from '@superstep/sdk'

try {
  await client.run({ message: 'hi' })
} catch (err) {
  if (err instanceof RateLimitError) console.log(`retry in ${err.retryAfter ?? 1} s`)
  else throw err
}
```

## Types

`Run`, `RunResult`, `RunStatus`, `RunMetrics` and the raw `paths`,
`operations` and `components` are exported alongside `ChatEvent`, `ChatResult`,
`ChatSession`, `ChatTurn` and other chat types. `src/schema.ts` comes from the
public spec; `src/chat/frames.ts` comes from the backend's v1 JSON Schemas:

```bash
npm run gen         # regenerate HTTP and socket types
npm run gen:check   # fail when it is out of date (CI)
```

## Development

```bash
cd sdk/typescript
npm ci
npm test            # workflow, Node/jsdom/native chat contracts, store and tokens
npm run build       # dist/esm and dist/cjs
```

The workflow live test (`test/integration.test.ts`) runs when `SUPERSTEP_IT_BASE_URL`,
`SUPERSTEP_IT_TOKEN` and `SUPERSTEP_IT_WORKFLOW_ID` are set;
`scripts/sdk_integration.sh` at the repository root starts a local backend
and runs it for both SDKs. It also seeds ephemeral app keys and sets
`SUPERSTEP_IT_CHAT_CONFIG` for `test/chat-integration.test.ts` (TypeScript chat,
Human text/form answers, anonymous identity, files, ratings, user isolation,
expiry and revocation). Shared synthetic signing vectors live in
`sdk/fixtures/chat-token-vectors.json` and are verified by the real backend.

## License

MIT


## Edit a message (0.11.0 target)

Confirm that the currently saved workflow may repeat API calls/writes/notifications before calling `edit`. It creates an independent branch; it never changes the original session. Keep `operationId` when recovering the same intent. A repeated intent reads the reserved run's persisted result instead of sending another execution.

```ts
const before = await chat.get(sessionId)
const operationId = crypto.randomUUID() // browser; persist with this deliberate intent
const edited = chat.edit(sessionId, turnId, 'Corrected request', {
  operationId, expectedLastTurnId: before.turns[before.turns.length - 1].id,
})
for await (const event of edited) {
  if (event.type === 'session') console.log('Branch:', event.session.id)
}
const branchId = (await edited.result).sessionId
```

`prepareEdit` creates the branch without running it. Session `capabilities.edit` and turn `editable` advertise support. An older server fails with `CHAT_EDIT_UNSUPPORTED`. Use the returned branch for history, Human answers, files and ratings. See the bilingual [API guide](../../handbook/docs/en/run/chat-api.md#prepare-and-execute-an-edit).
