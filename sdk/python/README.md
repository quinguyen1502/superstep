# superstep (Python SDK)

Python client for Superstep workflow runs and headless chat v1. Sync and async
clients, typed results/errors; the base dependency is `httpx`. Socket streaming
uses the optional `superstep[chat]` extra. The package shares its version with
the CLI/server; chat ships in the next owner-approved release, not a downgrade
to the old standalone SDK 0.2.0 target.

- Guide: <https://quinguyen1502.github.io/superstep/run/public-api/>
- API reference: <https://quinguyen1502.github.io/superstep/reference/public-api/>
- Spec: [`docs/api/openapi.public.json`](../../docs/api/openapi.public.json)

## Install

```bash
pip install superstep
# from the repository, before the first release:
pip install ./sdk/python
```

Python 3.9 or later.

## Chat

For a web UI, see the [React toolkit guide](../../handbook/docs/en/run/chat-react.md) and [widget guide](../../handbook/docs/en/run/chat-widget.md), also available in [Vietnamese](../../handbook/docs/vi/run/chat-react.md).


```bash
pip install 'superstep[chat]'
# From this repository before publication:
pip install './sdk/python[chat]'
```

Publish a workflow with app access and create an app key in Chat settings.
Authenticate your user in your own server, then mint a short-lived token there:

```python
from superstep import mint_chat_token

token = mint_chat_token(
    key_id=app_key_id, secret=app_key_secret, slug="support",
    user_id=authenticated_user.id, name=authenticated_user.name,
    ttl=600, meta={"locale": "vi"},
)
```

The helper uses only the standard library, HS256 with the literal UTF-8 secret,
and the audience `superstep-chat:<slug>`. TTL is 1..3600 seconds (default 600);
JSON metadata is bounded to 1024 UTF-8 bytes and grants no permissions. Keep the
app-key secret in your server. Never let a browser choose the signed user ID.

```python
from superstep import Client

# A callback gets a fresh user token from your application server; a fixed JWT
# string is also accepted. Never pass a workflow token or app-key secret here.
with Client(base_url="https://superstep.example.com") as client:
    chat = client.chat("support", token=get_user_token)
    page = chat.info()
    session = chat.start()  # HTTP methods return dictionaries.
    with chat.send(session["id"], "Hello", locale="vi") as stream:
        for event in stream:
            if event["type"] == "token":
                print(event["delta"], end="", flush=True)
    result = stream.result  # ChatResult, populated after the iterator is drained.
    if result.status == "waiting":
        with chat.answer(session["id"], {"approved": True, "note": "Confirmed"},
                         node=result.question.get("node")) as answer:
            for event in answer:
                handle_event(event)
```

`answer` accepts text, a JSON form object, or a boolean approval. v1 bounds text
and serialized form objects to 10000 characters; it does not provide a form
builder. Events are dictionaries following the published v1 schema, with
additional `history` and final `result` events. Unknown event types and duplicate
sequence numbers are ignored. `result.status` may be `ok`, `waiting`, `error`,
`cancelled` or `timeout`; protocol, authentication and network failures raise
typed exceptions. Iterators are lazy: creating a stream opens no socket or run.

```python
from superstep import AsyncClient

async with AsyncClient(base_url="https://superstep.example.com") as client:
    chat = client.chat("support", token=get_user_token)  # callback may be async
    session = await chat.start()
    async with chat.send(session["id"], "Hello") as stream:
        async for event in stream:
            handle_event(event)
    result = stream.result
```

`chat.list()`, `chat.get(session_id)` and `chat.turns(session_id, after=turn_id)`
read this identity's sessions/history. Anonymous clients omit `token`; save
`chat.visitor_token` after the first operation and restore it as `visitor_token`
on a new client. No storage is accessed automatically. Signed and visitor
identities cannot be combined on one chat client. `ChatClient` and
`AsyncChatClient` are also usable directly with `base_url`.

### Files, ratings and transport

Use these operations inside an open client context:

```python
with open("note.txt", "rb") as file:
    attachment = chat.attachments.upload(session["id"], file,
                                         filename="note.txt", content_type="text/plain")
with chat.send(session["id"], "Read this", attachments=[attachment["id"]]) as stream:
    for event in stream:
        handle_event(event)
download = chat.attachments.download(session["id"], attachment["id"])  # httpx.Response
chat.ratings.put(session["id"], stream.result.turn_id, "down", comment="Missing context")
chat.ratings.delete(session["id"], stream.result.turn_id)
# Before sending an attachment: chat.attachments.delete(session_id, attachment_id)
```

Uploads accept bytes or a binary file. A seekable file is rewound on an expiry
retry; a non-rewindable stream cannot safely be retried and raises `ConfigError`.
Async file/rating methods use `await`. The server must enable attachments.

HTTP requests and socket auth frames carry user tokens, never URLs. Chat never
inherits workflow headers, default HTTP authentication, query parameters or
studio cookies from a borrowed HTTP client, and refuses redirects. Configure
`origin` only when your server/native caller needs a matching allowed origin.
`websocket_connect` is injectable; otherwise the optional websockets package
is imported only when streaming. Its automatic proxy selection is disabled;
a custom factory can implement a deployment-specific transport.

### Refresh, recovery and cleanup

A token callback is called for each HTTP/socket authentication, and once more
after `CHAT_TOKEN_EXPIRED`. Only an explicit socket rejection before a run starts
can retry a message. Fixed JWT strings, revoked keys and forbidden origins never
refresh. No network failure triggers a blind message resend.

After completion or interruption, bounded `turns?after=` reads recover persisted
history. Recovery only confirms a new assistant turn for a known run ID. A lost
run acknowledgement or absent persisted result raises `CHAT_STREAM_INTERRUPTED`;
reload history before deciding whether to send again. Stream options:
`timeout=300` seconds (`None` disables the socket deadline), `after`,
`recovery_attempts=20` (0..100) and `recovery_interval=0.25` seconds. HTTP uses
the parent/direct client's timeout separately.

Use `with` / `async with` for deterministic cleanup when stopping iteration
early; `stream.close()` / `await stream.aclose()` is also available. Cancellation
uses `stream.cancel()` or `chat.cancel(session_id=None)` (await async versions),
then drain the iterator for the backend's terminal outcome. Async task
cancellation and parent-client close release active sockets. Cancellation can
race completion: reload history if the outcome is unknown. A stream closed
before completion has no final result. A bare `break` alone does not guarantee
immediate iterator cleanup in Python.

The sync/async contract tests replay the backend recording from TASK-0220 and
share its HS256 token vectors. `scripts/sdk_integration.sh` tests both SDKs
against a temporary backend (including live Python text/form answers, files,
ratings and user isolation). Unit CI covers Python 3.9 and 3.12.

## Configure

A workflow token (`wft_...`) starts runs of one workflow. The workflow owner
creates it in the editor under **More (⋯) → API → Create token**; it is shown
once.

```python
from superstep import Client

client = Client(
    workflow_id="example",
    token="wft_...",
    base_url="https://superstep.example.com",
)
```

Arguments left out are read from `SUPERSTEP_WORKFLOW_ID`, `SUPERSTEP_TOKEN`
and `SUPERSTEP_BASE_URL`. A missing base URL raises `ConfigError`; workflow
operations additionally require a workflow ID/token. Chat-only clients need
only `base_url`.

## Run a workflow

```python
# Start and wait: polls with a growing interval (1 s, 1.5 s, ... up to 10 s).
run = client.run_and_wait({"message": "where is my order A100"}, timeout=120)
print(run.status, run.final_state)

# Or step by step.
started = client.run({"message": "hi"})       # status "queued", poll_url set
current = client.get_run(started.run_id)      # status, final_state, metrics ...
done = client.wait(started.run_id, timeout=60, poll_interval=0.5)

# Let the server wait (up to STUDIO_SYNC_WAIT_MAX seconds, default 30).
run = client.run({"message": "hi"}, mode="sync")
```

`Run.done` is true for every status except `queued` and `running`. Finished
statuses are `ok`, `error`, `cancelled`, `timeout`, `waiting` (paused at a
Human node, see `run.waiting`) and `expired`. `run_and_wait` returns the run
whatever its final status; check `run.status`.

`callback_url=` on `run()` and `run_and_wait()` asks the server to POST the
result to your URL when the run ends.

## Async

```python
import asyncio
from superstep import AsyncClient

async def main():
    async with AsyncClient() as client:  # configured from the environment
        run = await client.run_and_wait({"message": "hi"})
        print(run.final_state)

asyncio.run(main())
```

## Errors

Every API error raises a subclass of `SuperstepError` with `code` (the
API's stable error code), `status`, `message` and `details`.

| Exception | When |
| --- | --- |
| `AuthenticationError` | `401 TRIGGER_TOKEN_INVALID`: missing, wrong or revoked token, or a token of another workflow |
| `NotFoundError` | `404 RUN_NOT_FOUND` |
| `InvalidRequestError` | `400 RUN_INPUT_INVALID`, `CALLBACK_URL_INVALID`; `422 VALIDATION_ERROR` |
| `PayloadTooLargeError` | `413 RUN_INPUT_TOO_LARGE` |
| `RateLimitError` | `429 RATE_LIMITED`; `retry_after` holds the seconds to wait |
| `ServerError` | `5xx` |
| `APIConnectionError` | Network failure, or a response that is not the API envelope |
| `WaitTimeoutError` | `wait` / `run_and_wait` ran out of time; `err.run` is the last state |
| `ConfigError` | Missing base URL, token or workflow id |

```python
from superstep import RateLimitError
import time

try:
    run = client.run({"message": "hi"})
except RateLimitError as err:
    time.sleep(err.retry_after or 1)
```

## Development

```bash
cd sdk/python
pip install -e ".[dev]"
pytest                                   # unit tests, mocked HTTP
```

`tests/test_spec_sync.py` checks the models against the public spec. The live
test (`tests/test_integration.py`) runs when `SUPERSTEP_IT_BASE_URL`,
`SUPERSTEP_IT_TOKEN` and `SUPERSTEP_IT_WORKFLOW_ID` are set;
`scripts/sdk_integration.sh` at the repository root starts a local backend,
creates a token and runs it for both SDKs.

## License

MIT


## Edit a message (0.11.0 target)

After the user confirms that running the current saved workflow may repeat external actions, create a new branch with a stable operation ID:

```python
import uuid

before = chat.get(session_id)
operation_id = uuid.uuid4().hex  # retain for recovery of this same intent
stream = chat.edit(session_id, turn_id, "Corrected request",
    operation_id=operation_id, expected_last_turn_id=before["turns"][-1]["id"])
for event in stream:
    pass
branch_id = stream.result.session_id
```

For `AsyncChatClient`, use `stream = await chat.edit(...)`, then `async for event in stream`. `prepare_edit` prepares only (await it on the async client). Repeated admitted intents recover their reserved run from history without another socket write. The original session remains unchanged; Human questions must be answered again, and all subsequent operations address the branch. Older servers fail clearly when `capabilities.edit` is absent. Full semantics: [English](../../handbook/docs/en/run/chat-api.md#prepare-and-execute-an-edit) / [Tiếng Việt](../../handbook/docs/vi/run/chat-api.md).


Regenerate the latest terminal answer only after confirming that current-workflow actions may repeat:

```python
stream = chat.regenerate(session_id, latest_answer_id,
    operation_id="new-client-generated-unique-id", expected_last_turn_id=latest_answer_id)
for event in stream:
    pass  # ordinary v1 stream/history events
branch_id = stream.result.session_id

# Async client: preparing is awaited, then consume the returned stream.
stream = await async_chat.regenerate(session_id, latest_answer_id,
    operation_id="another-client-generated-unique-id", expected_last_turn_id=latest_answer_id)
async with stream:
    async for event in stream:
        pass
```

`prepare_regenerate` prepares without execution. Support requires `capabilities.regenerate`; only the latest terminal answer is eligible. Keep the same operation ID when recovering one attempt. Files are independent copies, source history stays unchanged, and Human/reviewer questions must be answered again. Reading an admitted intent never resends execution, even after its branch has continued.
