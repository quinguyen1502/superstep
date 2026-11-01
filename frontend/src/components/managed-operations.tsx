import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RefreshCw, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { can, useMe } from '@/lib/rbac'

type Operation = { operation_id: string; key: string; tool: string; outcome: 'pending' | 'confirmed' | 'failed' | 'unknown'; created: number }
export function ManagedOperations({ serverId }: { serverId: string }) {
  const manages = can(useMe(), 'resources.manage')
  const { t } = useTranslation(); const [items, setItems] = useState<Operation[]>([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const load = useCallback(() => { setError(''); return api<Operation[]>(`/api/mcp/servers/${serverId}/operations`).then(setItems).catch(e => setError(e.message)) }, [serverId])
  useEffect(() => { load() }, [load])
  const reconcile = async (id: string) => {
    setError(''); setBusy(true)
    try { await api(`/api/mcp/servers/${serverId}/operations/${id}/reconcile`, { method: 'POST' }); await load() }
    catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="space-y-2" data-testid="managed-operations">
    <div className="flex items-center justify-between gap-2"><span className="text-sm font-medium">{t('managedTools.operations')}</span>
      <Button size="sm" variant="outline" disabled={busy} onClick={load}><RefreshCw />{t('managedTools.refresh')}</Button></div>
    {error && <Alert variant="warning"><TriangleAlert /><AlertDescription>{error}</AlertDescription></Alert>}
    {!items.length && <p className="text-xs text-muted-foreground">{t('managedTools.noOperations')}</p>}
    {items.map(item => <div key={item.operation_id} className="space-y-2 rounded-md border p-3" data-testid="managed-operation" data-outcome={item.outcome}>
      <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs">{item.tool}</span>
        <Badge variant="outline">{t(`managedTools.outcomes.${item.outcome}`)}</Badge><span className="text-xs text-muted-foreground">{fmtDate(item.created)}</span></div>
      <div className="text-xs text-muted-foreground">{t('managedTools.operationKey')}<code className="block break-all">{item.key}</code></div>
      {(item.outcome === 'pending' || item.outcome === 'unknown') && <>
        <p className="text-xs text-muted-foreground">{t('managedTools.unknownHelp')}</p>
        {manages && <Button size="sm" variant="outline" disabled={busy} onClick={() => reconcile(item.operation_id)}>{t('managedTools.reconcile')}</Button>}
      </>}
    </div>)}
  </div>
}
