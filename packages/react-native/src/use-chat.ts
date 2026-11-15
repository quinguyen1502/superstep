import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { ChatClient, createChatStore, type ChatAttachment, type ChatClientOptions, type ChatQuestion, type ChatState, type NativeChatFile } from '@superstep/sdk/chat'
import type { ChatLocale } from './labels.js'

export interface UseChatOptions extends ChatClientOptions {
  slug: string
  /** A string loads that session. Omit it to stay empty until the first send. */
  sessionId?: string | null
  locale?: ChatLocale
}

export function useChat(options: UseChatOptions) {
  const latest = useRef(options)
  latest.current = options
  const authenticated = !!options.getToken
  const resource = useMemo(() => {
    const client = new ChatClient(options.slug, {
      baseUrl: options.baseUrl,
      visitorToken: options.visitorToken,
      getToken: authenticated ? () => latest.current.getToken!() : undefined,
      onVisitorToken: token => latest.current.onVisitorToken?.(token),
      fetch: options.fetch,
      WebSocket: options.WebSocket,
      FormData: options.FormData,
      Blob: options.Blob,
    })
    return { client, store: createChatStore(client) }
  }, [options.slug, options.baseUrl, options.visitorToken, authenticated, options.fetch, options.WebSocket, options.FormData, options.Blob])
  const snapshot = useSyncExternalStore(resource.store.subscribe, resource.store.getSnapshot, resource.store.getSnapshot)
  const [pending, setPending] = useState<string | null>(null)
  const [files, setFiles] = useState<ChatAttachment[]>([])
  const [operation, setOperation] = useState(false)
  const [actionError, setActionError] = useState<unknown>(null)
  const filesRef = useRef(files)
  filesRef.current = files
  const life = useRef(0)

  useEffect(() => {
    const generation = ++life.current
    setFiles([])
    setPending(null)
    setActionError(null)
    return () => {
      queueMicrotask(() => {
        if (life.current === generation) resource.store.dispose()
      })
    }
  }, [resource])

  useEffect(() => {
    if (typeof options.sessionId !== 'string') return
    const abort = new AbortController()
    void resource.store.load(options.sessionId, { signal: abort.signal }).catch(error => {
      if (!abort.signal.aborted) setActionError(error)
    })
    return () => abort.abort()
  }, [resource, options.sessionId])

  const actions = useMemo(() => {
    let operations = 0
    const perform = async <T,>(run: () => Promise<T>): Promise<T> => {
      operations += 1
      setOperation(true)
      setActionError(null)
      try {
        return await run()
      } catch (error) {
        setActionError(error)
        throw error
      } finally {
        operations -= 1
        if (operations === 0) setOperation(false)
      }
    }
    const sessionId = async () => {
      const current = resource.store.getSnapshot().sessionId
      if (current) return current
      const session = await resource.store.start()
      return session.id
    }
    return {
      send: (text: string) => perform(async () => {
        const attachments = filesRef.current.map(file => file.id)
        setPending(text)
        try {
          const result = await resource.store.send(text, {
            locale: latest.current.locale,
            ...(attachments.length ? { attachments } : {}),
          })
          setFiles([])
          return result
        } finally {
          setPending(null)
        }
      }),
      answer: (response: string | Record<string, unknown> | number | boolean) => perform(() => resource.store.answer(response, { locale: latest.current.locale })),
      cancel: () => resource.store.cancel(),
      start: () => perform(() => resource.store.start()),
      load: (id: string) => perform(() => resource.store.load(id)),
      upload: (file: NativeChatFile) => perform(async () => {
        const id = await sessionId()
        const stored = await resource.client.attachments.upload(id, file, { name: file.name, type: file.type })
        setFiles(current => [...current, stored])
        return stored
      }),
      removeFile: (id: string) => perform(async () => {
        const current = resource.store.getSnapshot().sessionId
        if (current) await resource.client.attachments.delete(current, id)
        setFiles(list => list.filter(file => file.id !== id))
      }),
      rate: (turnId: string, value: 'up' | 'down' | null, comment?: string) => perform(async () => {
        const current = resource.store.getSnapshot().sessionId
        if (!current) return
        if (value === null) await resource.client.ratings.delete(current, turnId)
        else await resource.client.ratings.put(current, turnId, value, comment === undefined ? {} : { comment })
        await resource.store.load(current)
      }),
    }
  }, [resource])

  const last = snapshot.turns[snapshot.turns.length - 1]
  const question: ChatQuestion | null = snapshot.question ?? (last?.status === 'waiting'
    ? { type: 'question', v: 1, seq: 0, node: last.node, prompt: last.text }
    : null)
  return {
    ...snapshot,
    error: actionError ?? snapshot.error,
    pending,
    pendingFiles: files,
    question,
    answeredBy: last?.status === 'waiting' ? last.answered_by ?? undefined : undefined,
    busy: operation || snapshot.status === 'loading' || snapshot.status === 'streaming',
    waiting: snapshot.status === 'waiting',
    ...actions,
  }
}

export type ChatController = ReturnType<typeof useChat>
export type { ChatState }
