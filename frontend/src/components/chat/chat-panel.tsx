/** The editor's Chat tab (TASK-0085, REQ-0048 phase 1): chat with the saved workflow as a visitor would. Your chats
 *  on the left with "New chat"; the Builder / Visitor switch shows every step (builders always see full) or the steps
 *  the Chat settings give visitors. Runs use the saved workflow, like a chat trigger. When the chat is published, the
 *  Visitors list shows the page's chats read-only with every step (TASK-0142). */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, ChevronDown, Eye, Settings2, SquarePen, Trash2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Tip } from '@/components/tip'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'
import { cn } from '@/lib/utils'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { published, waitingTurn, type ChatSession, type ChatSettings } from '@/lib/chat'
import { useChatRun, type ChatEndpoint, type ChatView } from './use-chat-run'
import { ChatThread } from './chat-thread'
import { ChatComposer } from './chat-composer'
import { ChatSettingsDialog } from './chat-settings-dialog'

export function ChatPanel({ wid, active, canConfigure, dirty, compact = false, actions }: { wid: string; active: boolean; canConfigure: boolean; dirty: boolean; compact?: boolean; actions?: React.ReactNode }) {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<ChatSettings | null>(null); const [sessions, setSessions] = useState<ChatSession[]>([])
  const [sid, setSid] = useState<string | null>(null); const [view, setView] = useState<ChatView>('builder')
  const [err, setErr] = useState(''); const [cfg, setCfg] = useState(false); const [del, setDel] = useState<ChatSession | null>(null)
  const [visitors, setVisitors] = useState<ChatSession[]>([]); const [vsid, setVsid] = useState<string | null>(null)   // vsid: a visitor chat is open
  const list = (pick?: string) => api<ChatSession[]>(`/api/workflows/${wid}/chat/sessions`).then(s => { setSessions(s); setSid(c => pick ?? (c && s.some(x => x.id === c) ? c : s[0]?.id ?? null)) })
  const listVisitors = () => api<ChatSession[]>(`/api/workflows/${wid}/chat/visitors`).then(setVisitors)
  const visitorEp = useMemo<ChatEndpoint>(() => ({ session: id => `/api/workflows/${wid}/chat/visitors/${id}`, socket: '/ws/run' }), [wid])
  const chat = useChatRun(sid, view, () => { list().catch(() => {}) })   // titles and order change after a message
  const read = useChatRun(vsid, 'builder', undefined, visitorEp)
  useLoadWhen(active, () => { setErr(''); api<ChatSettings>(`/api/workflows/${wid}/chat`).then(setSettings).catch(e => setErr(e.message)); list().catch(e => setErr(e.message)); listVisitors().catch(() => setVisitors([])) }, wid)
  const showVisitors = !!settings && (published(settings) || visitors.length > 0)
  const fresh = () => api<ChatSession>(`/api/workflows/${wid}/chat/sessions`, { method: 'POST' }).then(s => list(s.id)).catch(e => setErr(e.message))
  // the first message of a new chat creates it, then goes out once the chat is loaded
  const first = useRef(''); const { send: say, session } = chat
  const send = (text: string) => { if (sid) { say(text); return } first.current = text
    api<ChatSession>(`/api/workflows/${wid}/chat/sessions`, { method: 'POST' }).then(s => list(s.id)).catch(e => { first.current = ''; setErr(e.message) }) }
  useEffect(() => { if (first.current && sid && session?.id === sid) { const x = first.current; first.current = ''; say(x) } }, [sid, session, say])
  const remove = (s: ChatSession) => api(`/api/chat/sessions/${s.id}`, { method: 'DELETE' }).then(() => { if (sid === s.id) setSid(null); list() }).catch(e => setErr(e.message))
  const waiting = waitingTurn(chat.session?.turns ?? [])   // a typed message answers the waiting Human node
  const mode = view === 'builder' ? 'full' : chat.session?.steps_mode ?? settings?.steps ?? 'labels'
  const off = settings && !settings.enabled
  // one icon-only New chat button: next to the session Select (compact) or in the sidebar header (fullscreen)
  const newChat = <Tip tip={t('chat.new')}><Button size="icon-sm" variant="ghost" id="chat-new" aria-label={t('chat.new')} disabled={!!off} onClick={fresh}><SquarePen /></Button></Tip>
  return <div className="flex h-full min-h-0" id="chat-panel">
    {!compact && <aside className="flex w-56 shrink-0 flex-col border-r">
      <div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b px-3" id="chat-sidebar-header">
        {showVisitors ? <Tabs value={vsid === null ? 'mine' : 'visitors'} onValueChange={v => v === 'mine' ? setVsid(null) : setVsid(visitors[0]?.id ?? '')}>
            <TabsList size="sm"><TabsTrigger value="mine" id="chat-tab-mine">{t('chat.sessions')}</TabsTrigger>
              <TabsTrigger value="visitors" id="chat-tab-visitors" onClick={() => listVisitors().catch(() => {})}>{t('chat.visitors.tab')}</TabsTrigger></TabsList></Tabs>
          : <span className="truncate text-xs font-medium text-muted-foreground">{t('chat.sessions')}</span>}
        {vsid === null && newChat}</div>
      <ScrollArea className="min-h-0 flex-1">{vsid !== null ? <nav className="space-y-0.5 p-2" aria-label={t('chat.visitors.tab')} id="chat-visitors">
        {!visitors.length && <p className="px-2 py-1 text-xs text-muted-foreground">{t('chat.visitors.none')}</p>}
        {visitors.map(s => <button key={s.id} data-testid="chat-visitor-session" aria-current={s.id === vsid || undefined} onClick={() => setVsid(s.id)}
          className={cn('block w-full rounded-md px-2 py-1.5 text-left hover:bg-accent', s.id === vsid && 'bg-accent')}>
          <div className="truncate text-xs font-medium">{s.title || t('chat.untitled')}</div>
          <div className="truncate text-[11px] text-muted-foreground tabular-nums">{t(`chat.visitors.channel.${s.channel}`)} · {fmtDate(s.updated)}</div></button>)}
      </nav> : <nav className="space-y-0.5 p-2" aria-label={t('chat.sessions')}>
        {!sessions.length && <p className="px-2 py-1 text-xs text-muted-foreground">{t('chat.noSessions')}</p>}
        {sessions.map(s => <div key={s.id} className={cn('group flex items-center gap-1 rounded-md hover:bg-accent', s.id === sid && 'bg-accent')}>
          <button data-testid="chat-session" aria-current={s.id === sid || undefined} onClick={() => setSid(s.id)} className="min-w-0 flex-1 px-2 py-1.5 text-left">
            <div className="truncate text-xs font-medium">{s.title || t('chat.untitled')}</div>
            <div className="truncate text-[11px] text-muted-foreground tabular-nums">{fmtDate(s.updated)}</div></button>
          <Button size="icon-xs" variant="ghost" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" aria-label={t('chat.delete')} data-testid="chat-delete" onClick={() => setDel(s)}><Trash2 /></Button>
        </div>)}
      </nav>}</ScrollArea>
    </aside>}
    <div className="flex min-w-0 flex-1 flex-col">
      <div className={cn("flex h-11 shrink-0 items-center border-b", compact ? "gap-0.5 px-1.5" : "gap-2 px-3")} id="chat-toolbar">
        {compact
          // compact: a short "Builder" / "Visitor" trigger keeps the row for the session picker; its menu names and explains
          // both views and holds Chat settings
          ? <DropdownMenu><Tip tip={`${t('chat.viewAs')}: ${t(`chat.views.${view}.title`)}`}><DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="px-1.5 text-sm" id="chat-view" aria-label={`${t('chat.viewAs')}: ${t(`chat.views.${view}.title`)}`}>{t(`chat.views.${view}.short`)}<ChevronDown data-icon="inline-end" className="size-4 text-muted-foreground" /></Button>
            </DropdownMenuTrigger></Tip>
            <DropdownMenuContent align="start" className="w-72"><DropdownMenuLabel>{t('chat.viewAs')}</DropdownMenuLabel>
              <DropdownMenuRadioGroup value={view} onValueChange={v => setView(v as ChatView)}>
                {(['builder', 'visitor'] as const).map(v => <DropdownMenuRadioItem key={v} value={v} id={`chat-view-${v}`}>
                  <span className="flex flex-col gap-0.5"><span>{t(`chat.views.${v}.title`)}</span><span className="text-xs text-muted-foreground">{t(`chat.views.${v}.desc`)}</span></span></DropdownMenuRadioItem>)}
              </DropdownMenuRadioGroup>
              {canConfigure && <><DropdownMenuSeparator /><DropdownMenuItem id="chat-settings-btn" onSelect={() => setCfg(true)}><Settings2 />{t('chat.settings.title')}</DropdownMenuItem></>}
            </DropdownMenuContent></DropdownMenu>
          : <Select value={view} onValueChange={v => setView(v as ChatView)}>
            <SelectTrigger size="sm" variant="ghost" className="w-auto min-w-0 shrink" id="chat-view" aria-label={t('chat.viewAs')}><SelectValue>{t(`chat.views.${view}.title`)}</SelectValue></SelectTrigger>
            <SelectContent position="popper" align="start"><SelectGroup><SelectLabel>{t('chat.viewAs')}</SelectLabel>
              {(['builder', 'visitor'] as const).map(v => <SelectItem key={v} value={v} id={`chat-view-${v}`} className="max-w-80">
                <span className="flex flex-col gap-0.5"><span>{t(`chat.views.${v}.title`)}</span><span className="text-xs whitespace-normal text-muted-foreground">{t(`chat.views.${v}.desc`)}</span></span></SelectItem>)}
            </SelectGroup></SelectContent></Select>}
        <span className={cn('truncate text-xs text-muted-foreground', compact && 'hidden')} id="chat-mode-hint">{t(`chat.stepsHint.${mode}`)}</span>
        {dirty && !compact && <span className="truncate text-xs text-warning" id="chat-unsaved">{t('chat.unsaved')}</span>}
        {compact && <><Select value={vsid ? `v:${vsid}` : sid ?? ''} onValueChange={x => { if (x.startsWith('v:')) setVsid(x.slice(2)); else { setVsid(null); setSid(x) } }}>
          <SelectTrigger size="sm" variant="ghost" className="min-w-32 flex-1 justify-start" id="chat-session-picker" aria-label={t('chat.sessions')} onClick={() => { if (showVisitors) listVisitors().catch(() => {}) }}><SelectValue placeholder={t('chat.noSessions')} /></SelectTrigger>
          <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.title || t('chat.untitled')}</SelectItem>)}
            {showVisitors && visitors.length > 0 && <SelectGroup><SelectLabel>{t('chat.visitors.tab')}</SelectLabel>
              {visitors.map(s => <SelectItem key={s.id} value={`v:${s.id}`} data-testid="chat-visitor-option">{s.title || t('chat.untitled')}</SelectItem>)}</SelectGroup>}</SelectContent></Select>
          {vsid === null && newChat}</>}
        {!compact && <span className="ml-auto" />}
        {canConfigure && !compact && <Tip tip={t('chat.settings.title')}><Button size="icon-sm" variant="ghost" id="chat-settings-btn" aria-label={t('chat.settings.title')} onClick={() => setCfg(true)}><Settings2 /></Button></Tip>}{actions}
      </div>
      {(err || chat.error) && <Alert variant="destructive" className="m-3 w-auto"><AlertCircle /><AlertDescription id="chat-error-banner">{err || chat.error}</AlertDescription></Alert>}
      {vsid !== null ? <><div className="flex shrink-0 items-center gap-2 border-b bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground" id="chat-visitor-readonly" role="status">
          <Eye className="size-3.5 shrink-0" /><span className="min-w-0 flex-1 truncate">{t('chat.visitors.readOnly')}</span></div>
        {vsid ? <ChatThread turns={read.session?.turns ?? []} mode="full" events={[]} trace={read.trace} pending={null} running={false} />
          : <p className="m-auto p-6 text-sm text-muted-foreground">{t('chat.visitors.none')}</p>}</>
      : off ? <div className="m-auto max-w-sm space-y-3 p-6 text-center" id="chat-off">
          <p className="text-sm text-muted-foreground">{t('chat.off')}</p>
          {canConfigure && <Button size="sm" id="chat-turn-on" onClick={() => setCfg(true)}><Settings2 />{t('chat.settings.open')}</Button>}</div>
        : settings && <>{view === 'visitor' && <div className="flex shrink-0 items-center gap-2 border-b bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground" id="chat-visitor-banner" role="status">
            <Eye className="size-3.5 shrink-0" /><span className="min-w-0 flex-1 truncate">{t('chat.visitorBanner')}</span>
            <Button size="xs" variant="link" id="chat-visitor-exit" onClick={() => setView('builder')}>{t('chat.visitorExit')}</Button></div>}
          <ChatThread turns={chat.session?.turns ?? []} mode={mode} replyField={settings.reply_field} events={chat.events} trace={chat.trace}
            pending={chat.pending} running={chat.running} onAnswer={chat.answer} /></>}
      {!off && vsid === null && <ChatComposer disabled={!settings || waiting?.answered_by === 'reviewer'} running={chat.running} onStop={chat.cancel}
        placeholder={waiting ? t(waiting.answered_by === 'reviewer' ? 'chat.waitingReviewer' : 'chat.answerPlaceholder') : undefined}
        onSend={text => waiting?.run_id ? chat.answer(waiting.run_id, text) : send(text)} />}
    </div>
    <ChatSettingsDialog wid={wid} open={cfg} onOpenChange={setCfg} onSaved={setSettings} />
    <AlertDialog open={!!del} onOpenChange={o => { if (!o) setDel(null) }}><AlertDialogContent>
      <AlertDialogHeader><AlertDialogTitle>{t('chat.deleteTitle')}</AlertDialogTitle><AlertDialogDescription>{t('chat.deleteBody', { title: del?.title || t('chat.untitled') })}</AlertDialogDescription></AlertDialogHeader>
      <AlertDialogFooter><AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
        <AlertDialogAction asChild><Button variant="destructive" id="chat-delete-confirm" onClick={() => { if (del) remove(del); setDel(null) }}>{t("common.delete")}</Button></AlertDialogAction></AlertDialogFooter>
    </AlertDialogContent></AlertDialog>
  </div>
}
