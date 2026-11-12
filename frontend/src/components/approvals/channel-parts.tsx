/** Building blocks of the approval-channel settings: secret fields, copyable URLs,
 *  one connection (config, Test connection, replace secrets, register, remove) and the add-connection form. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRound, MessageSquare, PlugZap, Plus, Save, Trash2, TriangleAlert, Webhook } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Channel, ChannelKind } from '@/lib/approvals'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { useAction } from './use-action'
import { CopyField } from '@/components/copy-field'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { HandbookLink } from '@/components/handbook-link'

const GUIDE: Record<string, string> = { slack: 'slack', telegram: 'telegram', whatsapp: 'whatsapp-cloud-api', email: 'email', teams: 'teams' }

export { ErrorAlert } from './error-alert'


type Vals = Record<string, string>
const filled = (k: ChannelKind, v: Vals) => k.fields.some(f => !k.optional.includes(f) && v[f]?.trim())

function SecretFields({ k, vals, setVals, idp, placeholder }: { k: ChannelKind; vals: Vals; setVals: (f: (v: Vals) => Vals) => void; idp: string; placeholder?: string }) {
  const { t } = useTranslation()
  return <div className="grid gap-3 sm:grid-cols-2">
    {k.fields.map(f => <div key={f} className="space-y-1.5">
      <Label htmlFor={`${idp}-${f}`}>{t(`approvals.field.${f}`)}{k.optional.includes(f) && <span className="text-muted-foreground"> · {t('approvals.optional')}</span>}</Label>
      <Input id={`${idp}-${f}`} type="password" autoComplete="off" value={vals[f] || ''} placeholder={placeholder}
        onChange={e => setVals(v => ({ ...v, [f]: e.target.value }))} /></div>)}
  </div>
}

/** One connection: account, callback URL, Test connection; its owner (or an admin for org ones) can replace secrets, register, remove. */
export function ConnectionItem({ c, k, publicUrl, onChange }: { c: Channel; k: ChannelKind; publicUrl: string | null; onChange: () => void }) {
  const { t } = useTranslation(); const [vals, setVals] = useState<Vals>({}); const [edit, setEdit] = useState(false)
  const { run, alerts, busy } = useAction(() => { setVals({}); onChange() })
  const test = useAction(onChange); const confirmDel = useConfirmDelete(); const label = c.name || t(`approvals.kind.${c.kind}`)
  const url = c.callback_url || location.origin + c.callback_path
  const shared = c.shared_callback_path ? (c.shared_callback_url || location.origin + c.shared_callback_path) : null
  const idp = `ch-${c.id}`
  return <div className="space-y-3 rounded-lg border p-4" data-testid={`channel-${c.kind}-${c.scope}`} data-channel-id={c.id}>
    <div className="flex flex-wrap items-center gap-2">
      <ChannelLogo kind={c.kind} /><span className="font-medium">{c.name || t(`approvals.kind.${c.kind}`)}</span>
      {c.team_id && <span className="font-mono text-xs text-muted-foreground">({c.team_id})</span>}
      <Badge variant="outline" className="font-mono">{c.hint}</Badge>
    </div>
    {k.link_based ? <p className="text-xs text-muted-foreground">{t('approvals.linkNote')}</p>  /* no callback: answered on /approve */
      : shared ? <>
      <CopyField id={`${idp}-shared`} label={t('approvals.sharedUrl')} value={shared} />
      <p className="text-xs text-muted-foreground">{t('approvals.sharedHelp', { team: c.team_id })}</p></>
      : <CopyField id={`${idp}-url`} label={t('approvals.callbackUrl')} value={url} />}
    {!publicUrl && <p className="text-xs text-muted-foreground" id={`${idp}-public-url-missing`}>{t('approvals.publicUrlMissing')}{' '}
      <HandbookLink id={`${idp}-public-url-help`} page="operate/expose-local" label={t('docs.learnMore')} ariaLabel={t('docs.exposeLocalAria')} /></p>}
    <ChatSetup c={c} idp={idp} />
    {!c.editable && <p className="text-xs text-muted-foreground">{t('approvals.orgReadOnly')}</p>}
    {edit && <SecretFields k={k} vals={vals} setVals={setVals} idp={idp} placeholder={t('approvals.keepSecret')} />}
    {alerts}{test.alerts}
    <div className="flex flex-wrap justify-end gap-2">
      <Button variant="outline" size="sm" id={`${idp}-test`} disabled={test.busy}
        onClick={() => test.run(() => api<{ name: string | null }>(`/api/approvals/channels/${c.id}/test`, { method: 'POST' }),
          r => t('settings.testOk', { name: r.name || t(`approvals.kind.${c.kind}`) }))}><PlugZap />{t('settings.test')}</Button>
      {c.editable && <>
        {c.kind === 'telegram' && <Button variant="outline" size="sm" id={`${idp}-register`} disabled={busy}
          onClick={() => run(() => api(`/api/approvals/channels/${c.id}/register-webhook`, { method: 'POST' }), t('approvals.registered'))}><Webhook />{t('approvals.register')}</Button>}
        {edit ? <Button size="sm" id={`${idp}-save`} disabled={busy || !filled(k, vals)}
          onClick={async () => { if (await run(() => api(`/api/approvals/channels/${c.id}`, { method: 'PUT', json: vals }), t('approvals.saved'))) setEdit(false) }}><Save />{t('approvals.save')}</Button>
          : <Button variant="outline" size="sm" id={`${idp}-edit`} onClick={() => setEdit(true)}><KeyRound />{t('approvals.replaceSecrets')}</Button>}
        <Button variant="ghost" size="sm" disabled={busy} onClick={() => confirmDel.ask({ title: t('approvals.removeTitle', { name: label }), name: label, description: t('approvals.removeBody'), confirmLabel: t('confirmDelete.remove'), onConfirm: () => run(() => api(`/api/approvals/channels/${c.id}`, { method: 'DELETE' }), t('approvals.removed')) })}><Trash2 />{t('approvals.remove')}</Button>
      </>}
    </div>
    {confirmDel.dialog}
  </div>
}

/** Chat triggers: what this connection needs before a message can start a run. Slack: the Event Subscriptions
 *  URL and the two read scopes (unknown until the next Test); Telegram: Register webhook again, so messages arrive too. */
function ChatSetup({ c, idp }: { c: Channel; idp: string }) {
  const { t } = useTranslation()
  if (!c.chat) return null
  const missing = c.chat.missing_scopes
  return <div className="space-y-2" data-testid={`${idp}-chat`}>
    {c.chat.events_path && <CopyField id={`${idp}-events`} label={t('approvals.chat.eventsUrl')} value={c.chat.events_url || location.origin + c.chat.events_path} />}
    <p className="text-xs text-muted-foreground"><MessageSquare className="mr-1 inline size-3.5 align-[-2px]" />{t(`approvals.chat.help.${c.kind}`)}</p>
    {missing && missing.length > 0 && <Alert variant="warning" id={`${idp}-scopes`}><TriangleAlert /><AlertDescription>{t('approvals.chat.missing', { scopes: missing.join(', ') })}</AlertDescription></Alert>}
    {missing === null && <p className="text-xs text-muted-foreground" id={`${idp}-scopes-unknown`}>{t('approvals.chat.unknown')}</p>}
  </div>
}

/** New connection of one platform in one scope (the tab it sits in): optional name + secrets. */
export function AddConnection({ k, scope, onChange, collapsed = false }: { k: ChannelKind; scope: 'user' | 'org'; onChange: () => void; collapsed?: boolean }) {
  const { t } = useTranslation(); const [name, setName] = useState(''); const [vals, setVals] = useState<Vals>({}); const [open, setOpen] = useState(!collapsed)
  const { run, alerts, busy } = useAction(() => { setVals({}); setName(''); onChange() })
  const idp = `add-${k.kind}-${scope}`
  if (!open) return <Button variant="outline" size="sm" className="w-full border-dashed" id={`${idp}-open`} onClick={() => setOpen(true)}><Plus />{t('approvals.add')}</Button>
  return <div className="space-y-3 rounded-lg border border-dashed p-4" data-testid={idp}>
    <div className="flex items-center gap-2 text-sm font-medium"><Plus className="size-4" />{t('approvals.add')}</div>
    <div className="space-y-1.5"><Label htmlFor={`${idp}-name`}>{t('approvals.name')}<span className="text-muted-foreground"> · {t('approvals.optional')}</span></Label>
      <Input id={`${idp}-name`} value={name} onChange={e => setName(e.target.value)} placeholder={t('approvals.namePh')} /></div>
    <SecretFields k={k} vals={vals} setVals={setVals} idp={idp} />
    <p className="text-xs text-muted-foreground">{t(`approvals.help.${k.kind}`)}{GUIDE[k.kind] && <>{' '}
      <HandbookLink id={`${idp}-guide`} page="operate/channels" anchor={GUIDE[k.kind]} label={t('docs.setupGuide')}
        ariaLabel={t('docs.setupGuideAria', { platform: t(`approvals.kind.${k.kind}`) })} /></>}</p>
    {alerts}
    <div className="flex justify-end"><Button size="sm" id={`${idp}-save`} disabled={busy || !filled(k, vals)}
      onClick={() => run(() => api('/api/approvals/channels', { method: 'POST', json: { kind: k.kind, scope, name, ...vals } }), t('approvals.saved'))}><Save />{t('approvals.save')}</Button></div>
  </div>
}
