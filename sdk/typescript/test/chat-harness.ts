import { readFileSync } from 'node:fs'
import { URL as FileURL } from 'node:url'
import { ChatClient } from '../src/chat/index'
import type { ClientFrame, ServerFrame, WebSocketLike } from '../src/chat/index'

export const recorded = JSON.parse(readFileSync(new FileURL('./fixtures/chat-v1-recorded.json', import.meta.url), 'utf8'))
const BlobImpl = globalThis.Blob, FormImpl = globalThis.FormData
class NativeBlob {
  readonly size: number
  constructor(parts: Uint8Array[], readonly options: unknown) { this.size = parts.reduce((n, part) => n + part.byteLength, 0) }
  slice() { return this }
}
class NativeForm {
  private values = new Map<string, unknown>()
  append(key: string, value: { size: number }, name?: string) { this.values.set(key, name ? { size: value.size, name } : value) }
  get(key: string) { return this.values.get(key) }
}
// The injected fetch surface must not depend on Node's Buffer when simulating native.
const response = (data: unknown, status: number) => ({ ok: status < 400, status, json: async () => data }) as Response
export const ok = (data: unknown) => response({ success: true, data, error: null }, 200)
export const failure = (code: string, status = 401) => response({ success: false, data: null, error: { code, message: 'Fixture rejection' } }, status)
export const SID = 'recorded-session'
export type Script = (socket: TestSocket, request: ClientFrame, wire: Wire) => void

export class TestSocket implements WebSocketLike {
  readyState = 1
  readonly sent: ClientFrame[] = []
  private listeners = new Map<string, Set<(event: any) => void>>()
  constructor(readonly url: string, private wire: Wire, private script?: Script) {
    queueMicrotask(() => this.frame(recorded.frames[0]))
  }
  addEventListener(type: string, listener: (event: any) => void) { if (!this.listeners.has(type)) this.listeners.set(type, new Set()); this.listeners.get(type)!.add(listener) }
  removeEventListener(type: string, listener: (event: any) => void) { this.listeners.get(type)?.delete(listener) }
  dispatch(type: string, event: unknown) { for (const listener of [...this.listeners.get(type) ?? []]) listener(event) }
  frame(frame: unknown) { if (this.readyState === 1) this.dispatch('message', { data: JSON.stringify(frame) }) }
  send(data: string) {
    const frame = JSON.parse(data) as ClientFrame; this.sent.push(frame)
    if (frame.type === 'message' || frame.type === 'answer') {
      this.wire.writes++
      queueMicrotask(() => {
        if (this.script) this.script(this, frame, this.wire)
        else { this.wire.saved = true; for (const event of recorded.frames.slice(1)) this.frame(event) }
      })
    } else if (frame.type === 'cancel') {
      this.wire.cancels++; this.wire.status = 'cancelled'; this.wire.saved = true
      this.frame({ type: 'done', v: 1, seq: 100, status: 'cancelled', run_id: 'recorded-run' })
    }
  }
  close() { if (this.readyState !== 3) { this.readyState = 3; this.dispatch('close', {}) } }
  listenerCount() { return [...this.listeners.values()].reduce((n, listeners) => n + listeners.size, 0) }
}

export class Wire {
  saved = false
  status = 'ok'
  writes = 0
  cancels = 0
  readonly sockets: TestSocket[] = []
  readonly calls: { url: string; init: RequestInit }[] = []
  override?: (url: URL, init: RequestInit) => Response | undefined | Promise<Response | undefined>
  readonly Socket: new (url: string) => TestSocket
  constructor(scripts: Script[] = []) {
    const wire = this
    this.Socket = class extends TestSocket {
      constructor(url: string) { super(url, wire, scripts[wire.sockets.length]); wire.sockets.push(this) }
    }
  }
  readonly fetch = (async (input: string | URL | Request, init: RequestInit = {}) => {
    const url = new URL(String(input)); this.calls.push({ url: url.href, init })
    const override = await this.override?.(url, init)
    if (override) return override
    const visitor = (init.headers as Record<string, string>)?.['X-Chat-Visitor'] === 'new' ? { visitor_token: 'fixture-visitor-token' } : {}
    if (url.pathname.endsWith('/sessions') && init.method === 'GET') return ok({ sessions: [], ...visitor })
    if (url.pathname.endsWith('/sessions')) return ok({ ...recorded.session, turns: undefined, ...visitor })
    if (url.pathname.endsWith('/turns')) {
      let turns = this.saved ? recorded.session.turns.map((turn: any) => turn.role === 'assistant' ? { ...turn, status: this.status } : turn) : []
      const index = turns.findIndex((turn: any) => turn.id === url.searchParams.get('after'))
      if (index >= 0) turns = turns.slice(index + 1)
      return ok({ turns })
    }
    if (url.pathname.endsWith('/' + SID)) return ok({ ...recorded.session, turns: this.saved ? recorded.session.turns : [] })
    if (url.pathname.endsWith('/attachments') && init.method === 'POST') return ok({ id: 'file-fixture', name: 'file.txt', kind: 'document', mime: 'text/plain', size: 3 })
    if (url.pathname.includes('/attachments/') && init.method === 'GET') return { ok: true, status: 200, text: async () => 'abc' } as Response
    if (init.method === 'DELETE') return ok({ ok: true })
    if (url.pathname.endsWith('/rating')) return ok({ ...JSON.parse(String(init.body)), updated: 1 })
    return ok({ title: 'SDK fixture', slug: 'sdk-fixture' })
  }) as typeof fetch
  client(options: Partial<ConstructorParameters<typeof ChatClient>[1]> = {}) {
    return new ChatClient('sdk-fixture', { baseUrl: 'https://superstep.test', visitorToken: 'fixture-visitor-token', fetch: this.fetch,
      WebSocket: this.Socket, Blob: (globalThis.Blob ? BlobImpl : NativeBlob) as typeof Blob,
      FormData: (globalThis.FormData ? FormImpl : NativeForm) as typeof FormData, ...options })
  }
}
export async function collect(stream: AsyncIterable<unknown>) { const result: unknown[] = []; for await (const event of stream) result.push(event); return result as any[] }
export const holding: Script = socket => socket.frame({ type: 'run_started', v: 1, seq: 1, run_id: 'recorded-run' })
