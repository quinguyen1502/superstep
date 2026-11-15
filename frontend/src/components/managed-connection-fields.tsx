import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { api } from '@/lib/api'
import { channelLabel, type Channel, type Channels } from '@/lib/approvals'
import type { ManagedAdapter, ManagedSettings, McpSecretInput } from '@/lib/mcp'
import { browserDefaults, webDefaults, isBrowserAdapter, type ConnectionErrors } from '@/lib/browser-settings'
import { BrowserConnectionFields } from './browser-connection-fields'

export function ManagedConnectionFields({ adapters, adapter, settings, secrets, fixed, idp, onChange, scope, errors = {}, runtimeEnabled = false }: {
  adapters: ManagedAdapter[]; adapter: string; settings: ManagedSettings; secrets: McpSecretInput[]; fixed: boolean; idp: string; scope: 'user' | 'org'; errors?: ConnectionErrors; runtimeEnabled?: boolean
  onChange: (patch: { adapter?: string; settings?: ManagedSettings; secrets?: McpSecretInput[] }) => void
}) {
  const { t } = useTranslation(); const [channels, setChannels] = useState<Channel[]>([])
  useEffect(() => { api<Channels>('/api/approvals/channels').then(value => setChannels(value.channels)).catch(() => setChannels([])) }, [])
  const definition = adapters.find(value => value.id === adapter)
  const set = (field: string, value: string | number) => onChange({ settings: { ...settings, [field]: value } })
  const asText = (value: unknown) => value === undefined || value === null ? '' : typeof value === 'string' || typeof value === 'number' ? value : JSON.stringify(value)
  return <div className="space-y-3" id={`${idp}-managed`}>
    <div className="space-y-1.5"><Label htmlFor={`${idp}-adapter`}>{t('managedTools.adapter')}</Label>
      <Select value={adapter} disabled={fixed} onValueChange={value => {
        const spec = adapters.find(item => item.id === value)
        onChange({ adapter: value, settings: value === 'browser' ? browserDefaults() : value === 'web' ? webDefaults() : Object.fromEntries(Object.entries(spec?.settings_schema.properties || {}).map(([key, property]) => [key, property.default ?? ''])), secrets: [] })
      }}><SelectTrigger id={`${idp}-adapter`} className="w-full"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{adapters.map(value => <SelectItem key={value.id} value={value.id}><ChannelLogo kind={value.id} />{t(`managedTools.adapters.${value.id}`)}</SelectItem>)}</SelectContent></Select></div>
    {isBrowserAdapter(adapter) ? <BrowserConnectionFields adapter={adapter as 'browser' | 'web'} settings={settings} secrets={secrets} scope={scope} idp={idp} errors={errors} available={!!definition} runtimeEnabled={runtimeEnabled} onChange={onChange} /> : <>
    <div className="grid gap-3 sm:grid-cols-2">{Object.entries(definition?.settings_schema.properties || {}).map(([field, property]) => <div key={field} className={property.format === 'json' ? 'space-y-1.5 sm:col-span-2' : 'space-y-1.5'}>
      <Label htmlFor={`${idp}-${field}`}>{t(`managedTools.fields.${field}`)}</Label>
      {property.resource_kind ? <Select value={String(settings[field] ?? '')} onValueChange={value => set(field, value)}>
        <SelectTrigger id={`${idp}-${field}`} className="w-full"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{channels.filter(channel => channel.kind === property.resource_kind).map(channel => <SelectItem key={channel.id} value={channel.id}><ChannelLogo kind={channel.kind} />{channelLabel(t, channel)}</SelectItem>)}</SelectContent>
      </Select> : property.format === 'json' ? <Textarea id={`${idp}-${field}`} className="font-mono field-sizing-fixed" rows={12} value={asText(settings[field])}
        onChange={event => set(field, event.target.value)} /> : <Input id={`${idp}-${field}`} type={property.type === 'integer' ? 'number' : 'text'} value={asText(settings[field])}
        onChange={event => set(field, property.type === 'integer' && event.target.value ? Number(event.target.value) : event.target.value)} />}
    </div>)}</div>
    {definition?.secret_fields.map(field => {
      const secret = secrets.find(item => item.name === field)
      return <div className="space-y-1.5" key={field}><Label htmlFor={`${idp}-${field}`}>{t(`managedTools.fields.${field}`)}</Label>
        <Textarea id={`${idp}-${field}`} autoComplete="off" className="font-mono" rows={4} value={secret?.value || ''}
          placeholder={secret?.stored ? t('mcp.keepSecret') : t(field === 'headers' ? 'managedTools.headerHelp' : field === 'google_credentials' ? 'managedTools.googleCredentialHelp' : 'managedTools.secretHelp')} onChange={event => onChange({
            secrets: [...secrets.filter(item => item.name !== field), { name: field, value: event.target.value, stored: !!secret?.stored }],
          })} /></div>
    })}
    {definition && <p className="text-xs text-muted-foreground">{t(`managedTools.setup.${definition.id}`)}</p>}
    <p className="text-xs text-muted-foreground">{t('managedTools.help')}</p>
    </>}
  </div>
}
