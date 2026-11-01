import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { EventPolicy } from '@/lib/chat-triggers'

export function EventBindingSettings({ value, fields, onChange }: { value: EventPolicy; fields: string[]; onChange: (v: EventPolicy) => void }) {
  const { t } = useTranslation()
  return <div className="space-y-3" id="event-binding-settings">
    <p className="text-xs text-muted-foreground">{t('eventBinding.admissionHelp')}</p>
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-1.5"><Label htmlFor="event-senders">{t('eventBinding.senders')}</Label>
        <Input id="event-senders" value={value.senders.join(',')} placeholder={t('eventBinding.sendersPh')}
          onChange={e => onChange({ ...value, senders: e.target.value.split(',') })} /></div>
      <div className="space-y-1.5"><Label htmlFor="event-type">{t('eventBinding.type')}</Label>
        <Input id="event-type" value={value.type} onChange={e => onChange({ ...value, type: e.target.value })} /></div>
    </div>
    <p className="text-xs text-muted-foreground">{t('eventBinding.mappingHelp')}</p>
    <div className="grid gap-3 sm:grid-cols-2">{fields.map(field => <div key={field} className="space-y-1.5">
      <Label htmlFor={`event-map-${field}`}>{field}</Label>
      <Input id={`event-map-${field}`} className="font-mono" value={value.mapping[field] || ''} placeholder={t('eventBinding.pathPh')}
        onChange={e => {
          const mapping = { ...value.mapping }; if (e.target.value) mapping[field] = e.target.value; else delete mapping[field]
          onChange({ ...value, mapping })
        }} />
    </div>)}</div>
  </div>
}
