import { useEffect, useState } from 'react'
import { ExternalLink, AlertTriangle, FlaskConical, GitBranch, ShieldAlert, History, Workflow } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { JsonEditor } from '@/components/json-editor'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { HumanPanel } from '@/components/human-panel'
import { ChildWaitPanel } from '@/components/child-wait-panel'
import { TextLink } from '@/components/text-link'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import i18n from '@/lib/i18n'
import { useTranslation } from 'react-i18next'
import { RunTrace } from '@/components/run-trace'
import { fmtCost, fmtMs } from '@/lib/trace'
import { Tip } from '@/components/tip'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { api } from '@/lib/api'
import { EditorTestsPanel, TestCaseDialog, type TestCase } from './editor-tests-panel'
import { EditorCodePanel } from './editor-code-panel'
import { TimeTravelDialog } from './time-travel-dialog'
import { useStudioCtx } from './studio-context'
import { useIsMobile } from '@/lib/use-viewport-width'

/** Bottom panel (TASK-0085): Run (input | logs side by side, a picker for the last runs and a dialog with all of them),
 * Test (TASK-0067) and Code (TASK-0071). Chat lives in its own side panel (components/chat/chat-side-panel.tsx). */
export function EditorRunPanel() {
  const { t } = useTranslation()
  const { input, setInput, log, setLog, errors, history, tab, setTab, running, traceSel, setTraceSel, replay, setReplay, openRun, respond, fork, trace, traceMeta, wid, source, edit } = useStudioCtx()
  // the "Test runs" switch lists the workflow's test runs instead of its other runs (TASK-0067)
  const [testRuns, setTestRuns] = useState<any[] | null>(null)
  const mobile = useIsMobile()  // phones (TASK-0121): input above the logs instead of beside them
  const showTests = (on: boolean) => { if (!on || !wid) { setTestRuns(null); return } api<any[]>(`/api/workflows/${wid}/runs?tests=true`).then(setTestRuns).catch(() => setTestRuns([])) }
  const rows = testRuns ?? history
  // Save as test case (TASK-0068): a draft from the run opens in the test case editor; once saved, the Tests tab shows it
  const [draft, setDraft] = useState<TestCase | null>(null); const [picked, setPicked] = useState<string | null>(null); const [draftErr, setDraftErr] = useState('')
  const canSave = !!wid && edit && !source
  const saveCase = (rid: string) => api<Omit<TestCase, 'id' | 'last'>>(`/api/workflows/${wid}/tests/from-run/${rid}`, { method: 'POST' })
    .then(d => { setDraftErr(''); setDraft({ ...d, id: '', last: null }) }).catch(e => setDraftErr(e.message))
  const saveButton = (rid: string) => <Tip tip={t('tests.saveFromRun')}>
    <Button size="icon-xs" variant="ghost" data-testid="save-test" aria-label={t('tests.saveFromRun')} onClick={() => saveCase(rid)}><FlaskConical /></Button></Tip>
  const finished = (s: string) => s !== 'running' && s !== 'queued' && s !== 'idle'
  const mode = tab === 'tests' ? 'test' : tab === 'code' ? 'code' : 'run'
  const [allOpen, setAllOpen] = useState(false); const [travel, setTravel] = useState(false)
  const canTravel = !!wid && !source && !running && !!trace.runId && finished(trace.status) && trace.status !== 'waiting'
  const pick = rows.find(h => h.id === trace.runId)
  const forkedFrom = (log as any[]).find(e => e.type === 'run_started')?.forked_from as { run_id: string; checkpoint: number } | undefined
  // a run waiting for a workflow tool's child (TASK-0135) goes on by itself in the worker: look again until it moves on
  const child = !running ? trace.waiting?.child : undefined
  useEffect(() => {
    if (!child || !wid) return
    const id = window.setInterval(() => api<any[]>(`/api/workflows/${wid}/runs`).then(rs => {
      const h = rs.find(r => r.id === trace.runId); if (h && h.status !== 'waiting') openRun(h) }).catch(() => {}), 2000)
    return () => window.clearInterval(id)
  }, [child?.runId, wid, trace.runId])  // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="h-full min-h-0 flex flex-col">
      <div className="flex h-11 shrink-0 items-center gap-2 border-b px-3" id="run-toolbar">
        <Tabs value={mode} onValueChange={v => setTab(v === 'test' ? 'tests' : v === 'code' ? 'code' : 'logs')}>
          <TabsList aria-label={t('editor.panelModes')}>
            <TabsTrigger value="run" id="run-tab">{t('editor.tabRun')}</TabsTrigger>
            {!source && <TabsTrigger value="test" id="tests-tab">{t('tests.tab')}</TabsTrigger>}
            {!source && <TabsTrigger value="code" id="code-tab">{t('codeView.tab')}</TabsTrigger>}
          </TabsList>
        </Tabs>
        {mode === 'run' && <>
          <Select value={pick ? pick.id : ''} onValueChange={id => { const h = rows.find(x => x.id === id); if (h) openRun(h) }}>
            <SelectTrigger variant="ghost" className="w-auto min-w-56 max-md:min-w-0 max-md:flex-1" id="run-picker" aria-label={t('editor.pickRun')}><SelectValue placeholder={t('editor.pickRun')} /></SelectTrigger>
            <SelectContent>{rows.slice(0, 10).map(h => <SelectItem key={h.id} value={h.id}>
              <Badge variant={h.status === 'ok' ? 'success' : h.status === 'waiting' ? 'outline' : h.status === 'cancelled' ? 'secondary' : 'destructive'}>{t(`status.${h.status}`)}</Badge>
              <span className="inline-flex items-baseline gap-1.5 text-xs"><span className="tabular-nums text-muted-foreground" data-slot="run-time">{new Date(h.started * 1000).toLocaleTimeString(i18n.resolvedLanguage)}</span>
              <span className="font-mono tabular-nums" data-slot="run-id">{h.id}</span></span></SelectItem>)}</SelectContent></Select>
          <Button variant="ghost" id="history-all" onClick={() => setAllOpen(true)}><History /><span className="max-md:sr-only">{t('editor.viewAllRuns')}</span></Button>
        </>}
        {errors.length > 0 && <Badge variant="destructive">{t('editor.errorsBadge', { count: errors.length })}</Badge>}
      </div>
      {mode === 'run' && <ResizablePanelGroup key={mobile ? 'v' : 'h'} orientation={mobile ? 'vertical' : 'horizontal'} className="min-h-0 flex-1">
        <ResizablePanel id="run-input-panel" defaultSize="35%" minSize="20%" className="min-h-0"><div className="flex h-full min-h-0 flex-col gap-2 p-3">
          <span className="text-xs font-medium text-muted-foreground">{t('editor.tabInput')}</span>
          <JsonEditor id="run-input" value={input} onChange={setInput} className="min-h-0 flex-1" />
          {errors.length > 0 && <ScrollArea className="max-h-40 shrink-0"><Alert variant="destructive" id="validation-errors"><AlertTriangle /><AlertTitle>{t('editor.errorsTitle', { count: errors.length })}</AlertTitle>
            <AlertDescription><ul className="list-disc pl-4 space-y-0.5 text-xs">{errors.map((e, i) => <li key={i} className="break-words">{e}</li>)}</ul></AlertDescription></Alert></ScrollArea>}
        </div></ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel id="run-logs-panel" minSize="30%" className="min-h-0"><div className="flex h-full min-h-0 flex-col">
          {forkedFrom && <p className="flex shrink-0 items-center gap-1.5 border-b px-3 py-1.5 text-xs text-muted-foreground" id="trace-forked-from">
            <GitBranch className="size-3.5" />{t('timeTravel.forkedFrom', { run: forkedFrom.run_id, n: forkedFrom.checkpoint + 1 })}</p>}
          {pick?.parent && <p className="flex shrink-0 items-center gap-1.5 border-b px-3 py-1.5 text-xs text-muted-foreground" id="trace-called-by">
            <Workflow className="size-3.5" />{t('childRuns.calledBy', { name: pick.parent.workflow_name || t('childRuns.unknown') })}
            {pick.parent.workflow_name && <TextLink to={`/workflows/${pick.parent.workflow_id}?run=${pick.parent.run_id}`} id="trace-open-parent">{t('childRuns.openParent')}</TextLink>}</p>}
          {trace.waiting?.runId && !running && (trace.waiting.child
            ? <ChildWaitPanel child={trace.waiting.child} name={pick?.waiting_for?.workflow_name} status={pick?.waiting_for?.status} />
            : <HumanPanel waiting={trace.waiting} onRespond={r => respond(trace.waiting!.runId!, r, trace.waiting!.node)} />)}
          <RunTrace trace={trace} events={log as any} meta={traceMeta} selected={traceSel} onSelect={sp => setTraceSel(sp?.key ?? null)}
            replay={replay ?? undefined} onExitReplay={() => { setReplay(null); setLog([]); setTraceSel(null) }}
            actions={canTravel || (canSave && !running && trace.runId && finished(trace.status)) ? <>
              {canTravel && <Button variant="ghost" size="xs" id="trace-time-travel" onClick={() => setTravel(true)}><GitBranch />{t('timeTravel.open')}</Button>}
              {canSave && !running && trace.runId && finished(trace.status) && <Button variant="ghost" size="xs" id="trace-save-test"
                onClick={() => saveCase(trace.runId!)}><FlaskConical />{t('tests.saveFromRun')}</Button>}</> : undefined} />
          {trace.runId && <TimeTravelDialog runId={trace.runId} open={travel} onOpenChange={setTravel} onFork={(i, s) => fork(trace.runId!, i, s)} />}
        </div></ResizablePanel>
      </ResizablePanelGroup>}
      {mode === 'test' && <div className="min-h-0 flex-1"><EditorTestsPanel select={picked} /></div>}
      {mode === 'code' && <div className="min-h-0 flex-1"><EditorCodePanel /></div>}
      <Dialog open={allOpen} onOpenChange={setAllOpen}>
        <DialogContent className="flex max-h-[80vh] flex-col sm:max-w-4xl" id="history-dialog">
          <DialogHeader><DialogTitle>{t('editor.tabHistory')}</DialogTitle><DialogDescription>{t('editor.historyDesc')}</DialogDescription></DialogHeader>
          <ScrollArea className="min-h-0 flex-1"><div onClick={e => { if ((e.target as HTMLElement).closest('[data-testid=history-row]')) setAllOpen(false) }}>
          <div className="p-3 space-y-1">
            {wid && !source && <div className="flex items-center gap-2 pb-1"><Switch id="history-tests" checked={testRuns !== null} onCheckedChange={showTests} />
              <Label htmlFor="history-tests" className="text-xs font-normal">{t('tests.showRuns')}</Label></div>}
            {!rows.length && <span className="text-muted-foreground text-xs">{t('editor.noRuns')}</span>}
            {draftErr && <Alert variant="destructive"><AlertDescription>{draftErr}</AlertDescription></Alert>}
            {rows.map(h => <div key={h.id} className="flex items-center gap-1">
              <button data-testid="history-row" onClick={() => openRun(h)}
              className="min-w-0 flex-1 flex items-center gap-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent">
              <span className="w-16 shrink-0"><Badge variant={h.status === 'ok' ? 'success' : h.status === 'timeout' ? 'warning' : h.status === 'cancelled' || h.status === 'expired' || h.status === 'paused' ? 'secondary' : h.status === 'waiting' ? 'outline' : 'destructive'}>{t(`status.${h.status}`)}</Badge></span>
              <span className="w-20 shrink-0 text-muted-foreground tabular-nums">{new Date(h.started * 1000).toLocaleTimeString(i18n.resolvedLanguage)}</span>
              <span className="w-20 shrink-0 font-mono text-muted-foreground">{h.id}</span>
              <span className="flex w-28 shrink-0 items-center gap-1">
              {h.source === 'api' && <Badge variant="outline" data-testid="history-source">API</Badge>}
              {h.source === 'schedule' && <Badge variant="outline" data-testid="history-source">{t('schedules.badge')}</Badge>}
              {h.source === 'chat' && <Tip tip={t('chatTriggers.from', { sender: h.chat?.sender ?? '?', trigger: h.chat?.trigger ?? '—' })}>
                <Badge variant="outline" data-testid="history-source">{h.chat?.kind && <ChannelLogo kind={h.chat.kind} className="size-3" />}{t('chatTriggers.badge')}</Badge></Tip>}
              {h.source === 'test' && <Badge variant="outline" data-testid="history-source">{t('tests.badge')}</Badge>}
              {h.source === 'tool' && <Tip tip={t('childRuns.calledBy', { name: h.parent?.workflow_name || t('childRuns.unknown') })}>
                <Badge variant="outline" data-testid="history-source"><Workflow className="size-3" />{t('childRuns.badge')}</Badge></Tip>}
              {h.code_runtime === 'subprocess' && <Tip tip={t('code.runUnisolated')}><Badge variant="warning" data-testid="history-unisolated"><ShieldAlert className="size-3" /></Badge></Tip>}
              <Tip tip={h.version ? t('versions.runVersion', { n: h.version }) : t('versions.runUnsaved')}>
                <Badge variant="secondary" data-testid="history-version">{h.version ? `v${h.version}` : t('versions.unsaved')}</Badge></Tip></span>
              <span className="min-w-0 truncate">{JSON.stringify(h.input)}</span>
              <span className="ml-auto flex shrink-0 items-center gap-2 text-muted-foreground tabular-nums">
                {h.metrics && <span className="w-20 text-right" data-testid="history-tokens">{t('trace.tokens', { count: h.metrics.tokens })}</span>}
                {h.metrics && <span className="w-12 text-right" data-testid="history-cost">{fmtCost(h.metrics.cost_usd)}</span>}
                <span className="flex w-16 justify-end">{h.metrics?.error_count > 0 && <Badge variant="destructive">{t('trace.errorCount', { count: h.metrics.error_count })}</Badge>}</span>
                <span className="w-14 text-right">{fmtMs(h.metrics?.duration_ms ?? (h.ended - h.started) * 1000)}</span>
                {h.trace_url && <ExternalLink className="size-3.5" aria-label={t('trace.openTrace')} />}{/* link itself is in the replayed timeline (no <a> inside a button) */}
              </span>
            </button>
            {canSave && <span className="flex w-6 shrink-0 justify-center">{finished(h.status) && saveButton(h.id)}</span>}</div>)}
          </div>
          </div></ScrollArea>
        </DialogContent>
      </Dialog>
      {draft && wid && <TestCaseDialog wid={wid} value={draft} onClose={() => setDraft(null)} onSaved={c => { setDraft(null); setPicked(c.id); setTab('tests') }} />}
    </section>
}
