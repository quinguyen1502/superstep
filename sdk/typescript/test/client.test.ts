import { describe, expect, it, vi, afterEach } from 'vitest'
import {
  APIConnectionError, AuthenticationError, ConfigError, InvalidRequestError, NotFoundError, PayloadTooLargeError, RateLimitError,
  ServerError, Superstep, SuperstepError, WaitTimeoutError, isDone, pollDelays,
} from '../src/index'

const BASE = 'http://superstep.test', WID = 'wf1', TOKEN = 'wft_test'
const QUEUED = { run_id: 'r1', status: 'queued', poll_url: `${BASE}/api/hooks/workflows/${WID}/runs/r1` }
const DONE = { run_id: 'r1', workflow_id: WID, status: 'ok', source: 'api', final_state: { answer: 42 }, error: null, waiting: null,
  metrics: { duration_ms: 12.5, tokens_in: 1, tokens_out: 2, cost_usd: 0, error_count: 0 }, trace_url: null, started: 1, ended: 2 }
const RUNNING = { ...DONE, status: 'running', final_state: null, ended: null }

const ok = (data: unknown, status = 200) => new Response(JSON.stringify({ success: true, data, error: null }), { status })
const fail = (code: string, status: number, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify({ success: false, data: null, error: { code, message: 'boom', details: [{ field: 'mode' }] } }), { status, headers })

function server(...responses: (Response | (() => Response))[]) {
  const calls: { url: string; init: RequestInit }[] = []
  const fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init: init ?? {} })
    const next = responses.shift()!
    return typeof next === 'function' ? next() : next
  }) as unknown as typeof globalThis.fetch
  return { calls, client: new Superstep({ workflowId: WID, token: TOKEN, baseUrl: `${BASE}/`, fetch }) }
}

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); vi.unstubAllEnvs() })

describe('Superstep', () => {
  it('run sends the token and body and returns the queued run', async () => {
    const { calls, client } = server(ok(QUEUED, 202))
    const run = await client.run({ q: 1 }, { callbackUrl: 'https://hook.example.com' })
    expect(calls[0].url).toBe(`${BASE}/api/hooks/workflows/${WID}/runs`)
    expect(calls[0].init.method).toBe('POST')
    expect((calls[0].init.headers as Record<string, string>)['X-Workflow-Token']).toBe(TOKEN)
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ input: { q: 1 }, mode: 'async', callback_url: 'https://hook.example.com' })
    expect(run.status).toBe('queued'); expect(isDone(run)).toBe(false)
  })

  it('getRun encodes the id and returns the typed result', async () => {
    const { calls, client } = server(ok(DONE))
    const run = await client.getRun('r 1')
    expect(calls[0].url.endsWith('/runs/r%201')).toBe(true)
    expect(run.final_state).toEqual({ answer: 42 }); expect(run.metrics?.duration_ms).toBe(12.5)
  })

  it('runAndWait polls with backoff until done', async () => {
    vi.useFakeTimers()
    const { calls, client } = server(ok(QUEUED, 202), ok(RUNNING), ok(RUNNING), ok(RUNNING), ok(DONE))
    const t0 = Date.now()
    const p = client.runAndWait({}, { pollIntervalMs: 100, backoff: 2, maxPollIntervalMs: 300 })
    await vi.runAllTimersAsync()
    expect((await p).status).toBe('ok')
    expect(Date.now() - t0).toBe(100 + 200 + 300)  // fake clock: the three sleeps
    expect(calls).toHaveLength(5)
  })

  it('wait throws WaitTimeoutError with the last run', async () => {
    const { client } = server(ok(RUNNING), ok(RUNNING))
    const err = await client.wait('r1', { timeoutMs: 0 }).catch((e) => e)
    expect(err).toBeInstanceOf(WaitTimeoutError); expect(err.run.status).toBe('running'); expect(err.code).toBe('WAIT_TIMEOUT')
  })

  it('an AbortSignal stops the request and the polling', async () => {
    const { client } = server(ok(QUEUED, 202), ok(RUNNING), ok(DONE))
    const ctl = new AbortController()
    const p = client.runAndWait({}, { signal: ctl.signal, pollIntervalMs: 60_000 })
    setTimeout(() => ctl.abort(new Error('stop')), 10)
    await expect(p).rejects.toThrow('stop')
    const aborted = new AbortController(); aborted.abort()
    const fetch = vi.fn(async (_u: unknown, init?: RequestInit) => { if (init?.signal?.aborted) throw new DOMException('aborted', 'AbortError'); return ok(DONE) })
    const c2 = new Superstep({ workflowId: WID, token: TOKEN, baseUrl: BASE, fetch: fetch as unknown as typeof globalThis.fetch })
    await expect(c2.getRun('r1', { signal: aborted.signal })).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('sync mode and mode validation', async () => {
    const { calls, client } = server(ok(DONE))
    expect((await client.run({}, { mode: 'sync' })).status).toBe('ok')
    expect(JSON.parse(calls[0].init.body as string).mode).toBe('sync')
    expect(() => client.run({}, { mode: 'later' as never })).toThrow(RangeError)
  })

  it.each([
    ['TRIGGER_TOKEN_INVALID', 401, AuthenticationError], ['RUN_NOT_FOUND', 404, NotFoundError], ['RUN_INPUT_INVALID', 400, InvalidRequestError],
    ['CALLBACK_URL_INVALID', 400, InvalidRequestError], ['VALIDATION_ERROR', 422, InvalidRequestError], ['RUN_INPUT_TOO_LARGE', 413, PayloadTooLargeError],
    ['INTERNAL_ERROR', 500, ServerError], ['SOMETHING_NEW', 503, ServerError], ['SOMETHING_NEW', 418, SuperstepError],
  ] as const)('maps %s / %i to a typed error', async (code, status, Cls) => {
    const { client } = server(fail(code, status))
    const err = await client.getRun('r1').catch((e) => e)
    expect(err.constructor).toBe(Cls); expect(err.code).toBe(code); expect(err.status).toBe(status); expect(err.details).toEqual([{ field: 'mode' }])
  })

  it('RateLimitError exposes retryAfter', async () => {
    const { client } = server(fail('RATE_LIMITED', 429, { 'Retry-After': '7' }))
    const err = await client.run({}).catch((e) => e)
    expect(err).toBeInstanceOf(RateLimitError); expect(err.retryAfter).toBe(7)
  })

  it('non-envelope responses and network failures are APIConnectionError', async () => {
    const { client } = server(new Response('<html>bad gateway</html>', { status: 502 }), () => { throw new TypeError('fetch failed') })
    await expect(client.getRun('r1')).rejects.toMatchObject({ code: 'BAD_RESPONSE' })
    const err = await client.getRun('r1').catch((e) => e)
    expect(err).toBeInstanceOf(APIConnectionError); expect(err.code).toBe('CONNECTION_ERROR')
  })

  it('falls back to environment variables', () => {
    vi.stubEnv('SUPERSTEP_WORKFLOW_ID', ''); vi.stubEnv('SUPERSTEP_TOKEN', ''); vi.stubEnv('SUPERSTEP_BASE_URL', '')
    expect(() => new Superstep()).toThrow(ConfigError)
    vi.stubEnv('SUPERSTEP_WORKFLOW_ID', 'wenv'); vi.stubEnv('SUPERSTEP_TOKEN', 'wft_env'); vi.stubEnv('SUPERSTEP_BASE_URL', 'http://env.test/')
    const c = new Superstep()
    expect(c.workflowId).toBe('wenv'); expect(c.baseUrl).toBe('http://env.test')
    expect(new Superstep({ workflowId: 'arg' }).workflowId).toBe('arg')
  })

  it('pollDelays grows and caps', () => {
    const d = pollDelays(500, 2000, 2)
    expect(Array.from({ length: 5 }, () => d.next().value)).toEqual([500, 1000, 2000, 2000, 2000])
    expect(() => pollDelays(0, 1, 1).next()).toThrow(RangeError)
  })
})
