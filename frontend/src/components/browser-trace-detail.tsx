import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { JsonView } from './json-view'
import { api } from '@/lib/api'
import { browserStatus, type BrowserDetail } from '@/lib/browser-trace'

function ProtectedCapture({ id }: { id: string }) {
  const { t } = useTranslation(), [url, setUrl] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])
  const load = async () => { setBusy(true); setError(''); try { const blob = await api<Blob>(`/api/browser/artifacts/${encodeURIComponent(id)}`, { response: 'blob' }); setUrl(URL.createObjectURL(blob)) } catch (error: any) { setError(error.message) } finally { setBusy(false) } }
  return <div className="space-y-2" data-testid="browser-capture"><p className="text-xs text-muted-foreground">{t('browserTools.captureHelp')}</p>
    {url ? <img src={url} alt={t('browserTools.captureAlt')} className="max-w-full rounded-md border" /> : <Button variant="outline" size="sm" onClick={load} disabled={busy}>{t(busy ? 'common.loading' : 'browserTools.loadCapture')}</Button>}
    {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
  </div>
}

export function BrowserTraceDetail({ value }: { value: BrowserDetail }) {
  const { t } = useTranslation(), status = browserStatus(value.status)
  const approvals: Record<string, string> = { approved: 'trace.agent.approved', rejected: 'trace.agent.status.rejected', expired: 'chat.browser.status.expired', stale: 'chat.browser.status.stale_observation' }
  return <div className="space-y-3" data-testid="browser-trace-detail">
    <div className="flex flex-wrap items-center gap-2"><Badge variant="outline">{value.operation}</Badge>
      {status && <Badge variant={status === 'confirmed' ? 'success' : ['approval_required', 'challenge_required', 'expired', 'session_lost', 'stale_observation', 'policy_denied', 'missing_input'].includes(status) ? 'warning' : status === 'unknown' || status === 'failed_before_effect' ? 'destructive' : 'secondary'}>{t(`chat.browser.status.${status}`)}</Badge>}
      {value.approval && approvals[value.approval] && <Badge variant="outline">{t(approvals[value.approval])}</Badge>}
    </div>
    {status && !['confirmed', 'dry_run'].includes(status) && <Alert variant={status === 'unknown' ? 'destructive' : 'warning'}><ShieldAlert /><AlertDescription>{t(`chat.browser.help.${status}`)}</AlertDescription></Alert>}
    {value.sequence !== undefined && <p className="text-xs text-muted-foreground">{t('browserTools.sequence', { sequence: value.sequence, generation: value.generation ?? '—' })}</p>}
    {value.observation && <div className="space-y-2"><p className="text-xs font-medium wrap-anywhere">{value.observation.origin}</p>
      <p className="text-xs text-muted-foreground">{t('browserTools.pageGeneration', { generation: value.observation.page_generation ?? '—' })}</p>
      <p className="text-xs text-muted-foreground">{t('browserTools.untrustedObservation')}</p>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap wrap-anywhere rounded-md border bg-muted/30 p-3 text-xs">{value.observation.text}</pre>
      <JsonView value={value.observation.elements} /></div>}
    {value.extracted && <JsonView value={value.extracted} />}
    {value.artifact_id && <ProtectedCapture key={value.artifact_id} id={value.artifact_id} />}
  </div>
}
