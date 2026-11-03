/** SDK-backed iframe; parent credentials are accepted only by the frame bridge's checked window/origin. */
import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChatProvider, Composer, MessageList, QuestionCard, useChat, type ChatController } from '@superstep/react'
import type { ChatResult } from '@superstep/sdk/chat'
import { api, loginUrl } from '@/lib/api'
import { errorText, uiLocale, type ApiErrorBody } from '@/lib/i18n'
import { publicLogoUrl, type PublicChatPage as Page } from '@/lib/chat'
import { Empty, EmptyDescription, EmptyHeader } from '@/components/ui/empty'
import { createFrameBridge, type FrameBridge, type FrameState } from '@/widget/frame-bridge'
import { failureCode } from '@/widget/protocol'
import { DirectPublicChatPage } from './public-chat-direct'
import { PublicChatView } from './public-chat-view'
import '@superstep/react/styles.css'

export function EmbeddedChatPage({ widget }: { widget: boolean }) {
  const { slug = '' } = useParams()
  return <EmbeddedPage key={`${slug}:${widget}`} slug={slug} widget={widget} />
}
function EmbeddedPage({ slug, widget }: { slug: string; widget: boolean }) {
  const { t } = useTranslation()
  const [page, setPage] = useState<Page | null>(null), [error, setError] = useState<ApiErrorBody | null>(null)
  const [bridge, allow] = useMemo(() => {
    let origins: readonly string[] = []
    return [createFrameBridge(window, slug, widget, () => origins), (value: readonly string[]) => { origins = value }] as const
  }, [slug, widget])
  const state = useSyncExternalStore(bridge.subscribe, bridge.getSnapshot, bridge.getSnapshot)
  useEffect(() => bridge.start(), [bridge])
  useEffect(() => {
    const abort = new AbortController()
    void api<Page>(`/api/public/v1/chat/${slug}`, { signal: abort.signal }).then(value => {
      if (abort.signal.aborted) return
      const modes = Array.isArray(value.access) ? value.access : [value.access]
      if (!modes.includes('anonymous') && !modes.includes('app') && modes.includes('signed_in') && !value.signed_in) { location.href = loginUrl(false, `/c/${slug}`); return }
      allow(value.embed_origins); setPage(value); bridge.announce()
    }).catch(error => { if (!abort.signal.aborted) setError(error) })
    return () => abort.abort()
  }, [slug, bridge, allow])
  if (!page || state.kind === 'pending' || state.kind === 'error') return <main className="flex min-h-svh items-center justify-center bg-background p-4" id={error?.code === 'CHAT_NOT_PUBLISHED' ? 'public-chat-gone' : undefined}>
    <Empty><EmptyHeader><EmptyDescription role={error || state.code ? 'alert' : 'status'}>{error ? errorText(error) : state.code ? errorText({ code: state.code }) : t('chat.toolkit.loading')}</EmptyDescription></EmptyHeader></Empty>
  </main>
  const modes = Array.isArray(page.access) ? page.access : [page.access]
  if (state.kind === 'guest' && !modes.includes('anonymous') && modes.includes('signed_in') && page.signed_in) return <ChatProvider locale={state.options.language ?? (uiLocale().startsWith('vi') ? 'vi' : 'en')} theme={{ primary: state.options.color }}>
    <DirectPublicChatPage key={state.epoch} embed={widget ? 'widget' : 'iframe'} onReady={() => bridge.complete(state.epoch)} />
  </ChatProvider>
  return <EmbeddedController key={`${slug}:${state.epoch}:${state.kind}`} slug={slug} page={page} state={state} bridge={bridge} widget={widget} />
}
function EmbeddedController({ slug, page, state, bridge, widget }: { slug: string; page: Page; state: FrameState; bridge: FrameBridge; widget: boolean }) {
  const locale = state.options.language ?? (uiLocale().startsWith('vi') ? 'vi' : 'en'), app = state.kind === 'app'
  const getToken = useMemo(() => app ? () => bridge.getToken(state.epoch) : undefined, [bridge, state.epoch, app])
  const chat = useChat({ slug, baseUrl: location.origin, embed: true, identityKey: state.epoch, locale,
    getToken, visitorToken: app ? undefined : state.visitor, onVisitorToken: token => bridge.keep(token) })
  useEffect(() => { if (!chat.loading) bridge.complete(state.epoch, chat.error ? failureCode(chat.error) : undefined) }, [chat.loading, chat.error, bridge, state.epoch])
  const report = (error: unknown) => { if (bridge.getSnapshot().epoch === state.epoch) bridge.emit('error', { slug, code: failureCode(error) }) }
  const observe = async (operation: () => Promise<ChatResult>) => {
    const existing = new Set(chat.turns.map(turn => turn.id))
    try {
      const result = await operation()
      // Only newly produced turns, never restored history, auth frames, user metadata or attachment credentials.
      for (const turn of result.turns) if (bridge.getSnapshot().epoch === state.epoch && !existing.has(turn.id)) bridge.emit(turn.role === 'user' ? 'message' : 'answer', {
        slug, sessionId: result.sessionId, turn: { id: turn.id, role: turn.role, text: turn.text, status: turn.status },
      })
      return result
    } catch (error) { report(error); throw error }
  }
  const observed: ChatController = { ...chat, send: (text, files) => observe(() => chat.send(text, files)), answer: response => observe(() => chat.answer(response)) }
  return <ChatProvider chat={observed} locale={locale} theme={{ primary: state.options.color }} style={{ height: '100svh' }}>
    <EmbeddedView chat={observed} page={page} slug={slug} widget={widget} logo={state.options.logo} report={report} />
  </ChatProvider>
}
function EmbeddedView({ chat, page, slug, widget, logo: customLogo, report }: { chat: ChatController; page: Page; slug: string; widget: boolean; logo?: string; report: (error: unknown) => void }) {
  const { t, i18n } = useTranslation()
  const [fileError, setFileError] = useState('')
  const error = chat.error as ApiErrorBody | null
  const text = error ? error.code && i18n.exists(`errors.${error.code}`) ? errorText(error, i18n) : t('chat.toolkit.requestFailed') : fileError
  return <PublicChatView slug={slug} page={page} gone={error?.code === 'CHAT_NOT_PUBLISHED'} title={page.title || t('chat.page.title')}
    logo={customLogo || publicLogoUrl(slug, page.logo)} embed={widget ? 'widget' : 'iframe'} err={text} ready={!chat.busy} sessions={chat.sessions}
    sid={chat.sessionId} setSid={id => void chat.load(id).catch(report)} fresh={() => void chat.start().catch(report)} cancel={chat.cancel}
    send={(text, files) => void chat.send(text, files).catch(() => {})} onError={setFileError}
    chat={{ turns: [], mode: page.steps_mode, events: [], trace: { spans: [] }, pending: chat.pending, running: chat.busy }}
    renderThread={intro => <MessageList empty={intro} />} footer={<><QuestionCard showPrompt={false} /><Composer idPrefix="chat" /></>} />
}
