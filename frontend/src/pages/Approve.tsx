/** /approve?token=… (TASK-0047): the page e-mail and Teams approval links open. The signed-in studio user sees the
 * request and confirms; a link alone never decides, so mail scanners that open links cannot approve anything. */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertCircle, CircleCheck, Loader2, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { AppMeta } from '@/components/app-meta'
import { fmtDate } from '@/lib/i18n'

type Info = { decision: 'approved' | 'rejected'; status: string; kind: string; workflow_id: string | null; workflow_name: string | null
  run_id: string; label: string | null; prompt: string | null; expires: number; expired: boolean; decided_by: string | null }

export function ApprovePage() {
  const { t } = useTranslation(); const token = useSearchParams()[0].get('token') || ''
  const [info, setInfo] = useState<Info | null>(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [done, setDone] = useState<string | null>(null)
  useEffect(() => { api<Info>(`/api/approvals/link?token=${encodeURIComponent(token)}`).then(setInfo).catch(e => setErr(e.message)) }, [token])
  const decide = async () => {
    setBusy(true); setErr('')
    try { const r = await api<{ decision: string }>('/api/approvals/link', { method: 'POST', json: { token } }); setDone(r.decision) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const runUrl = info?.workflow_id ? `/workflows/${info.workflow_id}?run=${info.run_id}` : null
  const expired = !!info?.expired  // decided by the server clock
  const rows: [string, string | null][] = info ? [[t('approve.workflow'), info.workflow_name], [t('approve.step'), info.label || info.run_id], [t('approve.question'), info.prompt], [t('approve.expires'), fmtDate(info.expires)]] : []
  return <div className="flex min-h-dvh flex-col bg-muted/40">
    <div className="flex flex-1 items-center justify-center p-4">
    <Card className="w-full max-w-md" id="approve-card">
      <CardHeader>
        <div className="mb-2 w-fit rounded-lg bg-primary p-2 text-primary-foreground"><ShieldCheck className="size-5" /></div>
        <CardTitle>{t('approve.title')}</CardTitle>
        {info && info.status === 'pending' && !done && !expired && <CardDescription>{t(info.decision === 'approved' ? 'approve.approveQ' : 'approve.rejectQ')}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-3">
        {err && <Alert variant="destructive" id="approve-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
        {!info && !err && <Loader2 className="size-5 animate-spin text-muted-foreground" />}
        {info && <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          {rows.filter(([, v]) => v).map(([k, v]) => <div key={k} className="contents"><dt className="text-muted-foreground">{k}</dt><dd className="whitespace-pre-wrap break-words">{v}</dd></div>)}
        </dl>}
        {done && <div id="approve-done" role="status" className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><CircleCheck className="size-4 shrink-0 text-success" />{t(`approve.done.${done}`)}</div>}
        {info && !done && info.status !== 'pending' && <p className="text-sm" id="approve-decided"><Badge variant="secondary" className="mr-2">{t(`approve.status.${info.status}`, info.status)}</Badge>
          {t('approve.decided', { by: info.decided_by ? t('approve.by', { who: info.decided_by }) : '' })}</p>}
        {expired && !done && <p className="text-sm text-muted-foreground">{t('approve.expired')}</p>}
      </CardContent>
      <CardFooter className="flex-wrap justify-end gap-2">
        {runUrl && <Button variant="outline" asChild><Link to={runUrl} id="approve-open-run">{t('approve.openRun')}</Link></Button>}
        {info && info.status === 'pending' && !done && !expired &&
          <Button id="approve-confirm" variant={info.decision === 'approved' ? 'default' : 'destructive'} disabled={busy} onClick={decide}>
            {busy && <Loader2 className="animate-spin" />}{t(info.decision === 'approved' ? 'approve.approve' : 'approve.reject')}</Button>}
      </CardFooter>
    </Card>
    </div>
    <AppMeta />
  </div>
}
