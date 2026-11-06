/** Cookie-backed published chat for direct visits and Studio-only signed-in embeds.
 * Anonymous/app embeds use embedded-chat.tsx and its checked parent bridge instead. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError, loginUrl } from '@/lib/api'
import { useSystemTheme } from '@/lib/theme'
import { publicLogoUrl, waitingTurn, type ChatAttachment, type ChatSession, type PublicChatPage as Page } from '@/lib/chat'
import { useChatRun, type ChatEndpoint } from '@/components/chat/use-chat-run'
import { uploadChatFile } from '@/lib/chat-files'

import type { FileLinks } from '@superstep/react'
import type { ComposerFiles } from '@/components/chat/chat-composer'
import { PublicChatView } from './public-chat-view'

export function DirectPublicChatPage({ embed, onReady }: { embed?: 'iframe' | 'widget'; onReady?: () => void } = {}) {
  const { t } = useTranslation(); const { slug = '' } = useParams(); useSystemTheme()
  const [page, setPage] = useState<Page | null>(null); const [gone, setGone] = useState(false); const [err, setErr] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([]); const [sid, setSid] = useState<string | null>(null)
  const base = `/api/public/v1/chat/${slug}`
  const headers = undefined
  const ep = useMemo<ChatEndpoint>(() => ({ session: id => `${base}/sessions/${id}`, headers,
    socket: `/ws/public/v1/chat/${slug}`, v1: true }), [base, slug, headers])
  const list = (pick?: string) => api<{ sessions: ChatSession[]; visitor_token?: string }>(`${base}/sessions`, { headers }).then(d => {
    setSessions(d.sessions); setSid(c => pick ?? (c && d.sessions.some(x => x.id === c) ? c : d.sessions[0]?.id ?? null)) })
  // A failed session/message request belongs in the chat's error banner. Only
  // loading the page metadata determines whether the entire page is unavailable.
  const fail = (e: unknown) => setErr((e as Error).message)
  const chat = useChatRun(sid, 'visitor', () => { list().catch(() => {}) }, ep, setSid)
  const rate = (turnId: string, value: 'up' | 'down' | null, comment?: string) => {
    if (!sid) return
    const path = `${base}/sessions/${sid}/turns/${turnId}/rating`
    const req = value === null
      ? api<{ visitor_token?: string }>(path, { method: 'DELETE', headers })
      : api<{ visitor_token?: string }>(path, { method: 'PUT', json: comment === undefined ? { value } : { value, comment }, headers })
    req.then(() => chat.reload()).catch(fail)
  }
  useEffect(() => {
    let live = true
    api<Page>(base).then(p => {
      if (!live) return
      const modes = Array.isArray(p.access) ? p.access : [p.access]
      if (!modes.includes('anonymous') && modes.includes('signed_in') && !p.signed_in) { location.href = loginUrl(false, `/c/${slug}`); return }
      setPage(p); if (p.title) document.title = p.title
    }).catch(e => { if (!live) return; if (e instanceof ApiError && e.code === 'CHAT_NOT_PUBLISHED') setGone(true); else fail(e) })
    return () => { live = false }
  }, [base, slug])
  const logo = page ? publicLogoUrl(slug, page.logo) : undefined; const title = page?.title || t('chat.page.title')
  const ready = !!page
  useEffect(() => { if (ready) list().then(onReady).catch(fail) }, [ready])  // eslint-disable-line react-hooks/exhaustive-deps -- once page metadata arrives
  // the first message of a new chat creates it, then goes out once the chat is loaded (as in the studio Chat tab)
  const first = useRef(''); const { send: say, session } = chat
  const create = () => api<ChatSession>(`${base}/sessions`, { method: 'POST', json: { embed: !!embed }, headers })
  const send = (text: string, files: ChatAttachment[] = []) => { setErr(''); if (sid) { say(text, files); return } first.current = text
    create().then(s => list(s.id)).catch(e => { first.current = ''; fail(e) }) }
  useEffect(() => { if (first.current && sid && session?.id === sid) { const x = first.current; first.current = ''; say(x) } }, [sid, session, say])
  // files (TASK-0177): the first file of a new chat creates it; the visitor token goes with every request
  const made = useRef<Promise<string> | null>(null)
  const ensure = () => sid ? Promise.resolve(sid) : made.current ??= create().then(async s => { await list(s.id); return s.id }).finally(() => { made.current = null })
  const lim = page?.attachments
  const files: ComposerFiles | null = lim && !waitingTurn(chat.session?.turns ?? []) ? { ...lim,
    upload: f => ensure().then(id => uploadChatFile<ChatAttachment & { visitor_token?: string }>(`${base}/sessions/${id}/attachments`, f, headers)).then(d => { return d }),
    remove: id => sid ? api<{ visitor_token?: string }>(`${base}/sessions/${sid}/attachments/${id}`, { method: 'DELETE', headers }).then(() => {}) : Promise.resolve() } : null
  const links = useMemo<FileLinks | undefined>(() => sid ? { url: id => `${base}/sessions/${sid}/attachments/${id}`, headers } : undefined, [base, sid, headers])
  const fresh = () => { setErr(''); setSid(null) }   // the next message starts a new chat

  return <PublicChatView embed={embed} slug={slug} page={page} title={title} logo={logo} gone={gone} err={err || chat.error} ready={ready}
    sessions={sessions} sid={sid} setSid={setSid} fresh={fresh} send={send} files={files} onError={setErr} cancel={chat.cancel}
    chat={{ turns: sid ? chat.session?.turns ?? [] : [], mode: page?.steps_mode ?? 'labels', events: chat.events, trace: chat.trace, pending: chat.pending, pendingFiles: chat.pendingFiles, running: chat.running, onAnswer: chat.answer, onRate: sid ? rate : undefined,
      onEdit: chat.edit, onRegenerate: chat.regenerate, onSource: chat.session?.source_session_id ? () => setSid(chat.session!.source_session_id!) : undefined, files: links }} />
}
