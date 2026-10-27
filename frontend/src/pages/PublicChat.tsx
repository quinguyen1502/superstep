/** The published chat page /c/:slug (TASK-0142, REQ-0074, DEC-0067): people outside the studio chat with a workflow.
 *  It loads no studio data: the page settings, the visitor's own chats (an HttpOnly cookie says who they are) and the
 *  public socket. signed_in chats send a visitor who is not signed in to the login page and back.
 *  ?embed=1 is the page inside another site's iframe (TASK-0143): its chats are "embed" chats, and the visitor token
 *  goes as X-Chat-Visitor and ?visitor= because a frame's cookie is a third-party cookie that browsers may drop. With
 *  &widget=1 the widget on the host page keeps the token: the page asks it with postMessage and hands a new one back,
 *  and only takes tokens from the chat's embed_origins. A plain iframe keeps it in the frame's own (partitioned)
 *  localStorage, which some browsers (Safari) clear, so its chats may not last.
 *  The chat's logo (TASK-0145) sits in the header, over the welcome and in the browser tab; without one the header shows
 *  the title's first letter and the welcome a picture. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertCircle, MessageCircleOff, SquarePen } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tip } from '@/components/tip'
import { api, ApiError, loginUrl } from '@/lib/api'
import { useSystemTheme } from '@/lib/theme'
import { publicLogoUrl, waitingTurn, type ChatSession, type PublicChatPage as Page } from '@/lib/chat'
import { ChatIllustration, ChatLogo } from '@/components/chat/chat-logo'
import { useChatRun, type ChatEndpoint } from '@/components/chat/use-chat-run'
import { ChatThread } from '@/components/chat/chat-thread'
import { ChatComposer } from '@/components/chat/chat-composer'
import { ChatMarkdown } from '@/components/chat/chat-markdown'
import { MSG } from '@/widget/protocol'

const HOST_WAIT_MS = 2000   // a widget host that does not answer: start as a new visitor
const frameKey = (slug: string) => `superstep-chat:${slug}`
const stored = (slug: string) => { try { return localStorage.getItem(frameKey(slug)) } catch { return null } }

export function PublicChatPage() {
  const { t } = useTranslation(); const { slug = '' } = useParams(); useSystemTheme()
  const [params] = useSearchParams(); const embed = params.get('embed') === '1'; const widget = embed && params.get('widget') === '1'
  const [page, setPage] = useState<Page | null>(null); const [gone, setGone] = useState(false); const [err, setErr] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([]); const [sid, setSid] = useState<string | null>(null)
  // the visitor token ('new' when there is none yet); '' = the cookie (a direct visit); null = still asking the widget's host
  const [visitor, setVisitor] = useState<string | null>(() => widget ? null : embed ? stored(slug) || 'new' : ''); const host = useRef('')
  const base = `/api/public/chat/${slug}`
  const headers = useMemo(() => visitor ? { 'X-Chat-Visitor': visitor } : undefined, [visitor])
  const ep = useMemo<ChatEndpoint>(() => ({ session: id => `${base}/sessions/${id}`, headers,
    socket: `/ws/public/chat/${slug}${visitor && visitor !== 'new' ? `?visitor=${encodeURIComponent(visitor)}` : ''}` }), [base, slug, headers, visitor])
  /** A new token from the API: use it from now on, and give it to the host to keep. */
  const keep = (d: { visitor_token?: string }) => { const tok = d.visitor_token; if (!tok) return
    setVisitor(tok)
    if (widget) { if (host.current) window.parent.postMessage({ type: MSG.save, token: tok }, host.current) }
    else if (embed) { try { localStorage.setItem(frameKey(slug), tok) } catch { /* storage blocked: this view only */ } } }
  const list = (pick?: string) => api<{ sessions: ChatSession[]; visitor_token?: string }>(`${base}/sessions`, { headers }).then(d => { keep(d)
    setSessions(d.sessions); setSid(c => pick ?? (c && d.sessions.some(x => x.id === c) ? c : d.sessions[0]?.id ?? null)) })
  const fail = (e: unknown) => { if (e instanceof ApiError && e.code === 'CHAT_NOT_PUBLISHED') setGone(true); else setErr((e as Error).message) }
  const chat = useChatRun(sid, 'visitor', () => { list().catch(() => {}) }, ep)
  useEffect(() => {
    api<Page>(base).then(p => {
      if (p.access === 'signed_in' && !p.signed_in) { location.href = loginUrl(false, `/c/${slug}`); return }
      setPage(p); if (p.title) document.title = p.title
    }).catch(fail)
  }, [base, slug])
  const logo = page ? publicLogoUrl(slug, page.logo) : undefined; const title = page?.title || t('chat.page.title')
  useEffect(() => {   // the tab's icon: the logo while the page shows, in place of the studio's
    if (!logo) return
    const studio = [...document.querySelectorAll<HTMLLinkElement>('link[rel="icon"]')]; studio.forEach(l => l.remove())
    const icon = Object.assign(document.createElement('link'), { rel: 'icon', href: logo, id: 'public-chat-favicon' }); document.head.append(icon)
    return () => { icon.remove(); document.head.append(...studio) }
  }, [logo])
  useEffect(() => {   // the widget's host: ask for its token, from the allowed sites only
    if (!widget || !page) return
    const onMessage = (e: MessageEvent) => {
      if (e.source !== window.parent || !page.embed_origins.includes(e.origin) || e.data?.type !== MSG.token) return
      host.current = e.origin; setVisitor(v => v ?? (typeof e.data.token === 'string' && e.data.token ? e.data.token : 'new'))
    }
    window.addEventListener('message', onMessage); window.parent.postMessage({ type: MSG.ready }, '*')
    const late = setTimeout(() => setVisitor(v => v ?? 'new'), HOST_WAIT_MS)
    return () => { window.removeEventListener('message', onMessage); clearTimeout(late) }
  }, [widget, page])
  const ready = !!page && visitor !== null
  useEffect(() => { if (ready) list().catch(fail) }, [ready])  // eslint-disable-line react-hooks/exhaustive-deps -- once the visitor is known
  // the first message of a new chat creates it, then goes out once the chat is loaded (as in the studio Chat tab)
  const first = useRef(''); const { send: say, session } = chat
  const create = () => api<ChatSession & { visitor_token?: string }>(`${base}/sessions`, { method: 'POST', json: { embed }, headers }).then(s => { keep(s); return s })
  const send = (text: string) => { if (sid) { say(text); return } first.current = text
    create().then(s => list(s.id)).catch(e => { first.current = ''; fail(e) }) }
  useEffect(() => { if (first.current && sid && session?.id === sid) { const x = first.current; first.current = ''; say(x) } }, [sid, session, say])
  const fresh = () => setSid(null)   // the next message starts a new chat

  if (gone) return <main className="flex min-h-svh items-center justify-center bg-background p-4" id="public-chat-gone">
    <Empty><EmptyHeader><EmptyMedia variant="icon"><MessageCircleOff /></EmptyMedia>
      <EmptyTitle>{t('chat.page.goneTitle')}</EmptyTitle><EmptyDescription>{t('chat.page.gone')}</EmptyDescription></EmptyHeader></Empty></main>
  const waiting = waitingTurn(chat.session?.turns ?? [])
  const intro = page && <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-4 px-4 py-6 text-center" id="public-chat-intro">
    {logo ? <ChatLogo src={logo} title={title} className="size-16 rounded-2xl" id="public-chat-hero" /> : <ChatIllustration />}
    <h2 className="text-lg font-semibold">{title}</h2>
    {page.intro ? <ChatMarkdown text={page.intro} /> : <p className="text-sm text-muted-foreground">{t('chat.empty')}</p>}
    {!!page.suggestions.length && <div className="flex flex-wrap justify-center gap-2" id="public-chat-suggestions">
      {page.suggestions.map(x => <Button key={x} variant="outline" /* ui-class-ok: a suggestion can wrap to two lines, so its height follows the text */ className="h-auto min-h-9 py-2 whitespace-normal" data-testid="chat-suggestion" disabled={chat.running || !ready} onClick={() => send(x)}>{x}</Button>)}</div>}
  </div>
  return <main className="flex h-svh min-h-0 flex-col bg-background" id="public-chat" data-slug={slug} data-embed={embed ? (widget ? 'widget' : 'iframe') : undefined}>
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
      {page && <ChatLogo src={logo} title={title} size="sm" id="public-chat-logo" />}
      <h1 className="min-w-0 flex-1 truncate text-sm font-semibold" id="public-chat-title">{title}</h1>
      {sessions.length > 0 && <Select value={sid ?? ''} onValueChange={setSid}>
        <SelectTrigger size="sm" variant="ghost" className="max-w-48 min-w-0" id="public-chat-sessions" aria-label={t('chat.sessions')}><SelectValue placeholder={t('chat.untitled')} /></SelectTrigger>
        <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.title || t('chat.untitled')}</SelectItem>)}</SelectContent></Select>}
      <Tip tip={t('chat.new')}><Button size="icon-sm" variant="ghost" id="public-chat-new" aria-label={t('chat.new')} disabled={!page || chat.running} onClick={fresh}><SquarePen /></Button></Tip>
    </header>
    {(err || chat.error) && <Alert variant="destructive" className="mx-auto mt-3 w-full max-w-3xl"><AlertCircle /><AlertDescription id="public-chat-error">{err || chat.error}</AlertDescription></Alert>}
    {page && <ChatThread turns={sid ? chat.session?.turns ?? [] : []} mode={page.steps_mode} events={chat.events} trace={chat.trace}
      pending={chat.pending} running={chat.running} onAnswer={chat.answer} empty={intro} />}
    {page && <ChatComposer disabled={!ready || waiting?.answered_by === 'reviewer'} running={chat.running} onStop={chat.cancel}
      placeholder={waiting ? t(waiting.answered_by === 'reviewer' ? 'chat.waitingReviewer' : 'chat.answerPlaceholder') : undefined}
      onSend={text => waiting?.run_id ? chat.answer(waiting.run_id, text) : send(text)} />}
  </main>
}
