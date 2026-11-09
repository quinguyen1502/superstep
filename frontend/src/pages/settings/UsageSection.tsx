/** Settings → Usage: runs, tokens and estimated cost over a window, top workflows and product health (users.manage).
 *  Server, database and queue health live in Grafana; this page links to it when the server reports a URL. */
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
import { bucketTotal, fmtAge, fmtCount, fmtShare, fmtUsd, SERIES_STATUSES, USAGE_WINDOWS, type SeriesStatus, type UsageHealth,
  type UsageSort, type UsageSummary, type UsageWindow } from '@/lib/usage'

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
  const [err, setErr] = useState(''); const [tick, setTick] = useState(0)
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
      <Card id="usage-series"><CardHeader><CardTitle>{t('settings.usage.overTime')}</CardTitle>
        <CardDescription className="flex flex-wrap gap-3">{SERIES_STATUSES.map(s => <span key={s} className="inline-flex items-center gap-1.5">
          <span className={`inline-block size-2.5 rounded-sm ${BAR[s]}`} aria-hidden="true" />{t(`settings.usage.status.${s}`)}</span>)}</CardDescription></CardHeader>
        <CardContent>
          {tot.runs === 0 ? <p className="py-6 text-center text-sm text-muted-foreground" id="usage-empty">{t('settings.usage.empty')}</p> :
            <div className="flex h-40 items-end gap-0.5" role="img" aria-label={t('settings.usage.overTime')}>
              {data.series.map(b => { const n = bucketTotal(b)
                return <div key={b.start} className="flex h-full min-w-0 flex-1 flex-col justify-end" title={`${when(b.start)}: ${fmtCount(n, lang)}`} data-testid="usage-bar">
                  {SERIES_STATUSES.filter(s => b[s] > 0).map(s => <div key={s} className={BAR[s]} style={{ height: `${(b[s] / peak) * 100}%` }} />)}
                </div> })}
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
          {health.schedules.disabled_list.length > 0 && <Alert variant="warning" id="usage-health-stopped"><AlertCircle /><AlertDescription>
            <ul className="space-y-1">{health.schedules.disabled_list.map(s => <li key={s.id}><span className="font-medium">{s.name}</span>{s.note ? `: ${s.note}` : ''}</li>)}</ul>
          </AlertDescription></Alert>}
        </CardContent></Card>}
      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
        <HandbookLink id="usage-handbook" page="operate/observability" label={t('settings.usage.handbook')} />
        {data.grafana_url && <a id="usage-grafana" href={data.grafana_url} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground">{t('settings.usage.grafana')}<ExternalLink className="size-3" aria-hidden="true" /></a>}
      </div>
    </>}
  </div>
}
