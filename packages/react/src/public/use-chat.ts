import { useEffect, useLayoutEffect, useMemo, useRef, useSyncExternalStore } from 'react'
import { ChatClient, createChatStore, type ChatClientOptions, type ChatPage, type ChatSession, type ChatAttachment, type ChatResult, type ChatQuestion, type ChatState } from '@superstep/sdk/chat'

export interface UseChatOptions extends ChatClientOptions {
  slug: string
  /** Change this key (or remount) when the signed-in person changes. Refreshing a token does not change identity. */
  identityKey?: string | number
  /** undefined restores the latest chat; null starts empty; a string loads that session. */
  sessionId?: string | null
  locale?: 'en' | 'vi'
  embed?: boolean
}
type Extra = { page: ChatPage | null; sessions: readonly ChatSession[]; loading: boolean; operation: boolean; error: unknown; pending: string | null; pendingFiles: ChatAttachment[] }
let nextResource = 0
const useCommit = typeof window === 'undefined' ? useEffect : useLayoutEffect

function resource(client: ChatClient) {
  const store = createChatStore(client), listeners = new Set<() => void>()
  let extra: Extra = { page: null, sessions: [], loading: true, operation: false, error: null, pending: null, pendingFiles: [] }
  let cached = { ...store.getSnapshot(), ...extra, error: null as unknown }
  const publish = () => { cached = { ...store.getSnapshot(), ...extra, error: extra.error ?? store.getSnapshot().error }; for (const f of [...listeners]) f() }
  const off = store.subscribe(publish)
  const patch = (value: Partial<Extra>) => { extra = { ...extra, ...value }; publish() }
  const lifetime = new AbortController()
  return { id: ++nextResource, client, store, patch, lifetime, mounts: 0, navigation: 0, selection: 0,
    getSnapshot: () => cached,
    subscribe: (f: () => void) => { listeners.add(f); return () => { listeners.delete(f) } },
    dispose: () => { lifetime.abort(); off(); store.dispose(); client.cancel(); listeners.clear() },
  }
}

export function useChat(options: UseChatOptions) {
  const latest = useRef(options)
  useCommit(() => { latest.current = options })
  const authenticated = !!options.getToken
  const r = useMemo(() => resource(new ChatClient(options.slug, {
    baseUrl: options.baseUrl, visitorToken: options.visitorToken,
    getToken: authenticated ? () => latest.current.getToken!() : undefined,
    onVisitorToken: token => latest.current.onVisitorToken?.(token),
    fetch: options.fetch, WebSocket: options.WebSocket, FormData: options.FormData, Blob: options.Blob,
  })), [options.slug, options.baseUrl, options.sessionId, options.identityKey, options.visitorToken, authenticated, options.fetch, options.WebSocket, options.FormData, options.Blob])
  const snapshot = useSyncExternalStore(r.subscribe, r.getSnapshot, r.getSnapshot)
  const actions = useMemo(() => {
    const refresh = async () => {
      const list = await r.client.list({ signal: r.lifetime.signal })
      if (!r.lifetime.signal.aborted) r.patch({ sessions: list.sessions })
    }
    let operations = 0
    const perform = async <T,>(operation: () => Promise<T>): Promise<T> => {
      if (r.lifetime.signal.aborted) throw new DOMException('Aborted', 'AbortError')
      operations++; r.patch({ error: null, operation: true })
      try { return await operation() }
      catch (error) { if (!r.lifetime.signal.aborted) r.patch({ error }); throw error }
      finally { operations--; if (!r.lifetime.signal.aborted) r.patch({ operation: operations > 0 }) }
    }
    let starting: Promise<string> | null = null
    const ensureSession = async () => r.store.getSnapshot().sessionId ?? (starting ??= r.store.start({ signal: r.lifetime.signal, embed: latest.current.embed }).then(s => s.id).finally(() => { starting = null }))
    const reload = async () => { const id = r.store.getSnapshot().sessionId; if (id) await r.store.load(id, { signal: r.lifetime.signal }); await refresh() }
    return {
      refresh: () => perform(async () => { const page = await r.client.info({ signal: r.lifetime.signal }); r.patch({ page }); await reload() }),
      load: (id: string) => { r.navigation++; r.selection++; return perform(() => r.store.load(id, { signal: r.lifetime.signal })) },
      start: () => { r.navigation++; r.selection++; return perform(async () => { await r.store.start({ signal: r.lifetime.signal, embed: latest.current.embed }); await refresh() }) },
      send: (text: string, files: ChatAttachment[] = []) => perform(async () => {
        r.navigation++
        r.patch({ pending: text, pendingFiles: files })
        try { await ensureSession(); const result = await r.store.send(text, { locale: latest.current.locale, attachments: files.map(f => f.id), signal: r.lifetime.signal }); await refresh(); return result }
        finally { if (!r.lifetime.signal.aborted) r.patch({ pending: null, pendingFiles: [] }) }
      }),
      answer: (response: Parameters<typeof r.store.answer>[0]) => perform(async () => {
        r.navigation++
        const result = await r.store.answer(response, { locale: latest.current.locale, signal: r.lifetime.signal }); await refresh(); return result
      }),
      cancel: () => r.store.cancel(),
      upload: (file: File) => perform(async () => {
        r.navigation++
        const id = await ensureSession(); const stored = await r.client.attachments.upload(id, file, { name: file.name, signal: r.lifetime.signal }); await refresh(); return stored
      }),
      removeFile: (id: string) => perform(async () => {
        const session = r.store.getSnapshot().sessionId
        if (session) await r.client.attachments.delete(session, id, { signal: r.lifetime.signal })
      }),
      download: (file: ChatAttachment) => perform(async () => {
        const session = r.store.getSnapshot().sessionId; if (!session) return
        const response = await r.client.attachments.download(session, file.id, { signal: r.lifetime.signal })
        const url = URL.createObjectURL(await response.blob())
        const a = Object.assign(document.createElement('a'), { href: url, download: file.name }); a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      }),
      rate: (turn: string, value: 'up' | 'down' | null, comment?: string) => perform(async () => {
        const session = r.store.getSnapshot().sessionId; if (!session) return
        if (value === null) await r.client.ratings.delete(session, turn, { signal: r.lifetime.signal })
        else await r.client.ratings.put(session, turn, value, { comment, signal: r.lifetime.signal })
        await reload()
      }),
    }
  }, [r])
  useEffect(() => {
    const generation = ++r.mounts, abort = new AbortController(), navigation = r.navigation
    r.patch({ loading: true, error: null })
    void Promise.all([r.client.info({ signal: abort.signal }), r.client.list({ signal: abort.signal })]).then(async ([page, list]) => {
      if (abort.signal.aborted) return
      r.patch({ page, sessions: list.sessions })
      const id = options.sessionId === undefined ? list.sessions[0]?.id : options.sessionId
      if (id && navigation === r.navigation) await r.store.load(id, { signal: abort.signal })
    }).catch(error => { if (!abort.signal.aborted) r.patch({ error }) }).finally(() => { if (!abort.signal.aborted) r.patch({ loading: false }) })
    return () => {
      abort.abort()
      // React StrictMode replays effects; the immediate next setup keeps this resource alive.
      queueMicrotask(() => { if (r.mounts === generation) r.dispose() })
    }
  }, [r, options.sessionId])
  const last = snapshot.turns[snapshot.turns.length - 1]
  const question = useMemo<ChatQuestion | null>(() => snapshot.question ?? (last?.status === 'waiting' ? { type: 'question', v: 1, seq: 0, node: last.node, prompt: last.text } : null), [snapshot.question, last])
  return { ...snapshot, ...actions, question, resourceKey: r.id, selectionKey: r.selection, client: r.client,
    busy: snapshot.loading || snapshot.operation || snapshot.status === 'loading' || snapshot.status === 'streaming',
    waiting: snapshot.status === 'waiting', answeredBy: last?.status === 'waiting' ? last.answered_by : undefined,
  }
}
export type ChatController = ReturnType<typeof useChat>
export type { ChatState, ChatResult }
