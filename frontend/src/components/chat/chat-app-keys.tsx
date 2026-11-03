/** Server-only chat credentials: copy once, overlap two keys for rotation, type the label to revoke. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Copy, Plus, Trash2, TriangleAlert } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

type AppKey = { key_id: string; label: string; origins: string[]; created_at: number; revoked_at: number | null; last_used_at: number | null }

export function ChatAppKeys({ wid }: { wid: string }) {
  const { t } = useTranslation()
  const url = `/api/workflows/${wid}/chat/app-keys`
  const [keys, setKeys] = useState<AppKey[]>([]); const [ready, setReady] = useState(false)
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const [label, setLabel] = useState(''); const [origins, setOrigins] = useState('')
  const [created, setCreated] = useState<(AppKey & { secret: string }) | null>(null)
  const [copied, setCopied] = useState(false); const [revoking, setRevoking] = useState<AppKey | null>(null)
  const load = () => api<AppKey[]>(url).then(rows => { setKeys(rows); setReady(true) })
  useLoadWhen(true, () => { load().catch(e => {
    if (e instanceof ApiError && e.code === 'CHAT_TRIGGER_NOT_FOUND') setErr(t('chat.appKeys.saveFirst'))
    else setErr(e.message)
  }) }, wid)
  const active = keys.filter(k => !k.revoked_at).length
  const create = async () => {
    setBusy(true); setErr(''); setCopied(false)
    try {
      const key = await api<AppKey & { secret: string }>(url, { method: 'POST', json: { label, origins: origins.split('\n').map(s => s.trim()).filter(Boolean) } })
      setCreated(key); setLabel(''); setOrigins(''); await load()
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return <section id="chat-app-keys" className="grid gap-3 rounded-lg border p-3" aria-label={t('chat.appKeys.title')}>
    <Label>{t('chat.appKeys.title')}</Label><p className="text-xs text-muted-foreground">{t('chat.appKeys.hint')}</p>
    {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
    {keys.map(k => <div key={k.key_id} className="grid gap-1 rounded-md border p-2" data-testid="chat-app-key">
      <div className="flex items-center gap-2"><span className="min-w-0 flex-1 break-all text-sm">{k.label}</span>
        {k.revoked_at ? <Badge variant="secondary">{t('chat.appKeys.revoked')}</Badge> : <Button size="sm" variant="destructive" onClick={() => setRevoking(k)}><Trash2 />{t('chat.appKeys.revoke')}</Button>}</div>
      <code className="break-all text-xs">{k.key_id}</code>
      <p className="break-all text-xs text-muted-foreground">{k.origins.length ? k.origins.join(', ') : t('chat.appKeys.anyOrigin')}</p>
      <p className="text-xs text-muted-foreground">{t('chat.appKeys.lastUsed', { at: k.last_used_at ? fmtDate(k.last_used_at) : t('chat.appKeys.never') })}</p>
    </div>)}
    <div className="grid gap-1.5"><Label htmlFor="chat-key-label">{t('chat.appKeys.label')}</Label>
      <Input id="chat-key-label" maxLength={80} value={label} onChange={e => setLabel(e.target.value)} /></div>
    <div className="grid gap-1.5"><Label htmlFor="chat-key-origins">{t('chat.appKeys.origins')}</Label>
      <Textarea id="chat-key-origins" rows={2} value={origins} onChange={e => setOrigins(e.target.value)} />
      {!origins.trim() && <Alert variant="warning"><TriangleAlert /><AlertDescription>{t('chat.appKeys.anyOriginWarning')}</AlertDescription></Alert>}</div>
    <Button id="chat-key-create" className="justify-self-start" disabled={!ready || busy || !label.trim() || active >= 2} onClick={create}><Plus />{t('chat.appKeys.create')}</Button>
    <Dialog open={created !== null} onOpenChange={open => { if (!open) setCreated(null) }}>
      <DialogContent id="chat-key-secret"><DialogHeader><DialogTitle>{t('chat.appKeys.secretTitle')}</DialogTitle><DialogDescription>{t('chat.appKeys.secretHint')}</DialogDescription></DialogHeader>
        <Label htmlFor="chat-key-secret-value">{t('chat.appKeys.secret')}</Label>
        <Input id="chat-key-secret-value" readOnly value={created?.secret ?? ''} className="font-mono" />
        <Button onClick={() => navigator.clipboard.writeText(created?.secret ?? '').then(() => setCopied(true)).catch(() => setErr(t('chat.appKeys.copyFailed')))}>
          {copied ? <Check /> : <Copy />}{t(copied ? 'chat.copied' : 'chat.copy')}</Button>
      </DialogContent>
    </Dialog>
    <ConfirmDeleteDialog open={revoking !== null} onOpenChange={open => { if (!open) setRevoking(null) }}
      title={t('chat.appKeys.revoke')} name={revoking?.label ?? ''} description={t('chat.appKeys.revokeHint')} confirmLabel={t('chat.appKeys.revoke')}
      onConfirm={async () => { await api(`${url}/${revoking!.key_id}`, { method: 'DELETE' }); await load() }} />
  </section>
}
