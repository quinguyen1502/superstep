/** Transfer ownership: preview the references the new owner cannot use, re-bind them to the new owner's own
 *  credentials / knowledge bases / MCP servers, or leave them flagged; then transfer. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, ArrowRightLeft, CircleCheck, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import type { Issue, TransferPreview } from '@/lib/rbac'

const KEEP = '__keep'

export function TransferDialog({ workflowId, onDone }: { workflowId: string; onDone: (owner: string, flagged: Issue[]) => void }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false); const [email, setEmail] = useState(''); const [p, setP] = useState<TransferPreview | null>(null)
  const [rebind, setRebind] = useState<Record<string, string>>({}); const [keep, setKeep] = useState(true)
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const reset = (o: boolean) => { setOpen(o); if (!o) { setP(null); setEmail(''); setRebind({}); setErr('') } }
  const preview = async () => {
    setBusy(true); setErr('')
    try { setP(await api<TransferPreview>(`/api/workflows/${workflowId}/transfer?email=${encodeURIComponent(email.trim())}`)); setRebind({}) }
    catch (e: any) { setErr(e.message); setP(null) } finally { setBusy(false) }
  }
  const submit = async () => {
    setBusy(true); setErr('')
    const map = Object.fromEntries(Object.entries(rebind).filter(([, v]) => v && v !== KEEP))
    try { const r = await api<{ owner_email: string; flagged: Issue[] }>(`/api/workflows/${workflowId}/transfer`, { method: 'POST', json: { email: email.trim(), rebind: map, keep_access: keep } }); reset(false); onDone(r.owner_email, r.flagged) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return <Dialog open={open} onOpenChange={reset}>
    <DialogTrigger asChild><Button variant="outline" size="sm" id="transfer-btn"><ArrowRightLeft />{t('transfer.button')}</Button></DialogTrigger>
    <DialogContent className="flex max-h-[85dvh] flex-col overflow-hidden sm:max-w-xl">
      <DialogHeader><DialogTitle>{t('transfer.title')}</DialogTitle><DialogDescription>{t('transfer.intro')}</DialogDescription></DialogHeader>
      <DialogBody className="space-y-4">
      <div className="flex items-end gap-2"><div className="flex-1 space-y-1.5"><Label htmlFor="transfer-email">{t('transfer.newOwner')}</Label>
        <Input id="transfer-email" type="email" placeholder="name@example.com" value={email} onChange={e => { setEmail(e.target.value); setP(null) }} onKeyDown={e => e.key === 'Enter' && email.trim() && preview()} /></div>
        <Button variant="outline" id="transfer-check" onClick={preview} disabled={!email.trim() || busy}>{busy && !p ? <Loader2 className="animate-spin" /> : null}{t('transfer.check')}</Button></div>
      {p && (p.issues.length ? <div className="space-y-2" id="transfer-issues">
        <Alert variant="warning" id="transfer-warning"><AlertTriangle /><AlertDescription>{t('transfer.issues', { count: p.issues.length })}</AlertDescription></Alert>
        {p.issues.map(i => <div key={i.node_id + i.field} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm transfer-issue">
          <div className="min-w-0 flex-1"><div className="truncate font-medium">{i.node}</div>
            <div className="text-xs text-muted-foreground">{t(`transfer.kinds.${i.kind}`)}: {i.name ?? i.id}</div></div>
          {i.rebindable && (p.options[i.kind] || []).length ? <Select value={rebind[i.node_id] || KEEP} onValueChange={v => setRebind(r => ({ ...r, [i.node_id]: v }))}>
            <SelectTrigger size="sm" className="w-52" aria-label={t('transfer.rebindFor', { node: i.node })}><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value={KEEP}>{t('transfer.keepFlagged')}</SelectItem>
              {(p.options[i.kind] || []).map(o => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent></Select>
            : <Badge variant="secondary">{t('transfer.flagged')}</Badge>}
        </div>)}</div>
        : <Alert id="transfer-clean"><CircleCheck /><AlertDescription>{t('transfer.clean', { email: p.new_owner })}</AlertDescription></Alert>)}
      {p && <div className="flex items-center gap-2"><Switch id="transfer-keep" checked={keep} onCheckedChange={setKeep} /><Label htmlFor="transfer-keep" className="font-normal">{t('transfer.keepAccess')}</Label></div>}
      {err && <p role="alert" className="text-sm text-destructive" id="transfer-error">{err}</p>}
      </DialogBody>
      <DialogFooter><Button variant="outline" onClick={() => reset(false)}>{t('common.cancel')}</Button>
        <Button id="transfer-submit" onClick={submit} disabled={!p || busy}>{busy && p ? <Loader2 className="animate-spin" /> : <ArrowRightLeft />}{t('transfer.submit')}</Button></DialogFooter>
    </DialogContent>
  </Dialog>
}
