import { ConfigError } from '../errors.js'
import { abortReason } from '../transport.js'
import type { ChatClient } from './client.js'
import type { ChatStream } from './stream.js'
import type { ChatAnswerOptions, ChatEditOptions, ChatRegenerateOptions, ChatQuestion, ChatRequestOptions, ChatResult, ChatSendOptions, ChatTurn } from './types.js'

export interface ChatState {
  readonly sessionId: string | null
  readonly turns: readonly ChatTurn[]
  readonly status: 'idle' | 'loading' | 'streaming' | 'waiting' | 'error'
  readonly text: string
  readonly question: ChatQuestion | null
  readonly error: unknown
  readonly sourceSessionId?: string | null
}

/** A stable snapshot/subscribe surface shared by React, native bindings and plain JavaScript. */
export function createChatStore(client: ChatClient) {
  let state: ChatState = Object.freeze({ sessionId: null, turns: [], status: 'idle', text: '', question: null, error: null })
  const listeners = new Set<() => void>()
  let generation = 0, active: ChatStream | undefined, disposed = false
  const update = (patch: Partial<ChatState>) => {
    state = Object.freeze({ ...state, ...patch })
    for (const listener of [...listeners]) listener()
  }
  const usable = () => { if (disposed) throw new ConfigError('This chat store has been disposed', { code: 'CHAT_STORE_DISPOSED' }) }
  const merge = (turns: readonly ChatTurn[]) => {
    const byId = new Map(state.turns.map(turn => [turn.id, turn]))
    for (const turn of turns) byId.set(turn.id, turn)
    return Object.freeze([...byId.values()])
  }
  const switchSession = () => { usable(); generation++; void active?.return(); active = undefined; return generation }
  const load = async (sessionId: string, options: ChatRequestOptions = {}) => {
    const mine = switchSession()
    update({ sessionId, sourceSessionId: null, turns: [], text: '', question: null, status: 'loading', error: null })
    try {
      const view = await client.get(sessionId, options)
      if (mine !== generation || disposed) return
      const waiting = view.turns[view.turns.length - 1]?.status === 'waiting'
      update({ turns: Object.freeze([...view.turns]), sourceSessionId: view.source_session_id ?? null, status: waiting ? 'waiting' : 'idle' })
    } catch (error) { if (mine === generation && !disposed) update({ error, status: 'error' }); throw error }
  }
  const start = async (options: ChatRequestOptions & { embed?: boolean } = {}) => {
    const mine = switchSession()
    update({ sessionId: null, sourceSessionId: null, turns: [], text: '', question: null, status: 'loading', error: null })
    try {
      const session = await client.start(options)
      if (mine === generation && !disposed) update({ sessionId: session.id, status: 'idle' })
      return session
    } catch (error) { if (mine === generation && !disposed) update({ error, status: 'error' }); throw error }
  }
  const consume = async (make: (sid: string, after?: string) => ChatStream): Promise<ChatResult> => {
    usable()
    if (active || state.status === 'loading') throw new ConfigError('Wait for the current chat operation to finish', { code: 'CHAT_BUSY' })
    let mine = generation
    if (!state.sessionId) {
      const starting = start(); mine = generation; await starting
      if (mine !== generation || disposed) throw abortReason()
    }
    const stream = make(state.sessionId!, state.turns[state.turns.length - 1]?.id)
    active = stream; update({ text: '', question: null, error: null, status: 'streaming' })
    try {
      for await (const event of stream) {
        if (mine !== generation || disposed) continue
        if (event.type === 'token') update({ text: state.text + event.delta })
        else if (event.type === 'session') update({ sessionId: event.session.id, sourceSessionId: event.session.source_session_id ?? null, turns: Object.freeze([...event.session.turns]), text: '', question: null })
        else if (event.type === 'question') update({ question: event, status: 'waiting' })
        else if (event.type === 'history') update({ turns: merge(event.turns) })
      }
      const result = await stream.result
      if (mine === generation && !disposed) {
        const turns = merge(result.turns), last = turns[turns.length - 1]
        const later = !!last?.run_id && last.run_id !== result.runId
        update({ text: result.text, status: (later ? last.status === 'waiting' : result.status === 'waiting') ? 'waiting' : 'idle',
          ...(later ? { question: null } : {}), turns })
      }
      return result
    } catch (error) { if (mine === generation && !disposed) update({ error, status: 'error' }); throw error }
    finally { if (active === stream) active = undefined }
  }
  return {
    getSnapshot: (): ChatState => state,
    subscribe: (listener: () => void) => { usable(); listeners.add(listener); return () => { listeners.delete(listener) } },
    start, load,
    send: (text: string, options: ChatSendOptions = {}) => consume((sid, after) => client.send(sid, text, { after, ...options })),
    edit: (turn: string, text: string, options: ChatEditOptions) => consume(sid => client.edit(sid, turn, text, options)),
    regenerate: (turn: string, options: ChatRegenerateOptions) => consume(sid => client.regenerate(sid, turn, options)),
    answer: (response: Parameters<ChatClient['answer']>[1], options: ChatAnswerOptions = {}) => consume((sid, after) => client.answer(sid, response, { after, node: state.question?.node ?? undefined, ...options })),
    cancel: () => active?.cancel(),
    dispose: () => { if (!disposed) { generation++; void active?.return(); active = undefined; listeners.clear(); disposed = true } },
  }
}
export type ChatStore = ReturnType<typeof createChatStore>
