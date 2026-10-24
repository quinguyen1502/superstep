import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, ChevronDown, CircleDashed, Copy, ExternalLink, Send, FlaskConical, GitCompare, History, Loader2, Pencil, Play, Plus, Square, Trash2, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { JsonEditor } from '@/components/json-editor'
import { Tip } from '@/components/tip'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import i18n from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { useStudioCtx } from './studio-context'

/** Workflow tests (TASK-0067, REQ-0042): test cases with an input, Human answers and checks; Run all / run one on the
 * saved version, with the offline mock model as an option; each case's checks with expected and actual values.
 * TASK-0068: each result compared with the latest suite run on an earlier version, Run against version, the suite
 * history, and checks that name a node or field no longer in the graph marked as stale. */
type Kind = 'status' | 'field' | 'node' | 'duration' | 'cost'
export type TestCheck = { kind: Kind; value?: string; field?: string; op?: string; node?: string; ran?: boolean; max?: number }
type CheckResult = TestCheck & { passed: boolean | null; expected: string; actual: string | null; reason: string | null }
type Change = 'regression' | 'fixed' | 'still_failing' | 'still_passing' | 'new'
export type TestCase = { id: string; name: string; input: Record<string, unknown>; answers: Record<string, string[]>; checks: TestCheck[]
  last: { status: string; suite_id: string; version: number | null } | null }
type Result = { id: string; test_id: string; name: string; status: string; run_id: string | null; version: number | null
  reason: string | null; detail: string | null; checks: CheckResult[]; change: Change | null }
type Suite = { id: string; status: string; mock: boolean; total: number; passed: number; failed: number; version: number | null; started: number
  by: string | null; langsmith_url?: string | null; results?: Result[]; compare?: { suite_id: string; version: number; counts: Record<Change, number> } | null }
type Listing = { items: TestCase[]; suites: Suite[]; can_edit: boolean; limit: number; langsmith?: boolean; langsmith_configured?: boolean }

const KINDS: Kind[] = ['status', 'field', 'node', 'duration', 'cost']
const OPS = ['equals', 'contains', 'not_contains', 'matches', 'empty', 'not_empty']
const NO_VALUE = ['empty', 'not_empty']
const STATUSES = ['ok', 'error', 'waiting']
const POLL_MS = 1000
const CHANGES: Change[] = ['regression', 'fixed', 'new', 'still_failing', 'still_passing']
const changeVariant = (c: Change) => c === 'regression' ? 'destructive' : c === 'fixed' ? 'success' : c === 'new' ? 'outline' : 'secondary'
/** A check that names a node or a state field the graph no longer has (the run fails it with that reason). */
const isStale = (c: TestCheck, nodeIds: string[], fields: string[]) =>
  (c.kind === 'node' && !!c.node && !nodeIds.includes(c.node)) || (c.kind === 'field' && !!c.field && !fields.includes(c.field))
const when = (ts: number) => new Date(ts * 1000).toLocaleString(i18n.resolvedLanguage)
const blank = (k: Kind): TestCheck => ({ status: { kind: k, value: 'ok' }, field: { kind: k, field: '', op: 'equals', value: '' }, node: { kind: k, node: '', ran: true },
  duration: { kind: k, max: 30 }, cost: { kind: k, max: 0.05 } } as Record<Kind, TestCheck>)[k]
const variant = (s?: string) => s === 'passed' ? 'success' : s === 'failed' ? 'destructive' : s === 'running' || s === 'queued' ? 'outline' : 'secondary'

/** `select`: the case to show first (a case just saved from a run). */
export function EditorTestsPanel({ select }: { select?: string | null }) {
  const { t } = useTranslation()
  const { wid, nodes, fieldNames, isDirty, openRun } = useStudioCtx()
  const [versions, setVersions] = useState<{ version: number; created: number }[] | null>(null)
  const [list, setList] = useState<Listing | null>(null); const [suite, setSuite] = useState<Suite | null>(null)
  const [sel, setSel] = useState<string | null>(null); const [mock, setMock] = useState(false); const [err, setErr] = useState('')
  const [editing, setEditing] = useState<TestCase | 'new' | null>(null)
  const del = useConfirmDelete()
  const label = (id: string) => (nodes.find(n => n.id === id)?.data as any)?.label || id
  const loadSuite = (sid: string) => api<Suite>(`/api/workflows/${wid}/tests/runs/${sid}`).then(setSuite)
  const load = () => wid && api<Listing>(`/api/workflows/${wid}/tests`).then(d => {
    setList(d); setErr(''); setSel(s => [s, select].find(x => x && d.items.some(c => c.id === x)) ?? d.items[0]?.id ?? null)  // keep the choice, else the first case
    if (d.suites[0]) return loadSuite(d.suites[0].id) })
    .catch(e => setErr(e.message))
  useEffect(() => { load() }, [wid])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {  // follow a running suite until it ends, then refresh each case's last result
    if (!suite || suite.status !== 'running') return
    const h = setInterval(() => loadSuite(suite.id).then(() => {}).catch(() => {}), POLL_MS)
    return () => clearInterval(h)
  }, [suite?.id, suite?.status])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (suite && suite.status !== 'running') load() }, [suite?.status])  // eslint-disable-line react-hooks/exhaustive-deps

  const act = (p: Promise<unknown>) => p.then(() => setErr('')).catch(e => setErr(e.message))
  const runTests = (ids?: string[], version?: number) => act(api<Suite>(`/api/workflows/${wid}/tests/run`, { method: 'POST',
    json: { mock, ...(ids ? { test_ids: ids } : {}), ...(version ? { version } : {}) } }).then(setSuite))
  const loadVersions = () => api<{ items: { version: number; created: number; current: boolean }[] }>(`/api/workflows/${wid}/versions`)
    .then(d => setVersions(d.items.filter(v => !v.current))).catch(e => setErr(e.message))
  const cancel = () => suite && act(api<Suite>(`/api/workflows/${wid}/tests/runs/${suite.id}/cancel`, { method: 'POST' }).then(setSuite))
  const [sending, setSending] = useState(false)
  const sendToLangSmith = () => { if (!suite) return; setSending(true)
    act(api<Suite>(`/api/workflows/${wid}/tests/runs/${suite.id}/langsmith`, { method: 'POST' }).then(setSuite)).finally(() => setSending(false)) }
  const openTestRun = (rid: string) => act(api<any[]>(`/api/workflows/${wid}/runs?tests=true`).then(rs => { const h = rs.find(x => x.id === rid); if (h) openRun(h) }))
  const remove = (c: TestCase) => del.ask({ title: t('tests.deleteTitle', { name: c.name }), name: c.name,
    onConfirm: async () => { await api(`/api/workflows/${wid}/tests/${c.id}`, { method: 'DELETE' }); await load() } })

  if (!wid) return <p className="p-3 text-xs text-muted-foreground">{t('tests.saveFirst')}</p>
  const running = suite?.status === 'running'; const edit = !!list?.can_edit
  const resultOf = (id: string) => suite?.results?.find(r => r.test_id === id)
  const cur = list?.items.find(c => c.id === sel); const res = sel ? resultOf(sel) : undefined
  const nodeIds = nodes.map(n => n.id); const cmp = suite?.compare
  return <div className="flex h-full min-h-0 flex-col" id="tests-panel">
    <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
      {edit && <Button id="tests-run-all" onClick={() => runTests()} disabled={running || !list?.items.length}>{running ? <Loader2 className="animate-spin" /> : <Play />}{t('tests.runAll')}</Button>}
      {edit && <DropdownMenu onOpenChange={o => { if (o) loadVersions() }}>
        <DropdownMenuTrigger asChild><Button variant="outline" id="tests-run-version" disabled={running || !list?.items.length}><GitCompare />{t('tests.runVersion')}<ChevronDown /></Button></DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {versions?.length === 0 && <DropdownMenuItem disabled>{t('tests.noVersions')}</DropdownMenuItem>}
          {versions?.map(v => <DropdownMenuItem key={v.version} data-testid="run-version" onSelect={() => runTests(undefined, v.version)}>
            v{v.version}<span className="ml-auto pl-4 text-xs text-muted-foreground">{when(v.created)}</span></DropdownMenuItem>)}
        </DropdownMenuContent></DropdownMenu>}
      {edit && running && <Button variant="outline" id="tests-cancel" onClick={cancel}><Square />{t('common.cancel')}</Button>}
      {edit && <div className="flex items-center gap-2"><Switch id="tests-mock" checked={mock} onCheckedChange={setMock} /><Label htmlFor="tests-mock" className="text-xs font-normal">{t('tests.mock')}</Label></div>}
      {suite && <span className="flex items-center gap-2 text-xs text-muted-foreground" id="tests-summary">
        {running ? t('tests.running', { done: suite.passed + suite.failed, total: suite.total })
          : t('tests.summary', { passed: suite.passed, failed: suite.failed, version: suite.version ?? '—' })}
        {suite.status === 'cancelled' && <Badge variant="secondary">{t('status.cancelled')}</Badge>}{suite.mock && <Badge variant="outline">{t('tests.mockBadge')}</Badge>}</span>}
      <span className="ml-auto" />
      {suite && !running && (suite.langsmith_url || (edit && list?.langsmith_configured)) && <DropdownMenu>
        <DropdownMenuTrigger asChild><Button variant="outline" id="tests-langsmith">{sending ? <Loader2 className="animate-spin" /> : <ExternalLink />}{t('tests.langsmith')}<ChevronDown /></Button></DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-56">
          {suite.langsmith_url && <DropdownMenuItem asChild><a id="tests-langsmith-link" href={suite.langsmith_url} target="_blank" rel="noreferrer"><ExternalLink />{t('tests.openLangSmith')}</a></DropdownMenuItem>}
          {edit && <DropdownMenuItem id="tests-langsmith-send" disabled={sending || !list?.langsmith_configured} onSelect={sendToLangSmith}><Send />
            {list?.langsmith_configured ? t('tests.sendLangSmith') : <span className="flex flex-col">{t('tests.sendLangSmith')}<span className="text-xs text-muted-foreground" id="tests-langsmith-reason">{t('tests.langsmithNotConfigured')}</span></span>}</DropdownMenuItem>}
        </DropdownMenuContent></DropdownMenu>}
      {!!list?.suites.length && <DropdownMenu>
        <Tip tip={t('tests.history')}><DropdownMenuTrigger asChild><Button variant="outline" size="icon" id="tests-history" aria-label={t('tests.history')}><History /></Button></DropdownMenuTrigger></Tip>
        <DropdownMenuContent align="end" className="w-96">{list.suites.map(h => <DropdownMenuItem key={h.id} data-testid="suite-row" onSelect={() => loadSuite(h.id).catch(e => setErr(e.message))}>
          <Check className={cn('size-3.5', suite?.id !== h.id && 'invisible')} />
          <span>{h.status === 'running' ? t('tests.status.running') : t('tests.historyItem', { version: h.version ?? '—', passed: h.passed, failed: h.failed })}</span>
          <span className="ml-auto pl-4 text-xs text-muted-foreground">{[h.by, when(h.started)].filter(Boolean).join(' · ')}</span></DropdownMenuItem>)}
        </DropdownMenuContent></DropdownMenu>}
      {edit && <Button variant="outline" id="tests-add" disabled={!!list && list.items.length >= list.limit} onClick={() => setEditing('new')}><Plus />{t('tests.add')}</Button>}
    </div>
    {suite && !running && suite.version != null && <div className="flex flex-wrap items-center gap-2 border-b px-3 py-1.5 text-xs" id="tests-compare">
      {cmp ? <><span className="text-muted-foreground">{t('tests.comparedWith', { version: cmp.version })}</span>
        {CHANGES.filter(k => cmp.counts[k]).map(k => <Badge key={k} variant={changeVariant(k)} data-testid={`compare-${k}`}>{t(`tests.change.${k}`)}<span className="tabular-nums">{cmp.counts[k]}</span></Badge>)}</>
        : <span className="text-muted-foreground" id="tests-no-baseline">{t('tests.noBaseline')} {edit && t('tests.runVersionHelp')}</span>}
    </div>}
    {edit && isDirty() && <p className="border-b px-3 py-1.5 text-xs text-warning" id="tests-unsaved">{t('tests.unsaved')}</p>}
    {err && <Alert variant="destructive" className="m-2 w-auto"><AlertDescription>{err}</AlertDescription></Alert>}
    <div className="flex min-h-0 flex-1">
      <ScrollArea className="w-64 shrink-0 border-r"><div className="space-y-0.5 p-2">
        {list && !list.items.length && <p className="p-1 text-xs text-muted-foreground">{t(edit ? 'tests.empty' : 'tests.emptyViewer')}</p>}
        {list?.items.map(c => { const r = resultOf(c.id); const s = r?.status ?? c.last?.status
          return <button key={c.id} data-testid="test-row" onClick={() => setSel(c.id)}
            className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent', sel === c.id && 'bg-accent')}>
            <span className="min-w-0 flex-1 truncate">{c.name}</span>
            {r?.change === 'regression' || r?.change === 'fixed'  // says failed / passed too
              ? <Badge variant={changeVariant(r.change)} data-testid="test-change">{t(`tests.change.${r.change}`)}</Badge>
              : s && <Badge variant={variant(s)} data-testid="test-status">{t(`tests.status.${s}`)}</Badge>}</button> })}
      </div></ScrollArea>
      <ScrollArea className="min-w-0 flex-1"><div className="space-y-3 p-3">
        {!cur && <p className="text-xs text-muted-foreground">{t('tests.pick')}</p>}
        {cur && <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{cur.name}</span>
          {res && <Badge variant={variant(res.status)} data-testid="result-status">{t(`tests.status.${res.status}`)}</Badge>}
          {res?.version && <Badge variant="secondary">v{res.version}</Badge>}
          {res?.change && <Badge variant={changeVariant(res.change)} data-testid="result-change">{t(`tests.change.${res.change}`)}</Badge>}
          <span className="ml-auto flex items-center gap-1">
            {res?.run_id && <Button size="sm" variant="ghost" data-testid="result-open-run" onClick={() => openTestRun(res.run_id!)}><ExternalLink />{t('tests.openRun')}</Button>}
            {edit && <Tip tip={t('tests.runOne')}><Button size="icon" variant="ghost" aria-label={t('tests.runOne')} disabled={running} onClick={() => runTests([cur.id])}><Play /></Button></Tip>}
            {edit && <Tip tip={t('tests.edit')}><Button size="icon" variant="ghost" aria-label={t('tests.edit')} data-testid="test-edit" onClick={() => setEditing(cur)}><Pencil /></Button></Tip>}
            {edit && <Tip tip={t('tests.duplicate')}><Button size="icon" variant="ghost" aria-label={t('tests.duplicate')} onClick={() => setEditing({ ...cur, id: '', name: t('tests.copyOf', { name: cur.name }) })}><Copy /></Button></Tip>}
            {edit && <Tip tip={t('common.delete')}><Button size="icon" variant="ghost" aria-label={t('common.delete')} data-testid="test-delete" onClick={() => remove(cur)}><Trash2 /></Button></Tip>}
          </span></div>}
        {res?.reason && <p className="text-xs text-destructive" data-testid="result-reason">{t(`tests.reason.${res.reason}`, { node: label(res.detail ?? ''), status: t(`status.${res.detail}`) })}</p>}
        {cur && <table className="w-full text-xs" data-testid="result-checks"><thead className="text-muted-foreground"><tr className="text-left">
          <th className="w-6 py-1 font-normal" /><th className="py-1 font-normal">{t('tests.check')}</th><th className="w-1/4 py-1 font-normal">{t('tests.expected')}</th><th className="w-1/4 py-1 font-normal">{t('tests.actual')}</th></tr></thead>
          <tbody>{(res?.checks ?? cur.checks.map(c => ({ ...c, passed: undefined } as any))).map((c: CheckResult, i: number) => <tr key={i} className="border-t align-top leading-5" data-testid="check-row">
            <td className="py-1"><span className="flex h-5 items-center">{/* centred on the first text line */}
              {c.passed === true ? <Check className="size-3.5 text-success" /> : c.passed === false ? <X className="size-3.5 text-destructive" /> : c.passed === null ? <CircleDashed className="size-3.5 text-muted-foreground" /> : null}</span></td>
            <td className="py-1 pr-2">{describe(t, c, label)}{isStale(c, nodeIds, fieldNames) && <Badge variant="warning" className="ml-2 align-middle" data-testid="check-stale">{t('tests.stale')}</Badge>}</td>
            <td className="py-1 pr-2 font-mono break-all">{res ? shown(t, c, c.expected) : ''}</td>
            <td className="py-1 font-mono break-all">{res ? (c.reason ? <span className="font-sans text-muted-foreground">{t(`tests.reason.${c.reason}`, { node: label(c.node ?? '') })}</span> : shown(t, c, c.actual)) : ''}</td></tr>)}</tbody></table>}
      </div></ScrollArea>
    </div>
    {editing && <TestCaseDialog wid={wid} value={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={c => { setEditing(null); setSel(c.id); load() }} />}
    {del.dialog}
  </div>
}

function describe(t: (k: string, o?: any) => string, c: TestCheck, label: (id: string) => string): string {
  if (c.kind === 'status') return t('tests.desc.status', { value: t(`status.${c.value}`) })
  if (c.kind === 'field') return t(NO_VALUE.includes(c.op || '') ? 'tests.desc.fieldNoValue' : 'tests.desc.field', { field: c.field, op: t(`tests.op.${c.op}`), value: c.value })
  if (c.kind === 'node') return t(c.ran ? 'tests.desc.ran' : 'tests.desc.notRan', { node: label(c.node || '') })
  return t(`tests.desc.${c.kind}`, { max: c.max })
}

function shown(t: (k: string) => string, c: TestCheck, v: string | null): string {
  if (v === null) return '—'
  if (c.kind === 'status') return t(`status.${v}`)
  if (c.kind === 'node') return t(`tests.ran.${v}`)
  if (c.kind === 'field' && NO_VALUE.includes(v)) return t(`tests.op.${v}`)
  return v
}

/** Add or change a test case: name, input (JSON), answers per Human node, checks. `value.id === ''` adds a copy or a
 * draft (Duplicate, Save as test case). */
export function TestCaseDialog({ wid, value, onClose, onSaved }: { wid: string; value: TestCase | null; onClose: () => void; onSaved: (c: TestCase) => void }) {
  const { t } = useTranslation()
  const { nodes, fieldNames, input: runInput } = useStudioCtx()
  const [name, setName] = useState(value?.name ?? ''); const [input, setInput] = useState(value ? JSON.stringify(value.input, null, 2) : runInput)
  const [answers, setAnswers] = useState<Record<string, string[]>>(value?.answers ?? {})
  const [checks, setChecks] = useState<TestCheck[]>(value?.checks ?? [blank('status')]); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const humans = nodes.filter(n => n.type === 'human'); const graphNodes = nodes.filter(n => n.type !== 'note')
  const setCheck = (i: number, c: TestCheck) => setChecks(cs => cs.map((x, j) => j === i ? c : x))
  const setAnswer = (nid: string, list: string[]) => setAnswers(a => ({ ...a, [nid]: list }))
  const save = async () => {
    let parsed: unknown; try { parsed = JSON.parse(input || '{}') } catch { setErr(t('editor.badInput')); return }
    setBusy(true); setErr('')
    const body = { name, input: parsed, answers, checks }
    try {
      onSaved(value?.id ? await api<TestCase>(`/api/workflows/${wid}/tests/${value.id}`, { method: 'PUT', json: body })
        : await api<TestCase>(`/api/workflows/${wid}/tests`, { method: 'POST', json: body }))
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return <Dialog open onOpenChange={o => { if (!o) onClose() }}>
    <DialogContent className="flex max-h-[90vh] flex-col overflow-hidden sm:max-w-2xl" id="test-dialog">
      <DialogHeader className="shrink-0"><DialogTitle className="flex items-center gap-2"><FlaskConical className="size-4" />{t(value?.id ? 'tests.editTitle' : 'tests.addTitle')}</DialogTitle>
        <DialogDescription>{t('tests.dialogDesc')}</DialogDescription></DialogHeader>
      <div className="-mx-1 min-h-0 flex-1 space-y-4 overflow-y-auto px-1 py-1">
        <div className="space-y-1.5"><Label htmlFor="test-name">{t('tests.name')}</Label><Input id="test-name" value={name} onChange={e => setName(e.target.value)} maxLength={120} /></div>
        <div className="space-y-1.5"><Label htmlFor="test-input">{t('tests.input')}</Label><JsonEditor id="test-input" value={input} onChange={setInput} className="h-32" /></div>
        {humans.length > 0 && <div className="space-y-2"><Label>{t('tests.answers')}</Label><p className="text-xs text-muted-foreground">{t('tests.answersHelp')}</p>
          {humans.map(h => { const list = answers[h.id] ?? []
            return <div key={h.id} className="space-y-1.5 rounded-md border p-2" data-testid="answers-node">
              <div className="text-xs font-medium">{(h.data as any)?.label || h.id}</div>
              {list.map((a, i) => { const kind = a === 'approved' || a === 'rejected' ? a : 'text'
                return <div key={i} className="flex gap-2">
                  <Select value={kind} onValueChange={k => setAnswer(h.id, list.map((x, j) => j === i ? (k === 'text' ? '' : k) : x))}>
                    <SelectTrigger className="w-36" aria-label={t('tests.answer')} data-testid="answer-kind"><SelectValue /></SelectTrigger>
                    <SelectContent>{['approved', 'rejected', 'text'].map(k => <SelectItem key={k} value={k}>{t(`tests.answerKinds.${k}`)}</SelectItem>)}</SelectContent></Select>
                  {kind === 'text' && <Input className="flex-1 text-xs" aria-label={t('tests.answerText')} value={a} onChange={e => setAnswer(h.id, list.map((x, j) => j === i ? e.target.value : x))} />}
                  <Button size="icon" variant="ghost" aria-label={t('common.delete')} onClick={() => setAnswer(h.id, list.filter((_, j) => j !== i))}><X /></Button></div> })}
              <Button size="sm" variant="outline" data-testid="answer-add" onClick={() => setAnswer(h.id, [...list, 'approved'])}><Plus />{t('tests.addAnswer')}</Button>
            </div> })}</div>}
        <div className="space-y-2"><Label>{t('tests.checks')}</Label>
          {checks.map((c, i) => <div key={i} className="flex flex-wrap items-center gap-2" data-testid="check-edit">
            <Select value={c.kind} onValueChange={k => setCheck(i, blank(k as Kind))}>
              <SelectTrigger className="w-36" aria-label={t('tests.kind')} data-testid="check-kind"><SelectValue /></SelectTrigger>
              <SelectContent>{KINDS.map(k => <SelectItem key={k} value={k}>{t(`tests.kinds.${k}`)}</SelectItem>)}</SelectContent></Select>
            {c.kind === 'status' && <Pick value={c.value} opts={STATUSES.map(s => [s, t(`status.${s}`)])} label={t('tests.kinds.status')} onChange={v => setCheck(i, { ...c, value: v })} />}
            {c.kind === 'field' && <>
              <Pick value={c.field} opts={fieldNames.map(f => [f, f])} label={t('tests.field')} placeholder={t('tests.field')} testid="check-field" onChange={v => setCheck(i, { ...c, field: v })} />
              <Pick value={c.op} opts={OPS.map(o => [o, t(`tests.op.${o}`)])} label={t('tests.compare')} testid="check-op" onChange={v => setCheck(i, { ...c, op: v })} />
              {!NO_VALUE.includes(c.op || '') && <Input className="min-w-24 flex-1 text-xs" aria-label={t('tests.value')} data-testid="check-value" value={c.value ?? ''} onChange={e => setCheck(i, { ...c, value: e.target.value })} />}</>}
            {c.kind === 'node' && <>
              <Pick value={c.node} opts={graphNodes.map(n => [n.id, (n.data as any)?.label || n.id])} label={t('tests.node')} placeholder={t('tests.node')} testid="check-node" onChange={v => setCheck(i, { ...c, node: v })} />
              <Pick value={c.ran ? 'ran' : 'not_ran'} opts={['ran', 'not_ran'].map(r => [r, t(`tests.ran.${r}`)])} label={t('tests.kinds.node')} onChange={v => setCheck(i, { ...c, ran: v === 'ran' })} /></>}
            {(c.kind === 'duration' || c.kind === 'cost') && <Input type="number" min={0} step="any" className="w-28 text-xs" aria-label={t(`tests.kinds.${c.kind}`)}
              value={c.max ?? ''} onChange={e => setCheck(i, { ...c, max: Number(e.target.value) })} />}
            {(c.kind === 'duration' || c.kind === 'cost') && <span className="text-xs text-muted-foreground">{t(`tests.unit.${c.kind}`)}</span>}
            {isStale(c, graphNodes.map(n => n.id), fieldNames) && <span className="text-xs text-warning" data-testid="check-stale">{t('tests.stale')}</span>}
            <Button size="icon" variant="ghost" className="ml-auto" aria-label={t('common.delete')} disabled={checks.length < 2} onClick={() => setChecks(cs => cs.filter((_, j) => j !== i))}><X /></Button>
          </div>)}
          <Button size="sm" variant="outline" data-testid="check-add" onClick={() => setChecks(cs => [...cs, blank('field')])}><Plus />{t('tests.addCheck')}</Button>
        </div>
        {err && <Alert variant="destructive"><AlertDescription data-testid="test-dialog-error">{err}</AlertDescription></Alert>}
      </div>
      <DialogFooter className="shrink-0"><Button variant="outline" onClick={onClose}>{t('common.cancel')}</Button>
        <Button id="test-save" onClick={save} disabled={busy || !name.trim()}>{busy && <Loader2 className="animate-spin" />}{t('common.save')}</Button></DialogFooter>
    </DialogContent>
  </Dialog>
}

function Pick({ value, opts, label, placeholder, testid, onChange }: { value?: string; opts: string[][]; label: string; placeholder?: string; testid?: string; onChange: (v: string) => void }) {
  return <Select value={value || ''} onValueChange={onChange}>
    <SelectTrigger className="w-36" aria-label={label} data-testid={testid}><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent>{opts.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent></Select>
}
