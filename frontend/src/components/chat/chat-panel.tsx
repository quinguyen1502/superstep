/** The editor's Chat tab (TASK-0085, REQ-0048 phase 1): chat with the saved workflow as a visitor would. Your chats
 *  on the left and "New chat" on the right; the Builder / Visitor switch shows every step (builders always see full) or the steps
 *  the Chat settings give visitors. Runs use the saved workflow, like a chat trigger. Workflow history and ratings
 *  live in the separate workflow Chat history & feedback dialog. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, ChevronDown, Eye, Settings2, SquarePen, Trash2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { Tip } from '@/components/tip'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'
import { cn } from '@/lib/utils'
import { waitingTurn, type ChatAttachment, type ChatSession, type ChatSettings } from '@/lib/chat'
import { useChatRun, type ChatView } from './use-chat-run'
import { ChatThread, type FileLinks } from './chat-thread'
import { ChatComposer, type ComposerFiles } from './chat-composer'
import { uploadChatFile } from '@/lib/chat-files'
import { ChatSettingsDialog } from './chat-settings-dialog'
import { TestCaseDialog, type TestCase } from '@/components/editor/editor-tests-panel'
import { useStudioCtx } from '@/components/editor/studio-context'

export function ChatPanel({ wid, active, canConfigure, canEdit, dirty, compact = false, actions }: { wid: string; active: boolean; canConfigure: boolean; canEdit: boolean; dirty: boolean; compact?: boolean; actions?: React.ReactNode }) {
  const { t } = useTranslation(); const { setTab } = useStudioCtx()
  const [settings, setSettings] = useState<ChatSettings | null>(null); const [sessions, setSessions] = useState<ChatSession[]>([])
  const [sid, setSid] = useState<string | null>(null); const [view, setView] = useState<ChatView>('builder')
  const [err, setErr] = useState(''); const [cfg, setCfg] = useState(false); const [del, setDel] = useState<ChatSession | null>(null)
  const [draft, setDraft] = useState<TestCase | null>(null); const [draftErr, setDraftErr] = useState('')
  const list = (pick?: string) => api<ChatSession[]>(`/api/workflows/${wid}/chat/sessions`).then(s => { setSessions(s); setSid(c => pick ?? (c && s.some(x => x.id === c) ? c : s[0]?.id ?? null)) })
  const chat = useChatRun(sid, view, () => { list().catch(() => {}) }, undefined, setSid)   // titles and order change after a message
  useLoadWhen(active, () => { setErr(''); api<ChatSettings>(`/api/workflows/${wid}/chat`).then(setSettings).catch(e => setErr(e.message)); list().catch(e => setErr(e.message)) }, wid)
  const rate = (turnId: string, value: 'up' | 'down' | null, comment?: string) => {
    if (!sid) return
    const path = `/api/chat/sessions/${sid}/turns/${turnId}/rating`
    const req = value === null ? api(path, { method: 'DELETE' }) : api(path, { method: 'PUT', json: comment === undefined ? { value } : { value, comment } })
    req.then(() => { chat.reload() }).catch(e => setErr(e.message))
  }
  const saveCase = (rid: string) => api<Omit<TestCase, 'id' | 'last'>>(`/api/workflows/${wid}/tests/from-run/${rid}`, { method: 'POST' })
    .then(d => { setDraftErr(''); setDraft({ ...d, id: '', last: null }) }).catch(e => setDraftErr(e.message))
  const fresh = () => api<ChatSession>(`/api/workflows/${wid}/chat/sessions`, { method: 'POST' }).then(s => list(s.id)).catch(e => setErr(e.message))
  const waiting = waitingTurn(chat.session?.turns ?? [])   // a typed message answers the waiting Human node
  // the first message of a new chat creates it, then goes out once the chat is loaded
  const first = useRef(''); const { send: say, session } = chat
  const send = (text: string, files: ChatAttachment[] = []) => { if (sid) { say(text, files); return } first.current = text
    api<ChatSession>(`/api/workflows/${wid}/chat/sessions`, { method: 'POST' }).then(s => list(s.id)).catch(e => { first.current = ''; setErr(e.message) }) }
  // files (TASK-0177): the first file of a new chat creates it; a typed answer to a Human node takes none
  const made = useRef<Promise<string> | null>(null)
  const ensure = () => sid ? Promise.resolve(sid) : made.current ??= api<ChatSession>(`/api/workflows/${wid}/chat/sessions`, { method: 'POST' })
    .then(async s => { await list(s.id); return s.id }).finally(() => { made.current = null })
  const files = useMemo<ComposerFiles | null>(() => settings && !waiting ? { ...settings.attachments,
    upload: f => ensure().then(id => uploadChatFile(`/api/chat/sessions/${id}/attachments`, f)),
    remove: id => sid ? api(`/api/chat/sessions/${sid}/attachments/${id}`, { method: 'DELETE' }) : Promise.resolve() } : null,
  [settings, waiting, sid])   // eslint-disable-line react-hooks/exhaustive-deps -- ensure follows sid
  const links = useMemo<FileLinks | undefined>(() => sid ? { url: id => `/api/chat/sessions/${sid}/attachments/${id}` } : undefined, [sid])
  useEffect(() => { if (first.current && sid && session?.id === sid) { const x = first.current; first.current = ''; say(x) } }, [sid, session, say])
  const remove = (s: ChatSession) => api(`/api/chat/sessions/${s.id}`, { method: 'DELETE' }).then(async () => { if (sid === s.id) setSid(null); await list() })
  const mode = view === 'builder' ? 'full' : chat.session?.steps_mode ?? settings?.steps ?? 'labels'
  const deleteName = (del?.title || t('chat.untitled')).replace(/\s+/g, ' ').trim()
  const off = settings && !settings.enabled
  // One New chat button in the right-hand toolbar, immediately before the panel actions.
  const newChat = <Tip tip={t('chat.new')}><Button size="icon-sm" variant="ghost" id="chat-new" aria-label={t('chat.new')} disabled={!!off} onClick={fresh}><SquarePen /></Button></Tip>
  return <div className="flex h-full min-h-0" id="chat-panel">
    {!compact && <aside className="flex w-56 shrink-0 flex-col border-r">
      <div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b px-3" id="chat-sidebar-header">
        <span className="truncate text-xs font-medium text-muted-foreground">{t('chat.sessions')}</span></div>
      <ScrollArea className="min-h-0 flex-1"><nav className="space-y-0.5 p-2" aria-label={t('chat.sessions')}>
        {!sessions.length && <p className="px-2 py-1 text-xs text-muted-foreground">{t('chat.noSessions')}</p>}
        {sessions.map(s => <div key={s.id} className={cn('group flex items-center gap-1 rounded-md hover:bg-accent', s.id === sid && 'bg-accent')}>
          <button data-testid="chat-session" aria-current={s.id === sid || undefined} onClick={() => setSid(s.id)} className="min-w-0 flex-1 px-2 py-1.5 text-left">
            <div className="truncate text-xs font-medium">{s.title || t('chat.untitled')}</div>
            <div className="truncate text-[11px] text-muted-foreground tabular-nums">{fmtDate(s.updated)}</div></button>
          <Button size="icon-xs" variant="ghost" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" aria-label={t('chat.delete')} data-testid="chat-delete" onClick={() => setDel(s)}><Trash2 /></Button>
        </div>)}
      </nav></ScrollArea>
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
        {compact && <Select value={sid ?? ''} onValueChange={setSid}>
          <SelectTrigger size="sm" variant="ghost" className="w-auto min-w-0 max-w-48 justify-start" id="chat-session-picker" aria-label={t('chat.sessions')}><SelectValue className="min-w-0 truncate" placeholder={t('chat.noSessions')} /></SelectTrigger>
          <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.title || t('chat.untitled')}</SelectItem>)}</SelectContent></Select>}
        <span className="ml-auto" />
        {canConfigure && !compact && <Tip tip={t('chat.settings.title')}><Button size="icon-sm" variant="ghost" id="chat-settings-btn" aria-label={t('chat.settings.title')} onClick={() => setCfg(true)}><Settings2 /></Button></Tip>}{newChat}{actions}
      </div>
      {(err || chat.error) && <Alert variant="destructive" className="m-3 w-auto"><AlertCircle /><AlertDescription id="chat-error-banner">{err || chat.error}</AlertDescription></Alert>}
      {draftErr && <Alert variant="destructive" className="m-3 w-auto"><AlertDescription>{draftErr}</AlertDescription></Alert>}
      {off ? <div className="m-auto max-w-sm space-y-3 p-6 text-center" id="chat-off">
          <p className="text-sm text-muted-foreground">{t('chat.off')}</p>
          {canConfigure && <Button size="sm" id="chat-turn-on" onClick={() => setCfg(true)}><Settings2 />{t('chat.settings.open')}</Button>}</div>
        : settings && <>{view === 'visitor' && <div className="flex shrink-0 items-center gap-2 border-b bg-muted/60 px-3 py-1.5 text-xs text-muted-foreground" id="chat-visitor-banner" role="status">
            <Eye className="size-3.5 shrink-0" /><span className="min-w-0 flex-1 truncate">{t('chat.visitorBanner')}</span>
            <Button size="xs" variant="link" id="chat-visitor-exit" onClick={() => setView('builder')}>{t('chat.visitorExit')}</Button></div>}
          <ChatThread turns={chat.session?.turns ?? []} mode={mode} replyField={settings.reply_field} events={chat.events} trace={chat.trace}
            pending={chat.pending} pendingFiles={chat.pendingFiles} running={chat.running} onAnswer={chat.answer} onRate={rate}
            onEdit={chat.edit} onRegenerate={chat.regenerate} onSource={chat.session?.source_session_id ? () => setSid(chat.session!.source_session_id!) : undefined}
            onSaveTest={canEdit ? saveCase : undefined} files={links} /></>}
      {!off && <ChatComposer disabled={!settings || waiting?.answered_by === 'reviewer'} running={chat.running} onStop={chat.cancel}
        placeholder={waiting ? t(waiting.answered_by === 'reviewer' ? 'chat.waitingReviewer' : 'chat.answerPlaceholder') : undefined}
        files={files} onError={setErr}
        onSend={(text, f) => waiting?.run_id ? chat.answer(waiting.run_id, text) : send(text, f)} />}
    </div>
    <ChatSettingsDialog wid={wid} open={cfg} onOpenChange={setCfg} onSaved={setSettings} />
    {draft && <TestCaseDialog wid={wid} value={draft} onClose={() => setDraft(null)} onSaved={() => { setDraft(null); setTab('tests') }} />}
    <ConfirmDeleteDialog open={!!del} onOpenChange={o => { if (!o) setDel(null) }} idPrefix="chat-delete" title={t('chat.deleteTitle')}
      name={deleteName} description={t('chat.deleteBody', { title: deleteName })}
      onConfirm={async () => { if (del) await remove(del) }} />
  </div>
}
