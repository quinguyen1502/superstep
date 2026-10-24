# @superstep/sdk (TypeScript SDK)

TypeScript client for the Superstep public API: start a workflow run from your
own service, poll it, and read its final state. Built on `fetch`, zero
runtime dependencies, ESM and CommonJS, types generated from the public
OpenAPI spec. Works in Node 18+, Deno, Bun, edge runtimes and browsers.

- Guide: <https://quinguyen1502.github.io/superstep/run/public-api/>
- API reference: <https://quinguyen1502.github.io/superstep/reference/public-api/>
- Spec: [`docs/api/openapi.public.json`](../../docs/api/openapi.public.json)

## Install

```bash
npm install @superstep/sdk
```

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
and `SUPERSTEP_BASE_URL` when `process.env` exists. A missing value throws
`ConfigError`. Pass `fetch` to use a custom implementation.

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
| `AuthenticationError` | `401 TRIGGER_TOKEN_INVALID`: missing, wrong or revoked token, or a token of another workflow |
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
`operations` and `components` are exported. `src/schema.ts` is generated
from the public spec:

```bash
npm run gen         # regenerate src/schema.ts
npm run gen:check   # fail when it is out of date (CI)
```

## Development

```bash
cd sdk/typescript
npm ci
npm test            # unit tests, mocked fetch
npm run build       # dist/esm and dist/cjs
```

The live test (`test/integration.test.ts`) runs when `SUPERSTEP_IT_BASE_URL`,
`SUPERSTEP_IT_TOKEN` and `SUPERSTEP_IT_WORKFLOW_ID` are set;
`scripts/sdk_integration.sh` at the repository root starts a local backend
and runs it for both SDKs.

## License

MIT
