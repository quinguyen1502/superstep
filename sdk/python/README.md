# superstep (Python SDK)

Python client for the Superstep public API: start a workflow run from your own
service, poll it, and read its final state. Sync and async clients, typed
models and typed errors; the only dependency is `httpx`.

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
and `SUPERSTEP_BASE_URL`. A missing value raises `ConfigError`.

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
