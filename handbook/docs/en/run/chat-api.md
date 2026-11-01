# Chat API

Build a client for a [published chat](chat.md#publish-a-chat) with HTTP for
sessions, history, files and ratings, and WebSocket for streaming messages.
The chat runs the saved workflow using its owner's resources. A caller can
access only their own sessions.

## Contract and access

| Contract | Running server | Source |
| --- | --- | --- |
| HTTP v1 | `/openapi.public.json`, `/docs/public`, tag `Chat` | [Public API reference](../reference/public-api.md), [OpenAPI JSON](../reference/openapi.public.json) |
| Socket v1 | `/asyncapi.public.yaml` | [AsyncAPI YAML](https://github.com/quinguyen1502/superstep/blob/develop/docs/asyncapi/chat-v1.yaml) |
| Frame schemas | Included in AsyncAPI | [Client and server JSON Schema](https://github.com/quinguyen1502/superstep/tree/develop/backend/app/api/schemas/chat_ws_v1) |

HTTP uses `/api/public/v1/chat/{slug}`; streaming uses
`/ws/public/v1/chat/{slug}` (`wss://` over HTTPS). Use the versioned paths for
new clients. See [Compatibility](../reference/compatibility.md) for the old
paths and version policy. There is one message or Human answer per socket
connection; SSE is not available.

| Access mode | HTTP identity | Socket identity |
| --- | --- | --- |
| `anonymous` | Chat cookie, or `X-Chat-Visitor` | Chat cookie, `auth.visitor`, or `?visitor=` |
| `signed_in` | Studio session/Bearer token | Studio session, or studio `?token=` on the same origin |
| `app` | `Authorization: Bearer <user JWT>` | First `auth.token` frame; `?token=` is a fallback |

Anonymous and studio clients use the same origin as Superstep (an embedded
page runs inside its Superstep iframe). A direct cross-origin client needs
an app token and an allowed origin: see [Third-party auth](chat-third-party-auth.md).
`access` can be a legacy single string or a list of modes; a valid app token
takes priority over an anonymous cookie. App, anonymous and studio histories
stay separate.

## Start a session

Obtain a short-lived user token from your own authenticated backend. Here
`userToken` is that JWT; `baseUrl` is your Superstep origin, with no trailing
slash, and `slug` is the chat's page address.

```javascript
const baseUrl = 'https://studio.example.com'
const slug = 'support'
async function chatHttp(path, options = {}) {
  const response = await fetch(`${baseUrl}/api/public/v1/chat/${slug}${path}`, {
    ...options,
    credentials: 'omit',
    headers: { ...options.headers, Authorization: `Bearer ${userToken}` },
  })
  const body = await response.json()
  if (!body.success) throw body.error
  return body.data
}
const page = await chatHttp('')
const session = await chatHttp('/sessions', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
})
const sessionId = session.id
```

REST JSON uses `{"success":true,"data":...,"error":null}`; an error has
`success:false` and `error:{code,message,details}`. Logo and attachment
downloads return image/file bytes. All routes are listed in the
[HTTP reference](../reference/api.md#public-chat-v1).

For same-origin anonymous clients, start with `X-Chat-Visitor: new` when not
using cookies. Keep `data.visitor_token` returned by session creation/listing
and send it as `X-Chat-Visitor` thereafter, and as `auth.visitor` on sockets.
It is a credential for that visitor's history; do not expose it to other users.

## Send and stream

This example continues with `baseUrl`, `slug`, `sessionId` and `userToken`
above. The token is sent in a frame, keeping it out of the URL.

```javascript
const socketUrl = new URL(`/ws/public/v1/chat/${slug}`, baseUrl)
socketUrl.protocol = socketUrl.protocol === 'https:' ? 'wss:' : 'ws:'
const socket = new WebSocket(socketUrl)
let lastSeq = -1
socket.addEventListener('message', ({ data }) => {
  const frame = JSON.parse(data)
  if (frame.v !== 1 || frame.seq <= lastSeq) return
  lastSeq = frame.seq
  switch (frame.type) {
    case 'ready':
      socket.send(JSON.stringify({ type: 'auth', token: userToken }))
      socket.send(JSON.stringify({ type: 'message', chat_session_id: sessionId,
        text: 'Where is my order?', attachments: [], locale: 'en' }))
      break
    case 'token':
      // Append frame.delta to the draft answer.
      break
    case 'question':
      // Keep frame.node and show frame.prompt to the person chatting.
      break
    case 'turn':
      // Keep frame.turn_id to rate the saved assistant answer.
      break
    case 'done':
      // Check frame.status, then reload the saved turns over HTTP.
      break
    case 'error':
      // Handle frame.error.code; do not display raw errors as HTML.
      break
    default:
      // Ignore unknown frame types; optional step/run_started frames need no action here.
      break
  }
})
socket.addEventListener('close', () => {
  // A close without done/error is an interruption: recover history before retrying.
})
socket.addEventListener('error', () => {
  // Show a connection error without logging the token.
})
```

## Frames

Client frames have `type` and the fields below. Do not add `v`, `seq` or
arbitrary extra fields to a client frame; invalid frames return
`CHAT_FRAME_INVALID`. Send at most one `auth`, before the operation.

| Client type | Fields |
| --- | --- |
| `auth` | `token` for an app user, or `visitor` for an anonymous visitor |
| `message` | `chat_session_id`, `text`; optional `attachments` (uploaded ids), `locale` (`en`/`vi`) |
| `answer` | `chat_session_id`, `response`; optional `node` from the question and `locale` |
| `cancel` | No other fields; send while the run is active |

Every server frame has `v:1` and a `seq` starting at zero and increasing
within that connection. `ts`, when present, is Unix seconds. Ignore unknown
types and fields. `seq` restarts on a new socket; it is not a history cursor.

| Server type | Meaning |
| --- | --- |
| `ready` | Socket accepted, `protocol:"superstep-chat"`; authentication/permission is still to be checked |
| `run_started` | The run's `run_id` |
| `token` | Append `delta`; optional `node`, `field`, `iteration` |
| `step` | `event` = `started`, `finished` or `error`, plus `node`; details depend on the configured steps mode |
| `question` | A Human node is waiting: `node`, `prompt`, `kind`/`input_type`, with optional options/fields |
| `turn` | The stored assistant `turn_id`, `role`, optional `status` and `run_id`; emitted before `done` when persistence finishes in time |
| `done` | `status` = `ok`, `error`, `waiting`, `cancelled` or `timeout`; server closes afterwards |
| `error` | Stable `error.code`, English `message`, optional `details`; no `done` is guaranteed after an error |

An illustrative exchange (ids are placeholders):

```json
{"type":"ready","protocol":"superstep-chat","v":1,"seq":0}
{"type":"run_started","run_id":"r1","v":1,"seq":1}
{"type":"token","delta":"Hello","v":1,"seq":2}
{"type":"turn","turn_id":"t2","role":"assistant","status":"ok","run_id":"r1","v":1,"seq":3}
{"type":"done","status":"ok","run_id":"r1","v":1,"seq":4}
```

## Human answers and cancellation

After `question` and `done` with `status:"waiting"`, open a **new** socket,
authenticate again and send an answer for the same session:

```json
{"type":"answer","chat_session_id":"session-id","node":"human-node-id","response":"yes","locale":"en"}
```

Use the question's `node` and the response type the Human node accepts
(for example text or a boolean approval). The transport schema also permits
form objects; that alone does not add a form runtime. Questions assigned to a
reviewer are not answerable by the visitor (`CHAT_ANSWER_BY_REVIEWER`).
Do not send attachments with an answer. To cancel an active run, send
`{"type":"cancel"}` on its socket. Disconnecting also requests cancellation;
fetch history to find the final outcome.

## History and reconnection

`GET .../sessions` lists your sessions; `GET .../sessions/{sid}` includes
saved turns. After a stream or interruption, fetch
`GET .../sessions/{sid}/turns?after=<last-saved-turn-id>` for newer turns in
order; omit `after` for all turns. Responses contain `data.turns`.
An unknown or another session's cursor returns `404 CHAT_TURN_NOT_FOUND`.

Use stored turn ids to reconcile the draft stream with persisted history.
Persistence can lag: poll with backoff if the last turn is not saved yet.
There is no socket replay or message idempotency key. Resending text after
a disconnect can start another run, so inspect history first. An interrupted
connection may have no terminal `done`; `seq` cannot resume it.

## Files and ratings

1. Read `page.attachments` (`enabled`, `kinds`, `max_files`, `max_mb`).
2. Upload one file per `POST .../sessions/{sid}/attachments`, multipart field
   `file`; keep `data.id`. The browser sets the multipart Content-Type boundary.
3. Put those ids in `message.attachments`. Files must belong to that session
   and be unsent. A file already sent cannot be reused or deleted through
   the unsent-file endpoint.
4. Download with authenticated `GET .../attachments/{aid}` (bytes). Remove
   an unsent file with `DELETE .../attachments/{aid}`. JSON deletes return
   `data.ok`; they do not take a confirmation field.

Documents are PDF or UTF-8 `.txt`, `.md`, `.csv`; images are PNG, JPEG or
WebP. Chat settings and operator ceilings apply. An upload consumes the
message-rate quota too. See [Attachments](chat.md#attachments).

Rate an assistant turn with status `ok` or `error` using
`PUT .../sessions/{sid}/turns/{tid}/rating`, body `{"value":"up"}` or
`{"value":"down","comment":"Missing the delivery date"}`. A down comment
is optional and at most 1,000 characters; an up rating has no comment.
`DELETE` on the same path removes the rating. Use the saved `turn_id`,
fetching history if the stream did not include a `turn` frame.

## Errors and limits

Handle `error.code`, not message text. `CHAT_SESSION_NOT_FOUND` also hides
another user's session. Token errors and origin policy are in the
[auth guide](chat-third-party-auth.md); all codes are in
[Error codes](../reference/errors.md).

`429 RATE_LIMITED` carries HTTP `Retry-After` in seconds (socket errors carry
`error.details.retry_after`). Back off before opening another socket or
retrying a write. Per-IP read/message limits, per-visitor or external-user
message limits, and the chat's UTC daily cap all apply. Operators configure
`STUDIO_PUBLIC_CHAT_RATE_*`; see [Configuration](../reference/configuration.md).
