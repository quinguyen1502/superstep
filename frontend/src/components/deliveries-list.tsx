import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Send } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api } from '@/lib/api'
import i18n from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'

type Delivery = { id: string; run_id: string; url: string; status: 'pending' | 'retrying' | 'ok' | 'failed'; attempts: number
  response_code: number | null; latency_ms: number | null; last_error: string | null; next_attempt: number | null; created: number }
const VARIANT = { ok: 'success', failed: 'destructive', retrying: 'warning', pending: 'secondary' } as const
const when = (s: number) => new Date(s * 1000).toLocaleString(i18n.resolvedLanguage)

/** Result-webhook delivery log with redelivery (TASK-0020). */
export function DeliveriesList({ wid, refreshKey = 0 }: { wid?: string; refreshKey?: number }) {
  const { t } = useTranslation(); const [items, setItems] = useState<Delivery[]>([]); const [err, setErr] = useState('')
  const load = () => { setErr(''); if (wid) api<Delivery[]>(`/api/workflows/${wid}/deliveries`).then(setItems).catch(e => setErr(e.message)) }
  useLoadWhen(true, load, `${wid}:${refreshKey}`)
  const redeliver = async (id: string) => {
    try { await api(`/api/workflows/${wid}/deliveries/${id}/redeliver`, { method: 'POST' }); load() } catch (e: any) { setErr(e.message) }
  }
  return <div className="space-y-2">
    {err && <p role="alert" className="text-xs text-destructive">{err}</p>}
    {!items.length && <p className="text-xs text-muted-foreground">{t('deliveries.empty')}</p>}
    <ScrollArea className="max-h-72"><div className="space-y-1.5 pr-2">{items.map(d => <div key={d.id} data-testid="delivery-row" className="rounded-md border px-3 py-2 text-xs space-y-1">
      <div className="flex items-center gap-2">
        <Badge variant={VARIANT[d.status]} data-testid="delivery-status">{t(`deliveries.status.${d.status}`)}</Badge>
        <span className="font-mono truncate">{d.url}</span>
        <span className="ml-auto text-muted-foreground">{when(d.created)}</span>
        <Button size="xs" variant="outline" data-testid="delivery-redeliver" disabled={d.status === 'pending'} onClick={() => redeliver(d.id)}><Send />{t('deliveries.redeliver')}</Button>
      </div>
      <div className="flex gap-3 text-muted-foreground tabular-nums">
        <span>{t('deliveries.attempts', { count: d.attempts })}</span>
        {d.response_code != null && <span data-testid="delivery-code">HTTP {d.response_code}</span>}
        {d.latency_ms != null && <span>{Math.round(d.latency_ms)} ms</span>}
        <span className="font-mono">run {d.run_id}</span>
        {d.next_attempt && <span>{t('deliveries.next', { when: when(d.next_attempt) })}</span>}
        {d.last_error && <span className="text-destructive truncate">{d.last_error}</span>}
      </div>
    </div>)}</div></ScrollArea>
  </div>
}
