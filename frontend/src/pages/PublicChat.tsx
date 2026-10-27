/** The published chat page /c/:slug (TASK-0142, REQ-0074, DEC-0067): people outside the studio chat with a workflow.
 *  It loads no studio data: the page settings, the visitor's own chats (an HttpOnly cookie says who they are) and the
 *  public socket. signed_in chats send a visitor who is not signed in to the login page and back. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertCircle, MessageCircleOff, SquarePen } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tip } from '@/components/tip'
import { api, ApiError, loginUrl } from '@/lib/api'
import { useSystemTheme } from '@/lib/theme'
import { waitingTurn, type ChatSession, type PublicChatPage as Page } from '@/lib/chat'
import { useChatRun, type ChatEndpoint } from '@/components/chat/use-chat-run'
import { ChatThread } from '@/components/chat/chat-thread'
import { ChatComposer } from '@/components/chat/chat-composer'
import { ChatMarkdown } from '@/components/chat/chat-markdown'

export function PublicChatPage() {
  const { t } = useTranslation(); const { slug = '' } = useParams(); useSystemTheme()
  const [page, setPage] = useState<Page | null>(null); const [gone, setGone] = useState(false); const [err, setErr] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([]); const [sid, setSid] = useState<string | null>(null)
  const base = `/api/public/chat/${slug}`
  const ep = useMemo<ChatEndpoint>(() => ({ session: id => `${base}/sessions/${id}`, socket: `/ws/public/chat/${slug}` }), [base, slug])
  const list = (pick?: string) => api<{ sessions: ChatSession[] }>(`${base}/sessions`).then(d => {
    setSessions(d.sessions); setSid(c => pick ?? (c && d.sessions.some(x => x.id === c) ? c : d.sessions[0]?.id ?? null)) })
  const fail = (e: unknown) => { if (e instanceof ApiError && e.code === 'CHAT_NOT_PUBLISHED') setGone(true); else setErr((e as Error).message) }
  const chat = useChatRun(sid, 'visitor', () => { list().catch(() => {}) }, ep)
  useEffect(() => {
    api<Page>(base).then(p => {
      if (p.access === 'signed_in' && !p.signed_in) { location.href = loginUrl(false, `/c/${slug}`); return }
      setPage(p); if (p.title) document.title = p.title
      return list()
    }).catch(fail)
  }, [base])  // eslint-disable-line react-hooks/exhaustive-deps -- once per chat
  // the first message of a new chat creates it, then goes out once the chat is loaded (as in the studio Chat tab)
  const first = useRef(''); const { send: say, session } = chat
  const create = () => api<ChatSession>(`${base}/sessions`, { method: 'POST', json: {} })
  const send = (text: string) => { if (sid) { say(text); return } first.current = text
    create().then(s => list(s.id)).catch(e => { first.current = ''; fail(e) }) }
  useEffect(() => { if (first.current && sid && session?.id === sid) { const x = first.current; first.current = ''; say(x) } }, [sid, session, say])
  const fresh = () => setSid(null)   // the next message starts a new chat

  if (gone) return <main className="flex min-h-svh items-center justify-center bg-background p-4" id="public-chat-gone">
    <Empty><EmptyHeader><EmptyMedia variant="icon"><MessageCircleOff /></EmptyMedia>
      <EmptyTitle>{t('chat.page.goneTitle')}</EmptyTitle><EmptyDescription>{t('chat.page.gone')}</EmptyDescription></EmptyHeader></Empty></main>
  const waiting = waitingTurn(chat.session?.turns ?? [])
  const intro = page && <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-4 px-4 py-6" id="public-chat-intro">
    <h2 className="text-lg font-semibold">{page.title || t('chat.page.title')}</h2>
    {page.intro ? <ChatMarkdown text={page.intro} /> : <p className="text-sm text-muted-foreground">{t('chat.empty')}</p>}
    {!!page.suggestions.length && <div className="flex flex-wrap gap-2" id="public-chat-suggestions">
      {page.suggestions.map(x => <Button key={x} variant="outline" /* ui-class-ok: a suggestion can wrap to two lines, so its height follows the text */ className="h-auto min-h-9 py-2 whitespace-normal text-left" data-testid="chat-suggestion" disabled={chat.running} onClick={() => send(x)}>{x}</Button>)}</div>}
  </div>
  return <main className="flex h-svh min-h-0 flex-col bg-background" id="public-chat" data-slug={slug}>
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
      <h1 className="min-w-0 flex-1 truncate text-sm font-semibold" id="public-chat-title">{page?.title || t('chat.page.title')}</h1>
      {sessions.length > 0 && <Select value={sid ?? ''} onValueChange={setSid}>
        <SelectTrigger size="sm" variant="ghost" className="max-w-48 min-w-0" id="public-chat-sessions" aria-label={t('chat.sessions')}><SelectValue placeholder={t('chat.untitled')} /></SelectTrigger>
        <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.title || t('chat.untitled')}</SelectItem>)}</SelectContent></Select>}
      <Tip tip={t('chat.new')}><Button size="icon-sm" variant="ghost" id="public-chat-new" aria-label={t('chat.new')} disabled={!page || chat.running} onClick={fresh}><SquarePen /></Button></Tip>
    </header>
    {(err || chat.error) && <Alert variant="destructive" className="mx-auto mt-3 w-full max-w-3xl"><AlertCircle /><AlertDescription id="public-chat-error">{err || chat.error}</AlertDescription></Alert>}
    {page && <ChatThread turns={sid ? chat.session?.turns ?? [] : []} mode={page.steps_mode} events={chat.events} trace={chat.trace}
      pending={chat.pending} running={chat.running} onAnswer={chat.answer} empty={intro} />}
    {page && <ChatComposer disabled={waiting?.answered_by === 'reviewer'} running={chat.running} onStop={chat.cancel}
      placeholder={waiting ? t(waiting.answered_by === 'reviewer' ? 'chat.waitingReviewer' : 'chat.answerPlaceholder') : undefined}
      onSend={text => waiting?.run_id ? chat.answer(waiting.run_id, text) : send(text)} />}
  </main>
}
