import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Superstep, createChatStore } from '@superstep/sdk'
import type { ChatSession, ChatTurn } from '@superstep/sdk'
import { MessageCircle, Moon, Paperclip, Plus, Send, Square, Sun, ThumbsDown, ThumbsUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import i18n, { errorText } from '@/lib/i18n'
import en from './locales/en.json'
import vi from './locales/vi.json'
import './styles.css'
import { WidgetDemo } from './widget-demo'

i18n.addResourceBundle('en', 'host', en)
i18n.addResourceBundle('vi', 'host', vi)
type User = { id: string; name: string }
export type Session = { user: User | null; config: { baseUrl: string; slug: string } }
const displayError = (error: unknown) => {
  const value = error as { code?: string; message?: string }
  return errorText({ ...value, code: value?.code === 'CONNECTION_ERROR' ? 'NETWORK_ERROR' : value?.code, message: value?.message })
}
const locale = (): 'en' | 'vi' => i18n.language?.startsWith('vi') ? 'vi' : 'en'

export function App({ integration = 'headless' }: { integration?: 'headless' | 'widget' }) {
  const { t } = useTranslation('host'), { t: common } = useTranslation()
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [dark, setDark] = useState(() => localStorage.getItem('chat-host-theme') === 'dark')
  const lang = locale()
  useEffect(() => { document.documentElement.classList.toggle('dark', dark); localStorage.setItem('chat-host-theme', dark ? 'dark' : 'light') }, [dark])
  useEffect(() => { document.title = t('brand') }, [t])
  const load = async () => {
    setError(null)
    try { setSession(await api<Session>('/api/auth/session')) } catch (error) { setError(error) }
  }
  useEffect(() => {
    let mounted = true
    void api<Session>('/api/auth/session').then(value => { if (mounted) setSession(value) }, error => { if (mounted) setError(error) })
    return () => { mounted = false }
  }, [])
  const signIn = async (persona: string) => {
    setBusy(true); setError(null)
    try { setSession(await api<Session>('/api/auth/login', { method: 'POST', json: { persona } })) }
    catch (error) { setError(error) } finally { setBusy(false) }
  }
  const signOut = async () => {
    setBusy(true); setError(null)
    try { await api('/api/auth/logout', { method: 'POST' }); setSession(current => current && { ...current, user: null }) }
    catch (error) { setError(error) } finally { setBusy(false) }
  }
  return <div lang={lang} className="min-h-screen bg-background text-foreground">
    <header className="border-b bg-card">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-5">
        <div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground"><MessageCircle aria-hidden="true" className="size-5" /></span>
          <div><p className="font-semibold">{t('brand')}</p><p className="text-xs text-muted-foreground">{t('demo')}</p></div></div>
        <div className="flex flex-wrap items-center gap-2">
          {([['/', 'headlessExample'], ['/react/', 'reactExample'], ['/widget.html', 'widgetExample']] as const).map(([href, key]) => <Button key={href} asChild size="sm" variant="ghost"><a href={href}>{common(`chat.toolkit.${key}`)}</a></Button>)}
          <div className="flex items-center gap-1" role="group" aria-label={t('language')}>
            <Button size="sm" variant={lang === 'en' ? 'secondary' : 'ghost'} onClick={() => void i18n.changeLanguage('en')}>{t('english')}</Button>
            <Button size="sm" variant={lang === 'vi' ? 'secondary' : 'ghost'} onClick={() => void i18n.changeLanguage('vi')}>{t('vietnamese')}</Button>
          </div>
          <Button variant="outline" size="icon-sm" aria-label={t('theme')} onClick={() => setDark(value => !value)}>{dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}</Button>
          {session?.user && <><Badge variant="secondary">{session.user.name}</Badge><Button size="sm" variant="ghost" disabled={busy} onClick={() => void signOut()}>{t('signOut')}</Button></>}
        </div>
      </div>
    </header>
    <main className="mx-auto max-w-6xl px-5 py-8">
      {error !== null && <Alert variant="destructive" className="mb-5"><AlertDescription>{displayError(error)}</AlertDescription></Alert>}
      {!session && <Button variant="outline" onClick={() => void load()}>{t(error ? 'retry' : 'loading')}</Button>}
      {session && !session.user && <div className="mx-auto max-w-2xl py-12">
        <Card><CardHeader><Badge variant="outline" className="mb-4 w-fit">{t('demo')}</Badge><CardTitle className="text-2xl">{t('title')}</CardTitle><CardDescription>{t('intro')}</CardDescription></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">{(['lan', 'minh'] as const).map(persona => <Button key={persona} variant="outline" size="lg" disabled={busy} onClick={() => void signIn(persona)} data-testid={`signin-${persona}`}>
            {t('signIn', { name: t(`people.${persona}`) })}
          </Button>)}</CardContent><CardFooter><p className="text-xs text-muted-foreground">{t('privacy')}</p></CardFooter></Card>
      </div>}
      {integration === 'headless' && session?.user && <Workspace key={session.user.id} session={session as Session & { user: User }} />}
      {integration === 'widget' && session && <WidgetDemo session={session} lang={lang} onError={setError} />}
    </main>
  </div>
}

function Workspace({ session }: { session: Session & { user: User } }) {
  const { t } = useTranslation('host')
  const chat = useMemo(() => new Superstep({ baseUrl: session.config.baseUrl }).chat(session.config.slug, {
    getToken: async () => (await api<{ token: string }>('/api/auth/chat-token', { method: 'POST' })).token,
  }), [session.config.baseUrl, session.config.slug])
  const store = useMemo(() => createChatStore(chat), [chat])
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [message, setMessage] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [approved, setApproved] = useState(false)
  const [note, setNote] = useState('')
  const [ratings, setRatings] = useState<Record<string, 'up' | 'down'>>({})
  const fileInput = useRef<HTMLInputElement>(null)
  const pending = busy || state.status === 'loading' || state.status === 'streaming'
  const waiting = state.status === 'waiting'
  useEffect(() => {
    let mounted = true
    void (async () => {
      try {
        const page = await chat.list()
        if (!mounted) return
        setSessions(page.sessions)
        if (page.sessions.length) await store.load(page.sessions[0].id)
      } catch (error) { if (mounted) setError(error) }
      finally { if (mounted) setBusy(false) }
    })()
    return () => { mounted = false; store.dispose() }
  }, [chat, store])
  const perform = async (operation: () => Promise<unknown>) => {
    setBusy(true); setError(null)
    try { await operation() } catch (error) { setError(error) } finally { setBusy(false) }
  }
  const refresh = async () => setSessions((await chat.list()).sessions)
  const send = (event: FormEvent) => {
    event.preventDefault()
    void perform(async () => {
      if (!store.getSnapshot().sessionId) await store.start()
      const id = store.getSnapshot().sessionId!
      const attachments = file ? [(await chat.attachments.upload(id, file)).id] : []
      const text = message.trim() || t('attachmentMessage')
      setMessage(''); setFile(null); if (fileInput.current) fileInput.current.value = ''
      await store.send(text, { attachments, locale: locale() })
      await refresh()
    })
  }
  const answer = (event: FormEvent) => {
    event.preventDefault()
    void perform(async () => {
      const latest = [...state.turns].reverse().find(turn => turn.role === 'assistant' && turn.status === 'waiting')
      await store.answer({ approved, note }, { node: state.question?.node ?? latest?.node ?? undefined, locale: locale() })
      setApproved(false); setNote(''); await refresh()
    })
  }
  const rate = (turn: ChatTurn, value: 'up' | 'down') => void perform(async () => {
    await chat.ratings.put(state.sessionId!, turn.id, value)
    setRatings(current => ({ ...current, [turn.id]: value }))
  })
  const statusLabel = t(pending && state.status !== 'streaming' ? 'loading' : waiting ? 'waiting' : state.status === 'streaming' ? 'streaming' : error || state.error ? 'error' : 'ready')
  const failure = error || state.error
  return <div className="grid items-start gap-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
    <Card size="sm"><CardHeader><CardTitle>{t('conversations')}</CardTitle></CardHeader><CardContent className="space-y-4">
      <Button variant="outline" className="w-full" disabled={pending} onClick={() => void perform(async () => { await store.start(); await refresh() })}><Plus aria-hidden="true" />{t('newChat')}</Button>
      <nav aria-label={t('conversations')} className="max-h-80 space-y-1 overflow-auto" data-testid="conversation-list">
        {sessions.length === 0 && <p className="text-xs text-muted-foreground">{t('noChats')}</p>}
        {sessions.map(item => <Button key={item.id} variant={item.id === state.sessionId ? 'secondary' : 'ghost'} className="w-full justify-start" disabled={pending}
          aria-current={item.id === state.sessionId ? 'page' : undefined} onClick={() => void perform(() => store.load(item.id))} data-session-id={item.id}>
          <MessageCircle aria-hidden="true" /><span className="truncate">{item.title || t('untitled')}</span>
        </Button>)}
      </nav>
    </CardContent></Card>
    <Card className="min-w-0"><CardHeader className="border-b"><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>{t('assistant')}</CardTitle>
      <Badge variant={waiting ? 'warning' : failure ? 'destructive' : 'secondary'} data-testid="stream-status" data-state={state.status}>{statusLabel}</Badge>
    </div></CardHeader>
      <CardContent className="space-y-5">
        {failure ? <Alert variant="destructive"><AlertDescription>{displayError(failure)}</AlertDescription></Alert> : null}
        <div role="log" aria-live="polite" aria-label={t('conversations')} className="min-h-64 space-y-5" data-testid="messages" data-session-id={state.sessionId || ''}>
          {state.turns.length === 0 && !state.text && <div className="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-muted text-primary"><MessageCircle aria-hidden="true" className="size-6" /></span>
            <h1 className="text-lg font-semibold">{t('welcome')}</h1><p className="max-w-sm text-sm text-muted-foreground">{t('welcomeHint')}</p>
          </div>}
          {state.turns.map(turn => <article key={turn.id} className={`flex flex-col gap-2 ${turn.role === 'user' ? 'items-end' : 'items-start'}`} data-turn-id={turn.id} data-role={turn.role}>
            <p className="text-xs text-muted-foreground">{turn.role === 'user' ? t('you') : t('assistant')}</p>
            <div className={`max-w-full whitespace-pre-wrap break-words rounded-xl px-4 py-3 text-sm ${turn.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}>{turn.text}</div>
            {turn.attachments?.map(item => <Badge key={item.id} variant="outline"><Paperclip aria-hidden="true" className="mr-1 size-3" />{item.name}</Badge>)}
            {turn.role === 'assistant' && turn.status === 'ok' && <div className="flex items-center gap-1">
              <Button size="icon-xs" variant="ghost" disabled={pending} aria-label={t('helpful')} aria-pressed={(ratings[turn.id] ?? turn.rating?.value) === 'up'} onClick={() => rate(turn, 'up')}><ThumbsUp aria-hidden="true" /></Button>
              <Button size="icon-xs" variant="ghost" disabled={pending} aria-label={t('unhelpful')} aria-pressed={(ratings[turn.id] ?? turn.rating?.value) === 'down'} onClick={() => rate(turn, 'down')}><ThumbsDown aria-hidden="true" /></Button>
              {(ratings[turn.id] ?? turn.rating?.value) && <span className="ml-2 text-xs text-muted-foreground" role="status">{t('rated')}</span>}
            </div>}
          </article>)}
          {state.text && state.status === 'streaming' && state.turns[state.turns.length - 1]?.text !== state.text && <p className="whitespace-pre-wrap break-words rounded-xl bg-muted px-4 py-3 text-sm">{state.text}</p>}
        </div>
        {waiting && <form onSubmit={answer} className="space-y-4 rounded-xl border bg-muted/30 p-4" data-testid="approval-form">
          <h2 className="font-medium">{t('formTitle')}</h2>
          <div className="flex items-center gap-2"><Checkbox id="approved" checked={approved} onCheckedChange={value => setApproved(value === true)} disabled={pending} /><Label htmlFor="approved">{t('approved')}</Label></div>
          <div className="space-y-2"><Label htmlFor="note">{t('note')}</Label><Textarea id="note" value={note} onChange={event => setNote(event.target.value)} maxLength={1000} placeholder={t('notePlaceholder')} disabled={pending} /></div>
          <Button type="submit" disabled={pending}>{t('answer')}</Button>
        </form>}
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-3 border-t">
        <form onSubmit={send} className="w-full space-y-3">
          <div className="space-y-2"><Label htmlFor="message">{t('message')}</Label><Textarea id="message" value={message} onChange={event => setMessage(event.target.value)} maxLength={10000} placeholder={t('placeholder')} disabled={pending || waiting} className="min-h-20 resize-none" /></div>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0 space-y-2"><Label htmlFor="attachment" className="sr-only">{t('attachment')}</Label>
              <Input ref={fileInput} id="attachment" type="file" accept=".txt,.md,.csv,.json,.pdf" onChange={event => setFile(event.target.files?.[0] || null)} disabled={pending || waiting} className="hidden" tabIndex={-1} />
              <Button type="button" variant="outline" size="sm" disabled={pending || waiting} onClick={() => fileInput.current?.click()}><Paperclip aria-hidden="true" />{t('attachment')}</Button>
            </div>
            {state.status === 'streaming' ? <Button type="button" variant="outline" onClick={store.cancel}><Square aria-hidden="true" />{t('cancel')}</Button>
              : <Button type="submit" disabled={pending || waiting || (!message.trim() && !file)}><Send aria-hidden="true" />{t('send')}</Button>}
          </div>
          {file && <p className="text-xs text-muted-foreground">{t('file', { name: file.name })}</p>}
        </form><p className="text-center text-xs text-muted-foreground">{t('powered')}</p>
      </CardFooter>
    </Card>
  </div>
}

