/** Settings → Usage: runs, tokens and estimated cost over a window, top workflows and product health (users.manage).
 *  Server, database and queue health live in Grafana; this page links to it when the server reports a URL. */
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { UsageBudgetsCard } from './UsageBudgetsCard'
import { UsageQualityCard } from './UsageQualityCard'
import { AlertCircle, ExternalLink, RotateCw } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { HandbookLink } from '@/components/handbook-link'
import { api } from '@/lib/api'
import { can, useMe } from '@/lib/rbac'
import { bucketTotal, fmtAge, fmtCount, fmtShare, fmtUsd, MODEL_SORTS, SERIES_STATUSES, sortModels, USAGE_WINDOWS, type ModelSort,
  type SeriesStatus, type UsageHealth, type UsageSort, type UsageSummary, type UsageWindow } from '@/lib/usage'

const BAR: Record<SeriesStatus, string> = { ok: 'bg-success', error: 'bg-destructive', timeout: 'bg-warning', cancelled: 'bg-muted-foreground/50', other: 'bg-info' }

function Stat({ id, label, value, hint }: { id: string; label: string; value: string; hint?: React.ReactNode }) {
  return <Card id={id}><CardContent className="space-y-1">
    <div className="text-sm text-muted-foreground">{label}</div>
    <div className="text-2xl font-semibold tabular-nums" id={`${id}-value`}>{value}</div>
    {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
  </CardContent></Card>
}

export function UsageSection() {
  const { t, i18n } = useTranslation(); const me = useMe(); const lang = i18n.resolvedLanguage
  const [win, setWin] = useState<UsageWindow>('7d'); const [sort, setSort] = useState<UsageSort>('runs')
  const [data, setData] = useState<UsageSummary | null>(null); const [health, setHealth] = useState<UsageHealth | null>(null)
  const [err, setErr] = useState(''); const [tick, setTick] = useState(0); const [modelSort, setModelSort] = useState<ModelSort>('cost')
  const allowed = can(me, 'users.manage')
  const load = useCallback(() => setTick(n => n + 1), [])
  useEffect(() => {
    if (!allowed) return
    let live = true; setData(null); setHealth(null); setErr('')
    Promise.all([api<UsageSummary>(`/api/admin/usage?window=${win}&sort=${sort}`), api<UsageHealth>(`/api/admin/usage/health?window=${win}`)])
      .then(([d, h]) => { if (live) { setData(d); setHealth(h) } }).catch(e => { if (live) setErr(e.message) })
    return () => { live = false }
  }, [allowed, win, sort, tick])
  if (me && !allowed) return <Alert variant="warning"><AlertCircle /><AlertDescription>{t('users.adminOnly')}</AlertDescription></Alert>
  const tot = data?.totals; const unpriced = (tot?.unpriced_runs ?? 0) > 0
  const peak = Math.max(1, ...(data?.series ?? []).map(bucketTotal))
  const when = (ts: number) => new Date(ts * 1000).toLocaleString(lang, data?.bucket === 'hour' ? { hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric' })
  const age = (s: number | null) => { const a = fmtAge(s); return a ? t(`settings.usage.age.${a.unit}`, { n: a.n }) : '—' }
  const day = (ts: number) => new Date(ts * 1000).toLocaleDateString(lang, { year: 'numeric', month: 'short', day: 'numeric' })
  const models = sortModels(data?.models ?? [], modelSort)
  const people = [...(data?.users ?? []), ...(data?.teams ?? [])]; const peopleUnpriced = people.some(r => r.unpriced_runs > 0)
  const usd = (v: number, unpriced: boolean) => unpriced ? t('settings.usage.atLeast', { value: fmtUsd(v, lang) }) : fmtUsd(v, lang)
  return <div className="space-y-4" id="usage-page">
    <div className="flex h-11 items-center gap-2">
      <Select value={win} onValueChange={v => setWin(v as UsageWindow)}>
        <SelectTrigger id="usage-window" aria-label={t('settings.usage.window')}><SelectValue /></SelectTrigger>
        <SelectContent>{USAGE_WINDOWS.map(w => <SelectItem key={w} value={w}>{t(`settings.usage.windows.${w}`)}</SelectItem>)}</SelectContent>
      </Select>
      <span className="text-sm text-muted-foreground">{t('settings.usage.estimate')}</span>
    </div>
    {err && <Alert variant="destructive" id="usage-error"><AlertCircle /><AlertDescription className="flex items-center gap-2">
      <span>{err}</span><Button variant="outline" size="sm" onClick={load} id="usage-retry"><RotateCw />{t('common.retry')}</Button></AlertDescription></Alert>}
    {!data && !err && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true"><span className="sr-only">{t('common.loading')}</span>
      {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>}
    {data && tot && <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat id="usage-runs" label={t('settings.usage.runs')} value={fmtCount(tot.runs, lang)} />
        <Stat id="usage-success" label={t('settings.usage.successRate')} value={fmtShare(tot.success_rate, lang)} />
        <Stat id="usage-tokens" label={t('settings.usage.tokens')} value={`${fmtCount(tot.tokens_in, lang)} / ${fmtCount(tot.tokens_out, lang)}`}
          hint={t('settings.usage.tokensHint')} />
        <Stat id="usage-cost" label={t('settings.usage.cost')} value={unpriced ? t('settings.usage.atLeast', { value: fmtUsd(tot.cost_usd, lang) }) : fmtUsd(tot.cost_usd, lang)} />
        <Stat id="usage-unpriced" label={t('settings.usage.unpriced')} value={`${fmtCount(tot.unpriced_runs, lang)} (${fmtShare(tot.unpriced_share ?? 0, lang)})`}
          hint={unpriced ? <HandbookLink id="usage-prices-help" page="reference/configuration" label={t('settings.usage.unpricedHelp')} /> : undefined} />
      </div>
      {data.slo && <Card id="usage-slo">
        <CardHeader>
          <CardTitle>{t('settings.usage.slo.title')}</CardTitle>
          <CardDescription>{t('settings.usage.slo.window')}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <div className="font-medium">{t('settings.usage.slo.runs')}</div>
            <div className="text-sm text-muted-foreground">{t('settings.usage.slo.target', { value: fmtShare(data.slo.run_target, lang) })}</div>
            {data.slo.run_observed === null
              ? <div className="text-sm text-muted-foreground">{t('settings.usage.slo.empty')}</div>
              : <>
                <div className="text-sm">{t('settings.usage.slo.observed', { value: fmtShare(data.slo.run_observed, lang), count: data.slo.run_samples })}</div>
                <div className="text-sm">{t('settings.usage.slo.budget', { value: fmtShare(data.slo.run_budget_remaining, lang) })}</div>
              </>}
          </div>
          <div className="space-y-1">
            <div className="font-medium">{t('settings.usage.slo.api')}</div>
            <div className="text-sm text-muted-foreground">{t('settings.usage.slo.target', { value: fmtShare(data.slo.api_target, lang) })}</div>
            {data.grafana_url && <a href={data.grafana_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm underline underline-offset-4">
              <ExternalLink className="size-3" aria-hidden="true" />{t('settings.usage.slo.viewGrafana')}
            </a>}
          </div>
        </CardContent>
      </Card>}
      <Card id="usage-series"><CardHeader><CardTitle>{t('settings.usage.overTime')}</CardTitle>
        <CardDescription className="flex flex-wrap gap-3">{SERIES_STATUSES.map(s => <span key={s} className="inline-flex items-center gap-1.5">
          <span className={`inline-block size-2.5 rounded-sm ${BAR[s]}`} aria-hidden="true" />{t(`settings.usage.status.${s}`)}</span>)}</CardDescription></CardHeader>
        <CardContent>
          {tot.runs === 0 ? <p className="py-6 text-center text-sm text-muted-foreground" id="usage-empty">{t('settings.usage.empty')}</p> :
            <div className="relative h-40" role="img" aria-label={t('settings.usage.overTime')}>
              <div className="pointer-events-none absolute inset-0 flex flex-col justify-between" aria-hidden="true">
                {Array.from({ length: 5 }, (_, i) => <div key={i} className="border-t border-border" />)}
              </div>
              <div className="relative flex h-full items-end gap-0.5">
              {data.series.map(b => { const n = bucketTotal(b)
                return <div key={b.start} className="flex h-full min-w-0 flex-1 flex-col justify-end" title={`${when(b.start)}: ${fmtCount(n, lang)}`} data-testid="usage-bar">
                  {SERIES_STATUSES.filter(s => b[s] > 0).map(s => <div key={s} className={BAR[s]} style={{ height: `${(b[s] / peak) * 100}%` }} />)}
                </div> })}
              </div>
            </div>}
          {tot.runs > 0 && <div className="mt-2 flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>{when(data.since)}</span><span>{when(data.until)}</span></div>}
        </CardContent></Card>
      <Card id="usage-workflows" className="gap-0 overflow-hidden pb-0"><CardHeader className="flex items-center gap-2 pb-4">
        <CardTitle>{t('settings.usage.topWorkflows')}</CardTitle>
        <Select value={sort} onValueChange={v => setSort(v as UsageSort)}>
          <SelectTrigger id="usage-sort" className="ml-auto" aria-label={t('settings.usage.sortBy')}><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="runs">{t('settings.usage.sort.runs')}</SelectItem><SelectItem value="cost">{t('settings.usage.sort.cost')}</SelectItem></SelectContent>
        </Select></CardHeader>
        <Table id="usage-workflows-table"><TableHeader><TableRow>
          <TableHead className="pl-6">{t('settings.usage.col.workflow')}</TableHead><TableHead className="text-right">{t('settings.usage.col.runs')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.col.errorRate')}</TableHead><TableHead className="text-right">{t('settings.usage.col.tokens')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.col.cost')}</TableHead><TableHead className="pr-6 text-right">{t('settings.usage.col.unpriced')}</TableHead>
        </TableRow></TableHeader>
          <TableBody>
            {data.top_workflows.map(w => <TableRow key={w.workflow_id ?? 'none'} data-testid="usage-workflow-row">
              <TableCell className="max-w-64 truncate pl-6 font-medium">{w.name ?? <span className="font-mono text-muted-foreground">{w.workflow_id ?? '—'}</span>}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtCount(w.runs, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtShare(w.error_rate, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtCount(w.tokens_in + w.tokens_out, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtUsd(w.cost_usd, lang)}</TableCell>
              <TableCell className="pr-6 text-right tabular-nums">{fmtCount(w.unpriced_runs, lang)}</TableCell>
            </TableRow>)}
            {!data.top_workflows.length && <TableRow><TableCell /* ui-class-ok: empty table row spacing, layout not control sizing */ colSpan={6} className="py-8 text-center text-muted-foreground">{t('settings.usage.empty')}</TableCell></TableRow>}
          </TableBody></Table></Card>
      <Card id="usage-models" className="gap-0 overflow-hidden pb-0"><CardHeader className="flex items-center gap-2 pb-4">
        <div className="space-y-1.5"><CardTitle>{t('settings.usage.models.title')}</CardTitle>
          <CardDescription id="usage-models-since">{data.models_since ? t('settings.usage.models.since', { date: day(data.models_since) }) : t('settings.usage.models.notYet')}</CardDescription></div>
        <Select value={modelSort} onValueChange={v => setModelSort(v as ModelSort)}>
          <SelectTrigger id="usage-models-sort" className="ml-auto" aria-label={t('settings.usage.models.sortBy')}><SelectValue /></SelectTrigger>
          <SelectContent>{MODEL_SORTS.map(s => <SelectItem key={s} value={s}>{t(`settings.usage.models.sort.${s}`)}</SelectItem>)}</SelectContent>
        </Select></CardHeader>
        <Table id="usage-models-table"><TableHeader><TableRow>
          <TableHead className="pl-6">{t('settings.usage.models.col.model')}</TableHead><TableHead>{t('settings.usage.models.col.kind')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.models.col.calls')}</TableHead><TableHead className="text-right">{t('settings.usage.models.col.errors')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.col.tokens')}</TableHead><TableHead className="text-right">{t('settings.usage.models.col.latency')}</TableHead>
          <TableHead className="pr-6 text-right">{t('settings.usage.col.cost')}</TableHead>
        </TableRow></TableHeader>
          <TableBody>
            {models.map(m => <TableRow key={`${m.kind}:${m.provider}:${m.model}`} data-testid="usage-model-row">
              <TableCell className="max-w-64 truncate pl-6"><span className="font-medium">{m.model}</span> <span className="text-muted-foreground">{m.provider}</span></TableCell>
              <TableCell>{t(`settings.usage.models.kind.${m.kind}`)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtCount(m.calls, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtCount(m.errors, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtCount(m.tokens_in + m.tokens_out, lang)}</TableCell>
              <TableCell className="text-right tabular-nums">{m.avg_duration_ms === null ? '—' : t('settings.usage.models.ms', { n: fmtCount(Math.round(m.avg_duration_ms), lang) })}</TableCell>
              <TableCell className="pr-6 text-right tabular-nums">{m.unpriced_rows > 0 && m.cost_usd === 0 ? t('settings.usage.models.unpriced') : usd(m.cost_usd, m.unpriced_rows > 0)}</TableCell>
            </TableRow>)}
            {!models.length && <TableRow><TableCell /* ui-class-ok: empty table row spacing, layout not control sizing */ colSpan={7} className="py-8 text-center text-muted-foreground" id="usage-models-empty">{t('settings.usage.models.empty')}</TableCell></TableRow>}
          </TableBody></Table></Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card id="usage-users" className="gap-0 overflow-hidden pb-0"><CardHeader className="pb-4"><CardTitle>{t('settings.usage.people.users')}</CardTitle>
          <CardDescription>{t('settings.usage.people.sortedBy', { by: t(`settings.usage.sort.${sort}`) })}</CardDescription></CardHeader>
          <Table id="usage-users-table"><TableHeader><TableRow>
            <TableHead className="pl-6">{t('settings.usage.people.user')}</TableHead><TableHead className="text-right">{t('settings.usage.col.runs')}</TableHead>
            <TableHead className="text-right">{t('settings.usage.col.tokens')}</TableHead><TableHead className="pr-6 text-right">{t('settings.usage.col.cost')}</TableHead>
          </TableRow></TableHeader>
            <TableBody>
              {data.users.map(u => <TableRow key={u.user_id ?? 'none'} data-testid="usage-user-row">
                <TableCell className="max-w-56 truncate pl-6 font-medium">{u.deleted || !u.email ? <span className="text-muted-foreground">{t('settings.usage.people.deleted')}</span> : u.email}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtCount(u.runs, lang)}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtCount(u.tokens_in + u.tokens_out, lang)}</TableCell>
                <TableCell className="pr-6 text-right tabular-nums">{usd(u.cost_usd, u.unpriced_runs > 0)}</TableCell>
              </TableRow>)}
              {data.users.length > 0 && <TableRow className="font-medium" data-testid="usage-users-total">
                <TableCell className="pl-6">{t('settings.usage.people.total')}</TableCell><TableCell className="text-right tabular-nums">{fmtCount(tot.runs, lang)}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtCount(tot.tokens_in + tot.tokens_out, lang)}</TableCell>
                <TableCell className="pr-6 text-right tabular-nums">{usd(tot.cost_usd, unpriced || peopleUnpriced)}</TableCell></TableRow>}
              {!data.users.length && <TableRow><TableCell /* ui-class-ok: empty table row spacing, layout not control sizing */ colSpan={4} className="py-8 text-center text-muted-foreground">{t('settings.usage.empty')}</TableCell></TableRow>}
            </TableBody></Table></Card>
        <Card id="usage-teams" className="gap-0 overflow-hidden pb-0"><CardHeader className="pb-4"><CardTitle>{t('settings.usage.people.teams')}</CardTitle>
          <CardDescription id="usage-teams-note">{data.teams_shared_members > 0 ? t('settings.usage.people.shared', { count: data.teams_shared_members }) : t('settings.usage.people.teamsNote')}</CardDescription></CardHeader>
          <Table id="usage-teams-table"><TableHeader><TableRow>
            <TableHead className="pl-6">{t('settings.usage.people.team')}</TableHead><TableHead className="text-right">{t('settings.usage.people.members')}</TableHead>
            <TableHead className="text-right">{t('settings.usage.col.runs')}</TableHead><TableHead className="pr-6 text-right">{t('settings.usage.col.cost')}</TableHead>
          </TableRow></TableHeader>
            <TableBody>
              {data.teams.map(tm => <TableRow key={tm.team_id} data-testid="usage-team-row">
                <TableCell className="max-w-56 truncate pl-6 font-medium">{tm.name ?? <span className="font-mono text-muted-foreground">{tm.team_id}</span>}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtCount(tm.members, lang)}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtCount(tm.runs, lang)}</TableCell>
                <TableCell className="pr-6 text-right tabular-nums">{usd(tm.cost_usd, tm.unpriced_runs > 0)}</TableCell>
              </TableRow>)}
              {!data.teams.length && <TableRow><TableCell /* ui-class-ok: empty table row spacing, layout not control sizing */ colSpan={4} className="py-8 text-center text-muted-foreground">{t('settings.usage.people.noTeams')}</TableCell></TableRow>}
            </TableBody></Table></Card>
      </div>
      <UsageBudgetsCard />
      {health && <Card id="usage-health"><CardHeader><CardTitle>{t('settings.usage.health.title')}</CardTitle>
        <CardDescription>{t('settings.usage.health.intro')}</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
            <div id="usage-health-approvals"><div className="font-medium">{t('settings.usage.health.approvals')}</div>
              <div className="text-muted-foreground">{health.approvals.oldest_age_s === null ? t('settings.usage.health.waitingNone', { n: health.approvals.waiting })
                : t('settings.usage.health.waiting', { n: health.approvals.waiting, age: age(health.approvals.oldest_age_s) })}</div>
              <div className="text-muted-foreground">{t('settings.usage.health.expired', { n: health.approvals.expired })}</div></div>
            <div id="usage-health-webhooks"><div className="font-medium">{t('settings.usage.health.webhooks')}</div>
              <div className="text-muted-foreground">{t('settings.usage.health.failed', { n: health.webhooks.failed })}</div>
              <div className="text-muted-foreground">{t('settings.usage.health.retrying', { n: health.webhooks.retrying })}</div></div>
            <div id="usage-health-schedules"><div className="font-medium">{t('settings.usage.health.schedules')}</div>
              <div className="text-muted-foreground">{t('settings.usage.health.overdue', { n: health.schedules.overdue })}</div>
              <div className="text-muted-foreground">{t('settings.usage.health.disabled', { n: health.schedules.disabled })}</div></div>
          </div>
          <div id="usage-health-channels" className="space-y-2 text-sm">
            <div className="font-medium">{t('settings.usage.health.channels')}</div>
            <div className="text-muted-foreground">{t('settings.usage.health.refused', { n: health.channels.refused_total, share: fmtShare(health.channels.refusal_share, lang) })}</div>
            {health.channels.refused.length > 0 && <Table id="usage-refusals-table"><TableHeader><TableRow>
              <TableHead>{t('settings.usage.health.reason')}</TableHead><TableHead>{t('settings.usage.health.platform')}</TableHead>
              <TableHead className="text-right">{t('settings.usage.health.count')}</TableHead></TableRow></TableHeader>
              <TableBody>{health.channels.refused.map(r => <TableRow key={`${r.code}:${r.kind}`} data-testid="usage-refusal-row">
                <TableCell><span className="font-mono text-xs text-muted-foreground">{r.code}</span> {t(`errors.${r.code}`, { kind: r.kind, defaultValue: '' })}</TableCell>
                <TableCell>{r.kind}</TableCell><TableCell className="text-right tabular-nums">{fmtCount(r.count, lang)}</TableCell>
              </TableRow>)}</TableBody></Table>}
          </div>
          {health.schedules.disabled_list.length > 0 && <Alert variant="warning" id="usage-health-stopped"><AlertCircle /><AlertDescription>
            <ul className="space-y-1">{health.schedules.disabled_list.map(s => <li key={s.id}><span className="font-medium">{s.name}</span>{s.note ? `: ${s.note}` : ''}</li>)}</ul>
          </AlertDescription></Alert>}
        </CardContent></Card>}
      {health?.quality && <UsageQualityCard quality={health.quality} />}
      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
        <HandbookLink id="usage-handbook" page="operate/observability" label={t('settings.usage.handbook')} />
        {data.grafana_url && <a id="usage-grafana" href={data.grafana_url} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground"><ExternalLink className="size-3" aria-hidden="true" />{t('settings.usage.grafana')}</a>}
      </div>
    </>}
  </div>
}
