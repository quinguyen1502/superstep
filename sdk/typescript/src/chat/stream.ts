import { APIConnectionError, ConfigError } from '../errors.js'
import { abortReason } from '../transport.js'
import type { ChatEvent, ChatResult } from './types.js'

export interface StreamControl {
  signal: AbortSignal
  emit(event: ChatEvent): void
  setCancel(callback?: () => void): void
}

/** A single-consumer event stream. Always drain it; result is also yielded as the last event. */
export class ChatStream implements AsyncIterable<ChatEvent>, AsyncIterator<ChatEvent> {
  readonly result: Promise<ChatResult>
  private readonly controller = new AbortController()
  private queue: ChatEvent[] = []
  private waiters: { resolve: (value: IteratorResult<ChatEvent>) => void; reject: (error: unknown) => void }[] = []
  private ended = false
  private failed = false
  private error: unknown
  private consumed = false
  private cancelSocket?: () => void
  private connected = false

  constructor(produce: (control: StreamControl) => Promise<ChatResult>, signal?: AbortSignal) {
    const abort = () => this.controller.abort(abortReason(signal))
    if (signal?.aborted) abort()
    else signal?.addEventListener('abort', abort, { once: true })
    this.result = Promise.resolve().then(() => produce({ signal: this.controller.signal, emit: event => this.emit(event), setCancel: callback => { this.cancelSocket = callback; if (callback) this.connected = true } }))
      .then(result => { this.emit({ type: 'result', result }); this.end(); return result })
      .catch(error => { this.end(error); throw error })
      .finally(() => { signal?.removeEventListener('abort', abort); this.cancelSocket = undefined })
    // Consumers may first await events and only later await result; do not generate an unhandled rejection.
    void this.result.catch(() => {})
  }

  [Symbol.asyncIterator](): AsyncIterator<ChatEvent> {
    if (this.consumed) throw new ConfigError('A chat stream can only have one consumer', { code: 'CHAT_STREAM_CONSUMED' })
    this.consumed = true; return this
  }

  next(): Promise<IteratorResult<ChatEvent>> {
    if (this.queue.length) return Promise.resolve({ value: this.queue.shift()!, done: false })
    if (this.ended) return this.failed ? Promise.reject(this.error) : Promise.resolve({ value: undefined, done: true })
    return new Promise((resolve, reject) => this.waiters.push({ resolve, reject }))
  }

  /** Stop the run over the socket. Before connection, abort locally without sending a message. */
  cancel(): void {
    if (this.ended) return
    if (this.cancelSocket) this.cancelSocket()
    else if (!this.connected) this.controller.abort(abortReason())
  }

  return(): Promise<IteratorResult<ChatEvent>> {
    this.controller.abort(abortReason()); this.queue = []
    return Promise.resolve({ value: undefined, done: true })
  }

  private emit(event: ChatEvent): void {
    if (this.ended) return
    const waiter = this.waiters.shift()
    if (waiter) { waiter.resolve({ value: event, done: false }); return }
    if (this.queue.length >= 1024) throw new APIConnectionError('Chat event buffer is full; consume the async iterator', { code: 'CHAT_BUFFER_FULL' })
    this.queue.push(event)
  }

  private end(error?: unknown): void {
    this.ended = true; this.failed = error !== undefined; this.error = error
    for (const waiter of this.waiters.splice(0)) {
      if (this.failed) waiter.reject(error)
      else waiter.resolve({ value: undefined, done: true })
    }
  }
}
