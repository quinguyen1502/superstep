import type { ClientFrame, WebSocketLike } from '@superstep/sdk/chat'

type Turn = {
  id: string
  role: 'user' | 'assistant'
  text: string
  created: number
  inherited: boolean
  editable: boolean
  regeneratable: boolean
  status?: string
  run_id?: string
  node?: string
  rating?: { value: 'up' | 'down'; comment: string; updated: number } | null
}

const base = { created: 1, inherited: false, editable: false, regeneratable: false }

export class FakeSocket implements WebSocketLike {
  readyState = 1
  readonly sent: ClientFrame[] = []
  private listeners = new Map<string, Set<(event: { data?: string }) => void>>()
  constructor(readonly url: string, private readonly harness: Harness) {
    harness.sockets.push(this)
    queueMicrotask(() => this.frame({ type: 'ready', protocol: 'superstep-chat', v: 1, seq: 0 }))
  }
  addEventListener(type: string, listener: (event: { data?: string }) => void) {
    const set = this.listeners.get(type) ?? new Set()
    set.add(listener)
    this.listeners.set(type, set)
  }
  removeEventListener(type: string, listener: (event: { data?: string }) => void) {
    this.listeners.get(type)?.delete(listener)
  }
  send(data: string) {
    const frame = JSON.parse(data) as ClientFrame
    this.sent.push(frame)
    if (frame.type === 'message' || frame.type === 'answer') queueMicrotask(() => this.harness.reply(this, frame))
  }
  close() { this.readyState = 3 }
  frame(frame: unknown) {
    for (const listener of this.listeners.get('message') ?? []) listener({ data: JSON.stringify(frame) })
  }
}

class NativeForm {
  readonly values = new Map<string, unknown>()
  append(key: string, value: unknown) { this.values.set(key, value) }
  get(key: string) { return this.values.get(key) }
}

function envelope(data: unknown) {
  return { ok: true, status: 200, json: async () => ({ success: true, data, error: null }) } as Response
}

export class Harness {
  readonly sockets: FakeSocket[] = []
  readonly calls: { url: string; method: string; body: unknown; authorization?: string }[] = []
  userText = ''
  stage: 'empty' | 'waiting' | 'done' = 'empty'
  rating: Turn['rating'] = null
  readonly Socket: new (url: string) => FakeSocket
  readonly FormData = NativeForm as unknown as typeof FormData
  constructor(readonly question = false) {
    const harness = this
    this.Socket = class extends FakeSocket {
      constructor(url: string) { super(url, harness) }
    }
  }
  reply(socket: FakeSocket, frame: Extract<ClientFrame, { type: 'message' | 'answer' }>) {
    if (frame.type === 'message') this.userText = frame.text
    const ask = frame.type === 'message' && this.question && this.stage === 'empty'
    this.stage = ask ? 'waiting' : 'done'
    const run = ask ? 'run-1' : this.question ? 'run-2' : 'run-1'
    socket.frame({ type: 'run_started', run_id: run, v: 1, seq: 1 })
    if (ask) {
      socket.frame({ type: 'question', v: 1, seq: 2, node: 'ask', label: 'Name', prompt: 'What is your name?', kind: 'text' })
      socket.frame({ type: 'turn', turn_id: 'turn-q', role: 'assistant', status: 'waiting', run_id: run, v: 1, seq: 3 })
      socket.frame({ type: 'done', status: 'waiting', run_id: run, v: 1, seq: 4 })
      return
    }
    socket.frame({ type: 'token', delta: 'Hello', node: 'bot', field: 'reply', v: 1, seq: 2 })
    socket.frame({ type: 'turn', turn_id: 'turn-a', role: 'assistant', status: 'ok', run_id: run, v: 1, seq: 3 })
    socket.frame({ type: 'done', status: 'ok', run_id: run, v: 1, seq: 4 })
  }
  private turns(): Turn[] {
    if (this.stage === 'empty') return []
    const user: Turn = { ...base, id: 'turn-user', role: 'user', text: this.userText, run_id: 'run-1' }
    const waiting: Turn = { ...base, id: 'turn-q', role: 'assistant', text: 'What is your name?', status: 'waiting', run_id: 'run-1', node: 'ask' }
    if (this.stage === 'waiting') return [user, waiting]
    const answer: Turn = { ...base, id: 'turn-a', role: 'assistant', text: 'Hello', status: 'ok', run_id: this.question ? 'run-2' : 'run-1', rating: this.rating }
    return this.question ? [user, waiting, answer] : [user, answer]
  }
  readonly fetch = (async (input: string | URL | Request, init: RequestInit = {}) => {
    const url = new URL(String(input))
    const headers = init.headers as Record<string, string> | undefined
    let body: unknown = init.body
    if (typeof body === 'string') {
      try { body = JSON.parse(body) } catch { /* keep the raw body */ }
    }
    this.calls.push({ url: url.href, method: init.method ?? 'GET', body, authorization: headers?.Authorization })
    if (url.pathname.endsWith('/sessions') && init.method === 'POST') {
      return envelope({ id: 'sess-1', workflow_id: 'wf', channel: 'chat', title: 'Chat', created: 0, updated: 0 })
    }
    if (url.pathname.endsWith('/attachments') && init.method === 'POST') {
      const file = body && typeof body === 'object' && 'get' in body ? (body as NativeForm).get('file') as { name?: string } : undefined
      return envelope({ id: 'file-1', name: file?.name ?? 'note.txt', kind: 'document', mime: 'text/plain', size: 4 })
    }
    if (url.pathname.endsWith('/rating') && init.method === 'PUT') {
      const value = (typeof body === 'object' && body ? body : {}) as { value: 'up' | 'down'; comment?: string }
      this.rating = { value: value.value, comment: value.comment ?? '', updated: 1 }
      return envelope(this.rating)
    }
    if (url.pathname.endsWith('/rating') && init.method === 'DELETE') {
      this.rating = null
      return envelope({ ok: true })
    }
    if (init.method === 'DELETE') return envelope({ ok: true })
    if (url.pathname.endsWith('/turns')) {
      let turns = this.turns()
      const after = url.searchParams.get('after')
      const index = turns.findIndex(turn => turn.id === after)
      if (index >= 0) turns = turns.slice(index + 1)
      return envelope({ turns })
    }
    if (url.pathname.endsWith('/sess-1')) return envelope({ id: 'sess-1', turns: this.turns() })
    return envelope({ title: 'Fixture', slug: 'demo' })
  }) as typeof fetch
  props() {
    return { slug: 'demo', baseUrl: 'https://studio.test', visitorToken: 'fixture-visitor-token', fetch: this.fetch, WebSocket: this.Socket, FormData: this.FormData }
  }
}
