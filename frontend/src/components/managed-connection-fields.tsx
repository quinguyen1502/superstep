import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { channelLabel, type Channel, type Channels } from '@/lib/approvals'
import type { ManagedAdapter } from '@/lib/mcp'

type Secret = { name: string; value: string; stored: boolean }
export function ManagedConnectionFields({ adapters, adapter, settings, secrets, fixed, idp, onChange }: {
  adapters: ManagedAdapter[]; adapter: string; settings: Record<string, string | number>; secrets: Secret[]; fixed: boolean; idp: string
  onChange: (patch: { adapter?: string; settings?: Record<string, string | number>; secrets?: Secret[] }) => void
}) {
  const { t } = useTranslation(); const [channels, setChannels] = useState<Channel[]>([])
  useEffect(() => { api<Channels>('/api/approvals/channels').then(value => setChannels(value.channels)).catch(() => setChannels([])) }, [])
  const definition = adapters.find(value => value.id === adapter)
  const set = (field: string, value: string | number) => onChange({ settings: { ...settings, [field]: value } })
  return <div className="space-y-3" id={`${idp}-managed`}>
    <div className="space-y-1.5"><Label htmlFor={`${idp}-adapter`}>{t('managedTools.adapter')}</Label>
      <Select value={adapter} disabled={fixed} onValueChange={value => {
        const spec = adapters.find(item => item.id === value)
        onChange({ adapter: value, settings: Object.fromEntries(Object.entries(spec?.settings_schema.properties || {}).map(([key, property]) => [key, property.default ?? ''])), secrets: [] })
      }}><SelectTrigger id={`${idp}-adapter`} className="w-full"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{adapters.map(value => <SelectItem key={value.id} value={value.id}>{t(`managedTools.adapters.${value.id}`)}</SelectItem>)}</SelectContent></Select></div>
    <div className="grid gap-3 sm:grid-cols-2">{Object.entries(definition?.settings_schema.properties || {}).map(([field, property]) => <div key={field} className="space-y-1.5">
      <Label htmlFor={`${idp}-${field}`}>{t(`managedTools.fields.${field}`)}</Label>
      {property.resource_kind ? <Select value={String(settings[field] ?? '')} onValueChange={value => set(field, value)}>
        <SelectTrigger id={`${idp}-${field}`} className="w-full"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{channels.filter(channel => channel.kind === property.resource_kind).map(channel => <SelectItem key={channel.id} value={channel.id}>{channelLabel(t, channel)}</SelectItem>)}</SelectContent>
      </Select> : <Input id={`${idp}-${field}`} type={property.type === 'integer' ? 'number' : 'text'} value={settings[field] ?? ''}
        onChange={event => set(field, property.type === 'integer' && event.target.value ? Number(event.target.value) : event.target.value)} />}
    </div>)}</div>
    {definition?.secret_fields.map(field => {
      const secret = secrets.find(item => item.name === field)
      return <div className="space-y-1.5" key={field}><Label htmlFor={`${idp}-${field}`}>{t(`managedTools.fields.${field}`)}</Label>
        <Textarea id={`${idp}-${field}`} autoComplete="off" className="font-mono" rows={4} value={secret?.value || ''}
          placeholder={secret?.stored ? t('mcp.keepSecret') : t('managedTools.secretHelp')} onChange={event => onChange({
            secrets: [...secrets.filter(item => item.name !== field), { name: field, value: event.target.value, stored: !!secret?.stored }],
          })} /></div>
    })}
    {definition && <p className="text-xs text-muted-foreground">{t(`managedTools.setup.${definition.id}`)}</p>}
    <p className="text-xs text-muted-foreground">{t('managedTools.help')}</p>
  </div>
}
