import { APIConnectionError, ConfigError, SuperstepError } from '../errors.js'
import { abortable, checkAbort, envelope } from '../transport.js'
import { DONE_STATUSES } from './frames.js'
import type { ClientFrame } from './frames.js'
import { Interrupted, RetryExpired, socketRequest } from './socket.js'
import { ChatStream } from './stream.js'
import type { StreamControl } from './stream.js'
import type { ChatAnswerOptions, ChatClientOptions, ChatFile, ChatPage, ChatRating, ChatRequestOptions, ChatResult, ChatSendOptions,
  ChatSession, ChatSessionList, ChatSessionView, ChatStreamOptions, ChatTurn, ChatTurns, ChatUploadOptions, NativeChatFile, WebSocketConstructor } from './types.js'

function segment(value: string): string {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9_-]{1,200}$/.test(value)) throw new ConfigError('Invalid chat resource identifier', { code: 'CONFIG_INVALID' })
  return encodeURIComponent(value)
}
function baseUrl(value: string): string {
  let url: URL
  try { url = new URL(value) } catch { throw new ConfigError('baseUrl must be an absolute HTTP URL', { code: 'CONFIG_INVALID' }) }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new ConfigError('baseUrl must be an HTTP URL without credentials, query or fragment', { code: 'CONFIG_INVALID' })
  return url.href.replace(/\/+$/, '')
}
const bad = () => new APIConnectionError('Invalid chat response', { code: 'BAD_RESPONSE' })

export class ChatClient {
  readonly slug: string
  readonly baseUrl: string
  private readonly root: string
  private readonly fetchImpl: typeof fetch
  private visitor: string
  private bootstrap?: Promise<ChatSessionList>
  private readonly active = new Map<ChatStream, string>()

  constructor(slug: string, private readonly options: ChatClientOptions) {
    this.slug = slug; this.root = `/api/public/v1/chat/${segment(slug)}`; this.baseUrl = baseUrl(options.baseUrl)
    if (options.getToken && options.visitorToken) throw new ConfigError('Use either getToken or visitorToken for one chat client', { code: 'CONFIG_INVALID' })
    this.fetchImpl = (options.fetch ?? globalThis.fetch)?.bind(globalThis)
    if (!this.fetchImpl) throw new ConfigError('No fetch available: pass options.fetch', { code: 'CONFIG_MISSING' })
    this.visitor = options.visitorToken ?? 'new'
    this.validateToken(this.visitor)
  }

  /** Save this anonymous identity in host-controlled storage if persistence is needed. */
  get visitorToken(): string | undefined { return this.visitor === 'new' || this.options.getToken ? undefined : this.visitor }

  info(options: ChatRequestOptions = {}): Promise<ChatPage> { return this.json('', 'GET', undefined, options.signal) }

  async start(options: ChatRequestOptions & { embed?: boolean } = {}): Promise<ChatSession> {
    await this.identity(options.signal)
    return this.json('/sessions', 'POST', { embed: options.embed ?? false }, options.signal)
  }

  async list(options: ChatRequestOptions = {}): Promise<ChatSessionList> {
    const initial = await this.identity(options.signal)
    return initial ?? this.json('/sessions', 'GET', undefined, options.signal)
  }

  async get(sessionId: string, options: ChatRequestOptions = {}): Promise<ChatSessionView> {
    await this.identity(options.signal)
    return this.json(`/sessions/${segment(sessionId)}`, 'GET', undefined, options.signal)
  }

  async turns(sessionId: string, options: ChatRequestOptions & { after?: string } = {}): Promise<ChatTurns> {
    await this.identity(options.signal)
    const query = options.after ? `?after=${segment(options.after)}` : ''
    const result = await this.json<ChatTurns>(`/sessions/${segment(sessionId)}/turns${query}`, 'GET', undefined, options.signal)
    if (!Array.isArray(result?.turns)) throw bad()
    return result
  }

  send(sessionId: string, text: string, options: ChatSendOptions = {}): ChatStream {
    segment(sessionId)
    if (typeof text !== 'string') throw new ConfigError('Chat text must be a string', { code: 'CONFIG_INVALID' })
    const frame: Extract<ClientFrame, { type: 'message' }> = { type: 'message', chat_session_id: sessionId, text,
      ...(options.attachments ? { attachments: options.attachments.map(id => { segment(id); return id }) } : {}), ...(options.locale ? { locale: options.locale } : {}) }
    return this.stream(sessionId, frame, options)
  }

  answer(sessionId: string, response: Extract<ClientFrame, { type: 'answer' }>['response'], options: ChatAnswerOptions = {}): ChatStream {
    segment(sessionId)
    const frame: Extract<ClientFrame, { type: 'answer' }> = { type: 'answer', chat_session_id: sessionId, response,
      ...(options.node ? { node: options.node } : {}), ...(options.locale ? { locale: options.locale } : {}) }
    return this.stream(sessionId, frame, options)
  }

  cancel(sessionId?: string): void { for (const [stream, id] of this.active) if (!sessionId || id === sessionId) stream.cancel() }

  readonly attachments = {
    upload: async (sessionId: string, file: ChatFile, options: ChatUploadOptions = {}) => {
      await this.identity(options.signal)
      const Form = this.options.FormData ?? globalThis.FormData
      if (!Form) throw new ConfigError('No FormData available: pass options.FormData', { code: 'CONFIG_MISSING' })
      const form = new Form()
      if (file && typeof (file as NativeChatFile).uri === 'string') {
        const native = file as NativeChatFile
        if (!native.uri || !native.name || !native.type) throw new ConfigError('Native files need uri, name and type', { code: 'CONFIG_INVALID' })
        // RN's FormData accepts this native descriptor; it must be forwarded without JSON encoding or fetching its URI.
        form.append('file', native as unknown as Blob)
        if (typeof form.get === 'function' && typeof form.get('file') === 'string') throw new ConfigError('Native files require a native FormData implementation', { code: 'CONFIG_INVALID' })
      } else {
        const BlobImpl = this.options.Blob ?? globalThis.Blob
        let blob: Blob
        if (file && typeof (file as Blob).slice === 'function' && typeof (file as Blob).size === 'number') blob = file as Blob
        else if (BlobImpl && (file instanceof Uint8Array || file instanceof ArrayBuffer)) {
          const bytes = new Uint8Array(file instanceof ArrayBuffer ? file : new Uint8Array(file).buffer)
          blob = new BlobImpl([bytes], { type: options.type ?? 'application/octet-stream' })
        } else throw new ConfigError('Upload needs a Blob, bytes, or a native file descriptor', { code: 'CONFIG_INVALID' })
        form.append('file', blob, options.name ?? (typeof (file as File).name === 'string' ? (file as File).name : 'upload.bin'))
      }
      return this.request<import('./types.js').ChatAttachment>(`/sessions/${segment(sessionId)}/attachments`, 'POST', form, options.signal)
    },
    download: async (sessionId: string, attachmentId: string, options: ChatRequestOptions = {}): Promise<Response> => {
      await this.identity(options.signal)
      return this.request(`/sessions/${segment(sessionId)}/attachments/${segment(attachmentId)}`, 'GET', undefined, options.signal, true)
    },
    delete: async (sessionId: string, attachmentId: string, options: ChatRequestOptions = {}): Promise<{ ok: boolean }> => {
      await this.identity(options.signal)
      return this.json(`/sessions/${segment(sessionId)}/attachments/${segment(attachmentId)}`, 'DELETE', undefined, options.signal)
    },
  }

  readonly ratings = {
    put: async (sessionId: string, turnId: string, value: 'up' | 'down', options: ChatRequestOptions & { comment?: string } = {}): Promise<ChatRating> => {
      await this.identity(options.signal)
      return this.json(`/sessions/${segment(sessionId)}/turns/${segment(turnId)}/rating`, 'PUT', { value, ...(options.comment !== undefined ? { comment: options.comment } : {}) }, options.signal)
    },
    delete: async (sessionId: string, turnId: string, options: ChatRequestOptions = {}): Promise<{ ok: boolean }> => {
      await this.identity(options.signal)
      return this.json(`/sessions/${segment(sessionId)}/turns/${segment(turnId)}/rating`, 'DELETE', undefined, options.signal)
    },
  }

  private validateToken(token: string): void {
    if (typeof token !== 'string' || !token || token.length > 8192 || /[\x00-\x20\x7f]/.test(token)) throw new ConfigError('Invalid chat authentication token', { code: 'CONFIG_INVALID' })
  }

  private async auth(signal?: AbortSignal): Promise<Extract<ClientFrame, { type: 'auth' }>> {
    checkAbort(signal)
    if (!this.options.getToken) return { type: 'auth', visitor: this.visitor }
    const token = await abortable(Promise.resolve().then(() => this.options.getToken!()), signal)
    this.validateToken(token); return { type: 'auth', token }
  }

  /** Bootstrap an anonymous identity only once, even when initial operations overlap. */
  private async identity(signal?: AbortSignal): Promise<ChatSessionList | undefined> {
    checkAbort(signal)
    if (this.options.getToken || this.visitor !== 'new') return undefined
    if (!this.bootstrap) {
      this.bootstrap = this.json<ChatSessionList>('/sessions', 'GET').then(result => {
        if (!Array.isArray(result?.sessions) || !this.visitorToken) throw bad()
        return result
      }).finally(() => { this.bootstrap = undefined })
    }
    return abortable(this.bootstrap, signal)
  }

  private json<T>(path: string, method: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    return this.request(path, method, body === undefined ? undefined : JSON.stringify(body), signal)
  }

  private async request<T>(path: string, method: string, body?: BodyInit, signal?: AbortSignal, binary = false): Promise<T> {
    for (let attempt = 0; ; attempt++) {
      const auth = await this.auth(signal)
      const headers: Record<string, string> = { Accept: binary ? 'application/octet-stream' : 'application/json' }
      if ('token' in auth) headers.Authorization = `Bearer ${auth.token}`
      else headers['X-Chat-Visitor'] = auth.visitor!
      if (typeof body === 'string') headers['Content-Type'] = 'application/json'
      let response: Response
      try { response = await this.fetchImpl(this.baseUrl + this.root + path, { method, headers, body, signal, credentials: 'omit', redirect: 'error' }) }
      catch (error) {
        checkAbort(signal)
        throw new APIConnectionError('The request could not reach the Superstep server', { code: 'CONNECTION_ERROR' })
      }
      try {
        if (binary && response.ok) return response as T
        const data = await envelope<T>(response)
        const visitor = data && typeof data === 'object' ? (data as { visitor_token?: unknown }).visitor_token : undefined
        if (!this.options.getToken && visitor !== undefined) {
          this.validateToken(visitor as string); this.visitor = visitor as string; this.options.onVisitorToken?.(this.visitor)
        }
        return data
      } catch (error) {
        checkAbort(signal)
        if (attempt === 0 && this.options.getToken && error instanceof SuperstepError && error.status === 401 && error.code === 'CHAT_TOKEN_EXPIRED') continue
        throw error
      }
    }
  }

  private stream(sessionId: string, frame: Extract<ClientFrame, { type: 'message' | 'answer' }>, options: ChatStreamOptions): ChatStream {
    let stream: ChatStream
    stream = new ChatStream(async control => {
      try { return await this.runStream(sessionId, frame, options, control) }
      finally { this.active.delete(stream) }
    }, options.signal)
    this.active.set(stream, sessionId); return stream
  }

  private async runStream(sessionId: string, frame: Extract<ClientFrame, { type: 'message' | 'answer' }>, options: ChatStreamOptions, control: StreamControl): Promise<ChatResult> {
    const attempts = options.recoveryAttempts ?? 20, interval = options.recoveryIntervalMs ?? 250
    if (!Number.isInteger(attempts) || attempts < 0 || attempts > 100 || !Number.isFinite(interval) || interval < 0) throw new RangeError('Invalid recovery limits')
    const before = await this.get(sessionId, { signal: control.signal })
    if (!Array.isArray(before?.turns)) throw bad()
    const known = new Set(before.turns.map(turn => turn.id))
    let cursor = options.after ?? before.turns[before.turns.length - 1]?.id
    const Socket = this.options.WebSocket ?? globalThis.WebSocket as WebSocketConstructor | undefined
    if (!Socket) throw new ConfigError('No WebSocket available: pass options.WebSocket (Node 18 needs an adapter)', { code: 'CONFIG_MISSING' })
    const url = new URL(this.baseUrl + `/ws/public/v1/chat/${segment(this.slug)}`)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    let output: Awaited<ReturnType<typeof socketRequest>> | undefined, interrupted: Interrupted | undefined
    for (let attempt = 0; ; attempt++) {
      const auth = await this.auth(control.signal)
      try { output = await socketRequest(Socket, url.href, auth, frame, options, control, attempt === 0 && !!this.options.getToken); break }
      catch (error) {
        if (attempt === 0 && error instanceof RetryExpired) continue
        if (error instanceof Interrupted) { interrupted = error; break }
        throw error
      }
    }
    const runId = output?.runId ?? interrupted?.runId
    const recovered: ChatTurn[] = []
    let saved: ChatTurn | undefined
    for (let i = 0; i < attempts; i++) {
      checkAbort(control.signal)
      const page = await this.turns(sessionId, { after: cursor, signal: control.signal })
      if (page.turns.length) {
        recovered.push(...page.turns); cursor = page.turns[page.turns.length - 1].id
        control.emit({ type: 'history', turns: page.turns })
        saved = page.turns.find(turn => !known.has(turn.id) && turn.role === 'assistant' && !!runId && turn.run_id === runId &&
          (DONE_STATUSES as readonly string[]).includes(turn.status ?? ''))
      }
      if (saved || !runId) break
      if (i + 1 < attempts) await abortable(new Promise(resolve => setTimeout(resolve, interval)), control.signal)
    }
    if (!output && !saved) throw interrupted ?? new Interrupted(runId)
    return { sessionId, runId, turnId: saved?.id ?? output?.turnId, status: (saved?.status ?? output!.done.status) as ChatResult['status'],
      text: saved?.text ?? output?.text ?? '', turns: recovered, question: output?.question, recovered: !!interrupted }
  }
}
