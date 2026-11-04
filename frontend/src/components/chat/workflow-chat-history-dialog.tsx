import { useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Eye, Funnel, Loader2, RefreshCw } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import { errorText, fmtDate } from '@/lib/i18n'
import { downShare, type ChatSession, type RatingTotals } from '@/lib/chat'
import { useLoadWhen } from '@/lib/use-when'
import { ChatThread, type FileLinks } from './chat-thread'
import { useChatRun, type ChatEndpoint } from './use-chat-run'
import { TestCaseDialog, type TestCase } from '@/components/editor/editor-tests-panel'
import { useStudioCtx } from '@/components/editor/studio-context'

/** Workflow review lives outside the chat composer. Existing APIs retain the same visibility and access checks. */
export function WorkflowChatHistoryDialog({ wid, open, onOpenChange, canEdit }: { wid: string; open: boolean; onOpenChange: (open: boolean) => void; canEdit: boolean }) {
  const { t } = useTranslation(); const { setTab } = useStudioCtx()
  const [source, setSource] = useState('visitors'); const [downOnly, setDownOnly] = useState(false)
  const [visitors, setVisitors] = useState<ChatSession[]>([]); const [mine, setMine] = useState<ChatSession[]>([])
  const [selected, setSelected] = useState(''); const [totals, setTotals] = useState<RatingTotals | null>(null)
  const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const [draft, setDraft] = useState<TestCase | null>(null); const request = useRef(0)
  const rows = source === 'visitors' ? visitors : mine
  const sid = rows.some(s => s.id === selected) ? selected : rows[0]?.id ?? null
  const endpoint = useMemo<ChatEndpoint>(() => ({ session: id => source === 'visitors'
    ? `/api/workflows/${wid}/chat/visitors/${id}` : `/api/chat/sessions/${id}?view=builder`, socket: '/ws/run' }), [wid, source])
  const read = useChatRun(open ? sid : null, 'builder', undefined, endpoint)
  const files = useMemo<FileLinks | undefined>(() => sid ? { url: id => source === 'visitors'
    ? `/api/workflows/${wid}/chat/visitors/${sid}/attachments/${id}` : `/api/chat/sessions/${sid}/attachments/${id}` } : undefined, [wid, sid, source])
  const load = async () => {
    const generation = ++request.current; const current = () => request.current === generation
    setLoading(true); setError('')
    const results = await Promise.allSettled([
      api<ChatSession[]>(`/api/workflows/${wid}/chat/visitors${downOnly ? '?thumbs_down=1' : ''}`).then(rows => { if (current()) setVisitors(rows) }),
      api<ChatSession[]>(`/api/workflows/${wid}/chat/sessions`).then(rows => { if (current()) setMine(rows) }),
      api<RatingTotals>(`/api/workflows/${wid}/chat/ratings`).then(value => { if (current()) setTotals(value) }),
    ])
    if (!current()) return
    const failed = results.find(r => r.status === 'rejected')
    if (failed?.status === 'rejected') setError(errorText(failed.reason))
    setLoading(false)
  }
  useLoadWhen(open, () => { setVisitors([]); setMine([]); setTotals(null); load() }, `${wid}:${downOnly}`)
  const saveCase = (rid: string) => api<Omit<TestCase, 'id' | 'last'>>(`/api/workflows/${wid}/tests/from-run/${rid}`, { method: 'POST' })
    .then(d => setDraft({ ...d, id: '', last: null })).catch(e => setError(errorText(e)))
  return <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent id="chat-history-dialog" className="flex h-[85dvh] min-h-0 min-w-0 flex-col gap-3 overflow-hidden sm:max-w-4xl">
        <DialogHeader className="shrink-0 pr-6 text-left"><DialogTitle>{t('chat.history.title')}</DialogTitle><DialogDescription>{t('chat.history.description')}</DialogDescription></DialogHeader>
        {totals && <div id="chat-rating-totals" className="grid shrink-0 grid-cols-2 gap-2">{([7, 30] as const).map(days => {
          const counts = days === 7 ? totals.d7 : totals.d30; const share = downShare(counts)
          return <div key={days} className="space-y-1 rounded-lg border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">{t('chat.history.period', { days })}</p>
            <p className="text-sm font-medium tabular-nums">{t('chat.history.counts', counts)}</p>
            {share !== null && <p className="text-xs text-muted-foreground">{t('chat.history.negativeShare', { share: `${share}%` })}</p>}
          </div>
        })}</div>}
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Tabs value={source} onValueChange={v => { setSource(v); setSelected('') }}><TabsList size="sm" aria-label={t('chat.history.title')}>
            <TabsTrigger value="visitors">{t('chat.visitors.tab')}</TabsTrigger><TabsTrigger value="mine">{t('chat.sessions')}</TabsTrigger>
          </TabsList></Tabs>
          {source === 'visitors' && <Button size="sm" variant={downOnly ? 'secondary' : 'outline'} id="chat-thumbs-down" aria-pressed={downOnly} title={t('chat.visitors.thumbsDownHint')} onClick={() => setDownOnly(v => !v)}><Funnel />{t('chat.visitors.thumbsDown')}</Button>}
          <Button size="icon-sm" variant="ghost" className="ml-auto" id="chat-history-refresh" aria-label={t('chat.history.refresh')} disabled={loading} onClick={() => { load(); read.reload() }}>{loading ? <Loader2 className="animate-spin" /> : <RefreshCw />}</Button>
        </div>
        {rows.length > 0 && <Select value={sid ?? ''} onValueChange={setSelected}><SelectTrigger id="chat-history-picker" className="w-full min-w-0 shrink-0" aria-label={t('chat.sessions')}><SelectValue /></SelectTrigger>
          <SelectContent>{rows.map(s => <SelectItem key={s.id} value={s.id}><span className="truncate">{s.title || t('chat.untitled')} · {fmtDate(s.updated)}</span></SelectItem>)}</SelectContent></Select>}
        {(error || read.error) && <Alert variant="destructive" className="shrink-0"><AlertCircle /><AlertDescription>{error || read.error}</AlertDescription></Alert>}
        <div className="flex shrink-0 items-start gap-2 text-xs text-muted-foreground"><Eye className="size-4 shrink-0" /><p>{t('chat.history.readOnly')}</p></div>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border" id="chat-history-thread">
          {sid ? <ChatThread turns={read.session?.turns ?? []} mode="full" events={[]} trace={read.trace} pending={null} running={false} files={files} onSaveTest={canEdit ? saveCase : undefined} />
            : <p className="m-auto p-4 text-sm text-muted-foreground">{t(loading ? 'chat.history.loading' : 'chat.history.empty')}</p>}
        </div>
      </DialogContent>
    </Dialog>
    {draft && <TestCaseDialog wid={wid} value={draft} onClose={() => setDraft(null)} onSaved={() => { setDraft(null); onOpenChange(false); setTab('tests') }} />}
  </>
}
