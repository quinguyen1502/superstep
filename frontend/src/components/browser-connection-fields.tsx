import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, KeyRound, ShieldAlert, Trash2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { connectionFieldId, lines, object, text, type ConnectionErrors } from '@/lib/browser-settings'
import type { ManagedSettings, McpSecretInput } from '@/lib/mcp'

type FieldControl = { id: string; 'aria-invalid': boolean; 'aria-describedby'?: string }
function Field({ idp, name, errors, children }: { idp: string; name: string; errors: ConnectionErrors; children: (props: FieldControl) => ReactNode }) {
  const { t } = useTranslation(), id = connectionFieldId(idp, name), error = errors[name]
  return <div className="space-y-1.5"><Label htmlFor={id}>{t(`browserSettings.fields.${name}`)}</Label>
    {children({ id, 'aria-invalid': !!error, 'aria-describedby': error ? `${id}-error` : undefined })}
    {error && <p id={`${id}-error`} role="alert" className="text-xs text-destructive">{t(error)}</p>}
  </div>
}

function SecretField({ name, idp, secrets, errors, onChange, multiline = false }: {
  name: string; idp: string; secrets: McpSecretInput[]; errors: ConnectionErrors; onChange: (secrets: McpSecretInput[]) => void; multiline?: boolean
}) {
  const { t } = useTranslation(), confirm = useConfirmDelete(), secret = secrets.find(item => item.name === name)
  const set = (value: string) => onChange([...secrets.filter(item => item.name !== name), { name, value, stored: !!secret?.stored }])
  return <div className="space-y-1.5"><Field idp={idp} name={name} errors={errors}>{props => multiline
    ? <Textarea {...props} autoComplete="off" className="font-mono field-sizing-fixed" rows={5} value={secret?.value || ''} placeholder={secret?.stored ? t('mcp.keepSecret') : t('browserSettings.secretPlaceholder')} onChange={event => set(event.target.value)} />
    : <Input {...props} type="password" autoComplete="new-password" value={secret?.value || ''} placeholder={secret?.stored ? t('mcp.keepSecret') : t('browserSettings.secretPlaceholder')} onChange={event => set(event.target.value)} />}</Field>
    {secret?.stored && <div className="flex flex-wrap items-center gap-2"><Badge variant="outline"><KeyRound />{t('browserSettings.stored')}</Badge>
      <Button variant="ghost" size="sm" type="button" id={`${idp}-${name}-clear`} onClick={() => confirm.ask({ title: t('browserSettings.clearSecretTitle', { name }), name,
        description: t('browserSettings.clearSecretBody'), onConfirm: () => onChange(secrets.filter(item => item.name !== name)) })}><Trash2 />{t('browserSettings.clearSecret')}</Button></div>}
    {confirm.dialog}
  </div>
}

type Props = { adapter: 'browser' | 'web'; settings: ManagedSettings; secrets: McpSecretInput[]; scope: 'user' | 'org'; idp: string;
  errors: ConnectionErrors; available: boolean; onChange: (patch: { settings?: ManagedSettings; secrets?: McpSecretInput[] }) => void }

export function BrowserConnectionFields({ adapter, settings, secrets, scope, idp, errors, available, onChange }: Props) {
  const { t } = useTranslation(), confirm = useConfirmDelete(), [limitsOpen, setLimitsOpen] = useState(false)
  const update = (patch: ManagedSettings) => onChange({ settings: { ...settings, ...patch } })
  const proxy = object(settings.proxy), profile = object(settings.profile), search = object(settings.search)
  const mode = text(proxy.mode, 'direct'), provider = text(settings.provider, 'local'), enabled = lines(settings.enabled_tools ?? ['fetch'])
  const setSecret = (value: McpSecretInput[]) => onChange({ secrets: value })
  const origins = <Field idp={idp} name="allowed_origins" errors={errors}>{props => <Textarea {...props} className="font-mono field-sizing-fixed" rows={3}
    value={lines(settings.allowed_origins).join('\n')} onChange={event => update({ allowed_origins: event.target.value.split('\n') })} placeholder={t('browserSettings.originPlaceholder')} />}</Field>
  const removeProfile = () => {
    const apply = () => onChange({ settings: { ...settings, profile: null }, secrets: secrets.filter(item => item.name !== 'profile_state') })
    const name = text(profile.name)
    if (!name) { apply(); return }
    confirm.ask({ title: t('browserSettings.removeProfileTitle', { name }), name, description: t('browserSettings.removeProfileBody'), onConfirm: apply })
  }
  const limits = [['action_timeout_ms', 1000, 60000, 30000], ['idle_timeout_s', 30, 600, 120], ['lifetime_s', 30, 1800, 600], ['max_actions', 1, 100, 12]] as const
  return <div className="space-y-3" id={`${idp}-browser-settings`}>
    {!available && <Alert variant="warning"><ShieldAlert /><AlertDescription>{t('browserSettings.disabled')}</AlertDescription></Alert>}
    <fieldset disabled={!available} className="space-y-4">
      <p className="text-xs text-muted-foreground">{t(adapter === 'browser' ? 'browserSettings.connectionHelp' : 'browserSettings.webHelp')}</p>
      {adapter === 'browser' ? <>
        <Field idp={idp} name="provider" errors={errors}>{props => <Select value={provider} onValueChange={value => update({ provider: value })}>
          <SelectTrigger {...props} className="w-full"><SelectValue /></SelectTrigger><SelectContent>
            <SelectItem value="local">{t('browserSettings.providers.local')}</SelectItem><SelectItem value="controlled_remote">{t('browserSettings.providers.controlled_remote')}</SelectItem>
          </SelectContent></Select>}</Field>
        {provider === 'controlled_remote' && <div className="space-y-3">
          <p className="text-xs text-muted-foreground">{t('browserSettings.remoteHelp')}</p>
          <SecretField name="remote_endpoint" idp={idp} secrets={secrets} errors={errors} onChange={setSecret} />
          <SecretField name="remote_token" idp={idp} secrets={secrets} errors={errors} onChange={setSecret} />
        </div>}
        <Separator /><h3 className="text-sm font-medium">{t('browserSettings.network')}</h3>
        <Field idp={idp} name="proxy_mode" errors={errors}>{props => <Select value={mode} onValueChange={value => update({ proxy: { ...proxy, mode: value } })}>
          <SelectTrigger {...props} className="w-full"><SelectValue /></SelectTrigger><SelectContent>
            {['direct', 'operator_default', 'custom'].map(value => <SelectItem key={value} value={value}>{t(`browserSettings.proxyModes.${value}`)}</SelectItem>)}
          </SelectContent></Select>}</Field>
        {mode === 'custom' && <div className="space-y-3">
          <Field idp={idp} name="proxy_server" errors={errors}>{props => <Input {...props} value={text(proxy.server)} placeholder={t('browserSettings.proxyPlaceholder')} onChange={event => update({ proxy: { ...proxy, server: event.target.value } })} />}</Field>
          <Field idp={idp} name="proxy_auth" errors={errors}>{props => <Select value={text(proxy.auth, 'none')} onValueChange={value => update({ proxy: { ...proxy, auth: value } })}>
            <SelectTrigger {...props} className="w-full"><SelectValue /></SelectTrigger><SelectContent>
              <SelectItem value="none">{t('browserSettings.auth.none')}</SelectItem><SelectItem value="basic">{t('browserSettings.auth.basic')}</SelectItem>
            </SelectContent></Select>}</Field>
          {proxy.auth === 'basic' && <div className="grid gap-3 sm:grid-cols-2">{['proxy_username', 'proxy_password'].map(name => <SecretField key={name} name={name} idp={idp} secrets={secrets} errors={errors} onChange={setSecret} />)}</div>}
        </div>}
        <p className="text-xs text-muted-foreground">{t('browserSettings.proxyHelp')}</p>
        {origins}<p className="text-xs text-muted-foreground">{t('browserSettings.originHelp')}</p>
        <Separator /><div className="flex items-center justify-between gap-3"><Label htmlFor={`${idp}-profile-enabled`}>{t('browserSettings.profile')}</Label>
          <Switch id={`${idp}-profile-enabled`} checked={!!settings.profile} disabled={scope !== 'user'} onCheckedChange={value => value ? update({ profile: { name: '', origins: [] } }) : removeProfile()} /></div>
        <p className="text-xs text-muted-foreground">{t(scope === 'user' ? 'browserSettings.profileHelp' : 'browserSettings.orgProfileHelp')}</p>
        {settings.profile != null && <div className="space-y-3">
          <Field idp={idp} name="profile_name" errors={errors}>{props => <Input {...props} value={text(profile.name)} onChange={event => update({ profile: { ...profile, name: event.target.value } })} />}</Field>
          <Field idp={idp} name="profile_origins" errors={errors}>{props => <Textarea {...props} className="font-mono field-sizing-fixed" rows={3} value={lines(profile.origins).join('\n')} placeholder={t('browserSettings.httpsOriginPlaceholder')} onChange={event => update({ profile: { ...profile, origins: event.target.value.split('\n') } })} />}</Field>
          <SecretField name="profile_state" idp={idp} secrets={secrets} errors={errors} onChange={setSecret} multiline />
          <p className="text-xs text-muted-foreground">{t('browserSettings.profileStateHelp')}</p>
          <Button variant="outline" type="button" onClick={removeProfile} id={`${idp}-profile-remove`}><Trash2 />{t('browserSettings.removeProfile')}</Button>
        </div>}
        <Separator /><Collapsible open={limitsOpen || limits.some(([name]) => errors[name])} onOpenChange={setLimitsOpen}>
          <CollapsibleTrigger asChild><Button variant="ghost" type="button" aria-controls={`${idp}-limits`}><ChevronDown />{t('browserSettings.resources')}</Button></CollapsibleTrigger>
          <CollapsibleContent id={`${idp}-limits`} className="space-y-3"><div className="grid gap-3 sm:grid-cols-2">{limits.map(([name, min, max, fallback]) => <Field key={name} idp={idp} name={name} errors={errors}>{props => <div className="space-y-1.5"><Input {...props} type="number" min={min} max={max} aria-describedby={[props['aria-describedby'], `${props.id}-range`].filter(Boolean).join(' ')}
            value={settings[name] === undefined ? fallback : String(settings[name])} onChange={event => update({ [name]: event.target.value === '' ? '' : Number(event.target.value) })} /><p id={`${props.id}-range`} className="text-xs text-muted-foreground">{t('browserSettings.range', { min, max })}</p></div>}</Field>)}</div>
            <p className="text-xs text-muted-foreground">{t('browserSettings.resourceHelp')}</p></CollapsibleContent>
        </Collapsible>
        <p className="text-xs text-muted-foreground">{t('browserSettings.stealthHelp')}</p>
      </> : <>
        <h3 className="text-sm font-medium">{t('browserSettings.webTools')}</h3>
        {['search', 'fetch'].map(name => <div key={name} className="flex items-center justify-between gap-3"><Label htmlFor={`${idp}-enable-${name}`}>{t(`browserSettings.tools.${name}`)}</Label>
          <Switch id={`${idp}-enable-${name}`} checked={enabled.includes(name)} onCheckedChange={checked => update({ enabled_tools: checked ? [...enabled, name] : enabled.filter(value => value !== name),
            ...(checked && name === 'search' && !settings.search ? { search: { provider: 'searxng', endpoint: '' } } : {}) })} /></div>)}
        {!enabled.length && <p className="text-xs text-muted-foreground">{t('browserSettings.noWebTools')}</p>}
        {(enabled.includes('search') || !!settings.search) && <div className="space-y-3">
          <Field idp={idp} name="search_endpoint" errors={errors}>{props => <Input {...props} value={text(search.endpoint)} placeholder={t('browserSettings.searchPlaceholder')} onChange={event => update({ search: { ...search, provider: 'searxng', endpoint: event.target.value } })} />}</Field>
          <SecretField name="search_headers" idp={idp} secrets={secrets} errors={errors} onChange={setSecret} multiline />
          <p className="text-xs text-muted-foreground">{t('browserSettings.searchHelp')}</p>
        </div>}
        {origins}<p className="text-xs text-muted-foreground">{t('browserSettings.webOriginHelp')}</p>
      </>}
    </fieldset>
    {confirm.dialog}
  </div>
}
