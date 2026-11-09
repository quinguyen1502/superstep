/** Settings → Activity: audit log of roles, shares, teams, ownership, accounts and policy, with filters. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { FilterBar } from '@/components/settings/filter-bar'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { can, useMe, type AuditItem, type AuditPage } from '@/lib/rbac'
import { useOnChange } from '@/lib/use-when'

const LIMIT = 25
const CATS = ['user', 'share', 'team', 'workflow', 'policy']

function detailText(e: AuditItem): string {
  return Object.entries(e.details).filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`).join(' · ')
}

export function ActivitySection() {
  const { t } = useTranslation(); const me = useMe()
  const [q, setQ] = useState(''); const [cat, setCat] = useState('all'); const [since, setSince] = useState('all'); const [offset, setOffset] = useState(0)
  const [data, setData] = useState<AuditPage | null>(null); const [err, setErr] = useState('')
  useOnChange(`${q}\n${cat}\n${since}`, () => setOffset(0))  // a new filter starts at the first page
  useEffect(() => {
    if (!can(me, 'users.manage')) return
    const p = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) })
    if (q.trim()) p.set('q', q.trim()); if (cat !== 'all') p.set('category', cat); if (since !== 'all') p.set('since', since)
    const id = setTimeout(() => api<AuditPage>(`/api/admin/audit?${p}`).then(d => { setData(d); setErr('') }).catch(e => setErr(e.message)), 200)
    return () => clearTimeout(id)
  }, [me, q, cat, since, offset])
  if (me && !can(me, 'users.manage')) return <Alert variant="warning"><AlertCircle /><AlertDescription>{t('users.adminOnly')}</AlertDescription></Alert>
  return <div className="space-y-4">
    <FilterBar id="activity-filters" q={q} onQ={setQ} placeholder={t('activity.search')} filters={[
      { id: 'category', label: t('activity.category'), value: cat, onChange: setCat, options: [{ value: 'all', label: t('activity.anyCategory') }, ...CATS.map(c => ({ value: c, label: t(`activity.cat.${c}`) }))] },
      { id: 'since', label: t('activity.since'), value: since, onChange: setSince, options: ['all', '24h', '7d', '30d'].map(s => ({ value: s, label: t(`activity.when.${s}`) })) },
    ]} />
    {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
    <Card className="overflow-hidden p-0"><Table id="activity-table">
      <TableHeader><TableRow><TableHead className="pl-4">{t('activity.when.col')}</TableHead><TableHead>{t('activity.actor')}</TableHead><TableHead>{t('activity.action')}</TableHead>
        <TableHead>{t('activity.target')}</TableHead><TableHead className="pr-4">{t('activity.details')}</TableHead></TableRow></TableHeader>
      <TableBody>
        {data?.items.map(e => <TableRow key={e.id} data-testid="activity-row">
          <TableCell className="pl-4 whitespace-nowrap text-muted-foreground">{fmtDate(e.at)}</TableCell>
          <TableCell className="max-w-48 truncate">{e.actor ?? '—'}</TableCell>
          <TableCell><Badge variant="outline">{t(`activity.actions.${e.action.replace('.', '_')}`, { defaultValue: e.action })}</Badge></TableCell>
          <TableCell className="max-w-56"><div className="truncate font-medium">{e.target ?? e.target_id}</div><div className="text-xs text-muted-foreground">{t(`activity.types.${e.target_type}`)}</div></TableCell>
          <TableCell className="pr-4 max-w-80 text-xs text-muted-foreground"><div className="line-clamp-2 break-words">{detailText(e)}</div></TableCell>
        </TableRow>)}
        {!data && !err && Array.from({ length: 6 }, (_, i) => <TableRow key={i} className="hover:bg-transparent" aria-busy={i === 0 || undefined}>
          <TableCell /* ui-class-ok: empty/loading table row spacing, layout not control sizing */ colSpan={5} className="py-2 pl-4">{i === 0 && <span className="sr-only">{t('common.loading')}</span>}<Skeleton className="h-4 w-full" /></TableCell>
        </TableRow>)}
        {data && !data.items.length && <TableRow><TableCell /* ui-class-ok: empty/loading table row spacing, layout not control sizing */ colSpan={5} className="py-10 text-center text-muted-foreground" id="activity-empty">{t('activity.empty')}</TableCell></TableRow>}
      </TableBody></Table></Card>
    {data && data.total > LIMIT && <div className="flex items-center justify-end gap-2 text-sm text-muted-foreground">
      {t('activity.range', { from: offset + 1, to: Math.min(offset + LIMIT, data.total), total: data.total })}
      <Button variant="outline" size="icon" aria-label={t('activity.prev')} disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - LIMIT))}><ChevronLeft /></Button>
      <Button variant="outline" size="icon" aria-label={t('activity.next')} disabled={offset + LIMIT >= data.total} onClick={() => setOffset(o => o + LIMIT)}><ChevronRight /></Button></div>}
  </div>
}
