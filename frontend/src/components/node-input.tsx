import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { StateFieldAction } from '@/components/state-field-action'

/** Which state fields this node receives. All off stores nothing, so the node sees the whole state. */
export function NodeInput({ fields, value, onChange }: {
  fields: string[]
  value?: string[]
  onChange: (next: string[] | undefined) => void
}) {
  const { t } = useTranslation()
  const selected = new Set(value || [])
  const toggle = (name: string, on: boolean) => {
    const next = fields.filter(field => field === name ? on : selected.has(field))
    onChange(next.length ? next : undefined)
  }
  return <div className="space-y-3">
    <Separator />
    <div className="text-xs font-semibold uppercase text-muted-foreground">{t('editor.inputFields')}</div>
    {fields.length === 0
      ? <p className="text-[11px] text-muted-foreground">{t('editor.inputFieldsEmpty')}</p>
      : fields.map(name => <div key={name} className="flex items-center justify-between gap-2">
          <Label htmlFor={`node-input-${name}`} className="font-mono text-xs">{name}</Label>
          <Switch id={`node-input-${name}`} size="sm" checked={selected.has(name)} onCheckedChange={on => toggle(name, on)} />
        </div>)}
    <p className="text-[11px] text-muted-foreground">{t('editor.inputFieldsHint')}</p>
    <StateFieldAction compact={false} onCreated={name => { if (value?.length) onChange([...new Set([...value, name])]) }} />
  </div>
}
