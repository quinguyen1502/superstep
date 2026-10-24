import type { components } from './schema.js'
import { APIConnectionError, ConfigError, WaitTimeoutError, errorFor } from './errors.js'

type Schemas = components['schemas']
export type RunResult = Schemas['RunResult']
export type RunAccepted = Schemas['RunAccepted']
export type RunMetrics = Schemas['RunMetrics']
export type RunWaiting = Schemas['RunWaiting']
export type StartRunRequest = Schemas['StartRunRequest']
export type RunStatus = RunResult['status']
/** A run as returned by `run()` and `getRun()`. A just-queued run has only `run_id`, `status` and `poll_url`. */
export type Run = Partial<Omit<RunResult, 'run_id' | 'status'>> & { run_id: string; status: RunStatus; poll_url?: string }

export const VERSION = '0.1.0'
const PENDING: readonly RunStatus[] = ['queued', 'running']

/** True once the run has stopped changing (any status but `queued` / `running`). */
export const isDone = (run: Pick<Run, 'status'>): boolean => !PENDING.includes(run.status)

export interface ClientOptions {
  /** Defaults to SUPERSTEP_WORKFLOW_ID. */
  workflowId?: string
  /** Workflow token `wft_...`. Defaults to SUPERSTEP_TOKEN. */
  token?: string
  /** e.g. https://superstep.example.com. Defaults to SUPERSTEP_BASE_URL. */
  baseUrl?: string
  /** Custom fetch (tests, proxies). Defaults to globalThis.fetch. */
  fetch?: typeof fetch
}

export interface RequestOptions { signal?: AbortSignal }
export interface RunOptions extends RequestOptions {
  mode?: StartRunRequest['mode']
  callbackUrl?: string
}
export interface WaitOptions extends RequestOptions {
  /** Milliseconds before WaitTimeoutError; default 300000. `null` waits forever. */
  timeoutMs?: number | null
  /** First poll interval in ms; default 1000. */
  pollIntervalMs?: number
  /** Cap for the poll interval in ms; default 10000. */
  maxPollIntervalMs?: number
  /** Growth factor of the poll interval; default 1.5. */
  backoff?: number
}
export interface RunAndWaitOptions extends WaitOptions { callbackUrl?: string }

type Env = Record<string, string | undefined>
const env = (): Env => (globalThis as { process?: { env?: Env } }).process?.env ?? {}

/** initial, initial*factor, ... capped at maximum. */
export function* pollDelays(initial: number, maximum: number, factor: number): Generator<number> {
  if (!(initial > 0) || !(factor >= 1)) throw new RangeError('pollIntervalMs must be > 0 and backoff >= 1')
  for (let delay = initial; ; delay *= factor) yield Math.min(delay, maximum)
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason)
    const onAbort = () => { clearTimeout(timer); reject(signal!.reason) }
    const timer = setTimeout(() => { signal?.removeEventListener('abort', onAbort); resolve() }, ms)
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

export class Superstep {
  readonly workflowId: string
  readonly baseUrl: string
  private readonly token: string
  private readonly fetchImpl: typeof fetch

  constructor(options: ClientOptions = {}) {
    const e = env()
    const values = { workflowId: options.workflowId ?? e.SUPERSTEP_WORKFLOW_ID, token: options.token ?? e.SUPERSTEP_TOKEN, baseUrl: options.baseUrl ?? e.SUPERSTEP_BASE_URL }
    const names = { workflowId: 'SUPERSTEP_WORKFLOW_ID', token: 'SUPERSTEP_TOKEN', baseUrl: 'SUPERSTEP_BASE_URL' } as const
    const missing = (Object.keys(values) as (keyof typeof values)[]).filter((k) => !values[k]).map((k) => `${k} (or ${names[k]})`)
    if (missing.length) throw new ConfigError(`Missing ${missing.join(', ')}`, { code: 'CONFIG_MISSING' })
    this.workflowId = values.workflowId!
    this.token = values.token!
    this.baseUrl = values.baseUrl!.replace(/\/+$/, '')
    const f = options.fetch ?? globalThis.fetch
    if (!f) throw new ConfigError('No fetch available: pass options.fetch (Node 18+ has a global fetch)', { code: 'CONFIG_MISSING' })
    this.fetchImpl = f
  }

  /** Start a run. `async` (default) returns at once with status `queued`; `sync` waits up to the server's limit. */
  run(input: Record<string, unknown> = {}, options: RunOptions = {}): Promise<Run> {
    const mode = options.mode ?? 'async'
    if (mode !== 'async' && mode !== 'sync') throw new RangeError("mode must be 'async' or 'sync'")
    const body: StartRunRequest = { input, mode, ...(options.callbackUrl ? { callback_url: options.callbackUrl } : {}) }
    return this.send('POST', this.runsUrl(), options.signal, body)
  }

  getRun(runId: string, options: RequestOptions = {}): Promise<Run> {
    return this.send('GET', this.runsUrl(runId), options.signal)
  }

  /** Poll until the run is done. */
  async wait(runId: string, options: WaitOptions = {}): Promise<Run> {
    const timeout = options.timeoutMs === undefined ? 300_000 : options.timeoutMs
    const deadline = timeout === null ? null : Date.now() + timeout
    const delays = pollDelays(options.pollIntervalMs ?? 1000, options.maxPollIntervalMs ?? 10_000, options.backoff ?? 1.5)
    for (;;) {
      const run = await this.getRun(runId, options)
      if (isDone(run)) return run
      let delay = delays.next().value as number
      if (deadline !== null) {
        const left = deadline - Date.now()
        if (left <= 0) throw new WaitTimeoutError(`Run ${run.run_id} still ${run.status} after the timeout`, run)
        delay = Math.min(delay, left)
      }
      await sleep(delay, options.signal)
    }
  }

  /** Start a run and poll (interval growing by `backoff` up to `maxPollIntervalMs`) until it is done. */
  async runAndWait(input: Record<string, unknown> = {}, options: RunAndWaitOptions = {}): Promise<Run> {
    const started = await this.run(input, { callbackUrl: options.callbackUrl, signal: options.signal })
    return isDone(started) ? started : this.wait(started.run_id, options)
  }

  private runsUrl(runId?: string): string {
    const url = `${this.baseUrl}/api/hooks/workflows/${encodeURIComponent(this.workflowId)}/runs`
    return runId ? `${url}/${encodeURIComponent(runId)}` : url
  }

  private async send(method: string, url: string, signal?: AbortSignal, body?: unknown): Promise<Run> {
    const headers: Record<string, string> = { 'X-Workflow-Token': this.token, Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    let res: Response
    try {
      res = await this.fetchImpl(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal })
    } catch (err) {
      if (signal?.aborted) throw err  // let AbortError through unchanged
      throw new APIConnectionError(err instanceof Error ? err.message : String(err), { code: 'CONNECTION_ERROR' })
    }
    const payload = await res.json().catch(() => null) as { success?: boolean; data?: Run; error?: { code?: string; message?: string; details?: unknown } } | null
    if (!payload || typeof payload.success !== 'boolean') {
      throw new APIConnectionError(`Unexpected response (HTTP ${res.status}); is baseUrl a Superstep server?`, { code: 'BAD_RESPONSE', status: res.status })
    }
    if (!payload.success) {
      const e = payload.error ?? {}
      throw errorFor(res.status, e.code ?? 'UNKNOWN', e.message ?? `HTTP ${res.status}`, e.details, res.headers)
    }
    return payload.data as Run
  }
}
