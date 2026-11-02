import { APIConnectionError, AuthenticationError, errorFor } from '../errors.js'
import { abortReason, checkAbort } from '../transport.js'
import { DONE_STATUSES, SERVER_TYPES } from './frames.js'
import type { ClientFrame, ServerFrame } from './frames.js'
import type { ChatQuestion, ChatStreamOptions, WebSocketConstructor } from './types.js'
import type { StreamControl } from './stream.js'

export class Interrupted extends APIConnectionError {
  constructor(readonly runId?: string) { super('Chat connection ended before a terminal result; the message was not resent', { code: 'CHAT_STREAM_INTERRUPTED' }) }
}
/** Only an explicit pre-execution auth rejection may resend a frame after refreshing. */
export class RetryExpired extends AuthenticationError {}
type Done = Extract<ServerFrame, { type: 'done' }>
export interface SocketResult { done: Done; runId?: string; turnId?: string; text: string; question?: ChatQuestion }

/** Unknown v1 types are additive. Known frames still need the fields used by the client. */
export function decodeFrame(data: unknown): ServerFrame | undefined {
  const bad = () => new APIConnectionError('Invalid chat socket frame', { code: 'BAD_RESPONSE' })
  if (typeof data !== 'string' || data.length > 4 * 1024 * 1024) throw bad()
  let frame: any
  try { frame = JSON.parse(data) } catch { throw bad() }
  if (!frame || typeof frame !== 'object' || typeof frame.type !== 'string') throw bad()
  if (!(SERVER_TYPES as readonly string[]).includes(frame.type)) return undefined
  if (frame.v !== 1 || !Number.isSafeInteger(frame.seq) || frame.seq < 0) throw bad()
  if (frame.type === 'ready' && frame.protocol !== 'superstep-chat') throw bad()
  if (frame.type === 'run_started' && typeof frame.run_id !== 'string') throw bad()
  if (frame.type === 'token' && typeof frame.delta !== 'string') throw bad()
  if (frame.type === 'step' && (typeof frame.node !== 'string' || !['started', 'finished', 'error'].includes(frame.event))) throw bad()
  if (frame.type === 'turn' && (typeof frame.turn_id !== 'string' || frame.role !== 'assistant')) throw bad()
  if (frame.type === 'done' && !(DONE_STATUSES as readonly string[]).includes(frame.status)) throw bad()
  if (frame.type === 'error' && (!frame.error || typeof frame.error.code !== 'string' || typeof frame.error.message !== 'string')) throw bad()
  return frame as ServerFrame
}

export function socketRequest(Socket: WebSocketConstructor, url: string, auth: Extract<ClientFrame, { type: 'auth' }>,
  request: Extract<ClientFrame, { type: 'message' | 'answer' }>, options: ChatStreamOptions, control: StreamControl,
  retryExpired: boolean): Promise<SocketResult> {
  checkAbort(control.signal)
  const timeout = options.timeoutMs === undefined ? 300_000 : options.timeoutMs
  if (timeout !== null && (!(timeout > 0) || !Number.isFinite(timeout))) throw new RangeError('timeoutMs must be positive or null')
  return new Promise((resolve, reject) => {
    let socket: InstanceType<WebSocketConstructor>
    try { socket = new Socket(url) } catch { reject(new APIConnectionError('Cannot open the chat socket', { code: 'CONNECTION_ERROR' })); return }
    let settled = false, sent = false, seq = -1, runId: string | undefined, turnId: string | undefined, text = '', question: ChatQuestion | undefined
    let timer: ReturnType<typeof setTimeout> | undefined
    const cleanup = () => {
      clearTimeout(timer); control.setCancel(); control.signal.removeEventListener('abort', abort)
      socket.removeEventListener('message', message); socket.removeEventListener('error', failed); socket.removeEventListener('close', closed)
      try { socket.close() } catch { /* already closed */ }
    }
    const fail = (error: unknown, stop = false) => {
      if (settled) return
      settled = true
      try { if (stop) cancel() } finally { cleanup(); reject(error) }
    }
    const cancel = () => {
      try { if (socket.readyState === 1 && sent) socket.send(JSON.stringify({ type: 'cancel' } satisfies ClientFrame)) }
      catch { fail(new Interrupted(runId)) }
    }
    const abort = () => fail(abortReason(control.signal), true)
    const failed = () => fail(new Interrupted(runId))
    const closed = () => fail(new Interrupted(runId))
    const message = (event: { data: unknown }) => {
      if (settled) return
      try {
        const frame = decodeFrame(event.data)
        if (!frame || frame.seq <= seq) return
        seq = frame.seq
        if (frame.type === 'error') {
          const error = errorFor(frame.error.code === 'CHAT_TOKEN_EXPIRED' ? 401 : 400, frame.error.code, frame.error.message, frame.error.details)
          if (retryExpired && !runId && frame.error.code === 'CHAT_TOKEN_EXPIRED') {
            fail(new RetryExpired(error.message, { code: error.code, status: error.status, details: error.details })); return
          }
          control.emit(frame); fail(error); return
        }
        control.emit(frame)
        if (frame.type === 'ready' && !sent) {
          socket.send(JSON.stringify(auth)); socket.send(JSON.stringify(request)); sent = true; control.setCancel(cancel)
        } else if (frame.type === 'run_started') runId = frame.run_id
        else if (frame.type === 'token') {
          text += frame.delta
          if (text.length > 8 * 1024 * 1024) throw new APIConnectionError('Chat answer exceeds the client text limit', { code: 'CHAT_RESPONSE_TOO_LARGE' })
        } else if (frame.type === 'turn') turnId = frame.turn_id
        else if (frame.type === 'question') question = frame
        else if (frame.type === 'done') {
          settled = true; cleanup(); resolve({ done: frame, runId: frame.run_id ?? runId, turnId, text, question })
        }
      } catch (error) { fail(error) }
    }
    socket.addEventListener('message', message); socket.addEventListener('error', failed); socket.addEventListener('close', closed)
    control.signal.addEventListener('abort', abort, { once: true })
    if (timeout !== null) timer = setTimeout(() => fail(new APIConnectionError('Chat socket deadline exceeded', { code: 'CHAT_STREAM_TIMEOUT' }), true), timeout)
    if (control.signal.aborted) abort()
  })
}
