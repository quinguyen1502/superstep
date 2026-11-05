import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { KeyRound, Pencil, Plus, Save, Trash2, AlertCircle, Lock, PlugZap, CircleCheck, Info, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { credentialModels, probeProvider, useProviders, type ProbeResult } from '@/lib/providers'
import { useLoadWhen } from '@/lib/use-when'
import { SmtpFields } from '@/components/smtp-fields'
import { SMTP_DEFAULTS, type SmtpSettings } from '@/lib/smtp'
import { Tip } from '@/components/tip'

export type Credential = { id: string; name: string; provider: string; base_url: string | null; hint: string; headers?: Record<string, string>; settings?: SmtpSettings; created: number }
type Status = { busy?: boolean; ok?: ProbeResult; err?: string }

/** Result of 'Test connection' (form or saved row): success badge with model count, or the translated error. */
function ProbeStatus({ s, id }: { s: Status; id: string }) {
  const { t } = useTranslation()
  if (s.busy) return <span className="flex items-center gap-1 text-xs text-muted-foreground"><Loader2 className="size-3 animate-spin" />{t('creds.testing')}</span>
  if (s.ok) return <Badge variant="success" id={id}><CircleCheck />{s.ok.provider === 'smtp' ? t('creds.smtp.testOk', { ms: s.ok.latency_ms }) : t('creds.testOk', { count: s.ok.models.length, ms: s.ok.latency_ms })}</Badge>
  if (s.err) return <Alert variant="destructive" id={id}><AlertCircle /><AlertDescription>{s.err}</AlertDescription></Alert>
  return null
}

const run = async (set: (s: Status) => void, fn: () => Promise<ProbeResult>) => {
  set({ busy: true })
  try { set({ ok: await fn() }) } catch (e: any) { set({ err: e.message }) }
}

export function CredentialsDialog({ trigger, onChanged }: { trigger?: React.ReactElement; onChanged?: () => void } = {}) {
  const { t } = useTranslation(); const [open, setOpen] = useState(false)
  const providers = useProviders()
  const [items, setItems] = useState<Credential[]>([])
  const [name, setName] = useState(''); const [provider, setProvider] = useState('openai')
  const [key, setKey] = useState(''); const [baseUrl, setBaseUrl] = useState(''); const [headers, setHeaders] = useState<Record<string, string>>({})
  const [settings, setSettings] = useState<SmtpSettings>(SMTP_DEFAULTS)
  const [err, setErr] = useState(''); const [test, setTest] = useState<Status>({}); const [rowTest, setRowTest] = useState<Record<string, Status>>({})
  const [editing, setEditing] = useState<Credential | null>(null); const [clearKey, setClearKey] = useState(false)
  const p = providers.find(x => x.id === provider)
  const email = p?.kind === 'email'  // SMTP: settings instead of a base URL, the secret is the password
  const keptKey = !!editing?.hint && !clearKey  // editing: an empty key field keeps the stored secret
  const keyMissing = !!p?.key_required && !key.trim() && !keptKey
  const load = () => api<Credential[]>('/api/credentials').then(setItems)
  const reset = () => { setEditing(null); setClearKey(false); setName(''); setKey(''); setBaseUrl(''); setHeaders({}); setSettings(SMTP_DEFAULTS); setTest({}); setErr('') }
  useLoadWhen(open, load); useLoadWhen(!open, reset)
  const pick = (v: string) => { setProvider(v); setKey(''); setBaseUrl(''); setHeaders({}); setSettings(SMTP_DEFAULTS); setTest({}); setErr('') }  // never carry a key to another provider
  const form = () => ({ api_key: key, base_url: baseUrl || null, headers, ...(email ? { settings } : {}), ...(editing && !clearKey ? { credential_id: editing.id } : {}) })
  const startEdit = (c: Credential) => { reset(); setEditing(c); setName(c.name); setProvider(c.provider); setBaseUrl(c.base_url || ''); setHeaders(c.headers || {}); setSettings({ ...SMTP_DEFAULTS, ...c.settings }) }
  const submit = async () => {
    setErr('')
    try {
      if (editing) await api(`/api/credentials/${editing.id}`, { method: 'PUT', json: { name, base_url: baseUrl || null, headers, api_key: key || null, clear_key: clearKey, ...(email ? { settings } : {}) } })
      else await api('/api/credentials', { method: 'POST', json: { name, provider, api_key: key, base_url: baseUrl || null, headers, ...(email ? { settings } : {}) } })
      reset(); load()
    } catch (e: any) { setErr(e.message) }
  }
  const confirmDel = useConfirmDelete()
  const del = (c: Credential) => confirmDel.ask({ title: t('creds.deleteTitle', { name: c.name }), name: c.name, description: t('creds.deleteBody'),
    onConfirm: async () => { await api(`/api/credentials/${c.id}`, { method: 'DELETE' }); load() } })
  const label = (id: string) => t(`creds.providers.${id}`, { defaultValue: providers.find(x => x.id === id)?.label ?? id })
  return <Dialog open={open} onOpenChange={o => { setOpen(o); if (!o) onChanged?.() }}>
    <DialogTrigger asChild>{trigger ?? <Button variant="outline" id="creds-btn"><KeyRound />{t('creds.button')}</Button>}</DialogTrigger>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-2xl [&>*]:min-w-0">
      <DialogHeader><DialogTitle>{t('creds.title')}</DialogTitle>
        <DialogDescription className="flex items-center gap-1"><Lock className="size-3" />{t('creds.desc')}</DialogDescription></DialogHeader>
      <DialogBody className="space-y-4">
      <div className="space-y-2">
        {items.map(c => <div key={c.id} className={cn('space-y-2 rounded-md border px-3 py-2 text-sm', editing?.id === c.id && 'border-primary bg-accent/40')} data-cred={c.name}>
          <div className="flex min-w-0 items-center gap-2">
            <Badge variant="secondary" className="shrink-0">{label(c.provider)}</Badge><span className="shrink-0 font-medium">{c.name}</span>
            {c.hint && <span className="shrink-0 font-mono text-xs text-muted-foreground">{c.hint}</span>}
            {c.settings?.host && <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground" data-smtp>{c.settings.from_email} · {c.settings.host}:{c.settings.port}</span>}
            {c.base_url && <Tip tip={c.base_url}><span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">{c.base_url}</span></Tip>}
            <div className="ml-auto flex shrink-0 items-center gap-1">
              <Button variant="ghost" size="sm" aria-label={t('creds.testAria', { name: c.name })}
                onClick={() => run(s => setRowTest(r => ({ ...r, [c.id]: s })), () => credentialModels(c.id))}><PlugZap />{t('creds.test')}</Button>
              <Button variant="ghost" size="icon-sm" aria-label={t('creds.editAria', { name: c.name })} onClick={() => startEdit(c)}><Pencil /></Button>
              <Button variant="ghost" size="icon-sm" aria-label={t('creds.deleteAria', { name: c.name })} onClick={() => del(c)}><Trash2 /></Button>
            </div></div>
          {rowTest[c.id] && <ProbeStatus s={rowTest[c.id]} id={`cred-test-${c.id}`} />}
        </div>)}
        {!items.length && <p className="text-xs text-muted-foreground">{t('creds.empty')}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3 border-t pt-3" id="cred-form" data-mode={editing ? 'edit' : 'add'}>
        {editing && <p className="col-span-2 flex items-center gap-1.5 text-sm font-medium" id="cred-edit-title"><Pencil className="size-3.5" />{t('creds.editTitle', { name: editing.name })}</p>}
        <div className="space-y-1.5"><Label htmlFor="cred-name">{t('creds.name')}</Label><Input id="cred-name" value={name} onChange={e => setName(e.target.value)} placeholder={t('creds.namePh')} /></div>
        <div className="space-y-1.5"><Label>{t('creds.provider')}</Label><Select value={provider} onValueChange={pick} disabled={!!editing}><SelectTrigger className="w-full" id="cred-provider"><SelectValue /></SelectTrigger>
          <SelectContent>{providers.map(x => <SelectItem key={x.id} value={x.id}>{label(x.id)}</SelectItem>)}</SelectContent></Select></div>
        {email && <SmtpFields value={settings} onChange={setSettings} />}
        <div className="space-y-1.5 col-span-2"><Label htmlFor="cred-key">{email ? t('creds.smtp.password') : p && !p.key_required ? t('creds.keyOptional') : t('creds.key')}</Label>
          <Input id="cred-key" type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} disabled={clearKey}
            placeholder={editing?.hint ? t('creds.keyKeep', { hint: editing.hint }) : undefined} />
          {editing?.hint && !p?.key_required && <div className="flex items-center gap-2 pt-1"><Switch id="cred-clear-key" checked={clearKey} onCheckedChange={v => { setClearKey(v); if (v) setKey('') }} />
            <Label htmlFor="cred-clear-key" className="text-xs font-normal text-muted-foreground">{t('creds.clearKey')}</Label></div>}</div>
        {!email && <div className="space-y-1.5 col-span-2"><Label htmlFor="cred-base">{t('creds.baseUrl')}</Label>
          <Input id="cred-base" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder={p?.default_base_url ?? 'https://api.openai.com/v1'} />
          {p?.local && <p className="flex items-start gap-1 text-xs text-muted-foreground" id="cred-docker-hint"><Info className="mt-0.5 size-3 shrink-0" />{t('creds.dockerHint')}</p>}</div>}
        {p?.header_fields.map(h => <div key={h} className="space-y-1.5"><Label htmlFor={`cred-h-${h}`}>{t('creds.header', { name: h })}</Label>
          <Input id={`cred-h-${h}`} value={headers[h] ?? ''} onChange={e => setHeaders({ ...headers, [h]: e.target.value })}
            placeholder={t(h === 'X-Title' ? 'creds.titlePh' : 'creds.refererPh')} /></div>)}
      </div>
      <ProbeStatus s={test} id="cred-test-result" />
      {err && <Alert variant="destructive" id="cred-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
      </DialogBody>
      <DialogFooter>
        {editing && <Button variant="ghost" id="cred-cancel" onClick={reset}>{t('common.cancel')}</Button>}
        <Button variant="outline" id="cred-test" disabled={test.busy || keyMissing} onClick={() => run(setTest, () => probeProvider(provider, form()))}><PlugZap />{t('creds.test')}</Button>
        <Button onClick={submit} id={editing ? 'cred-save' : 'cred-add'} disabled={keyMissing}>{editing ? <><Save />{t('common.save')}</> : <><Plus />{t('creds.add')}</>}</Button></DialogFooter>
    </DialogContent>
    {confirmDel.dialog}
  </Dialog>
}
