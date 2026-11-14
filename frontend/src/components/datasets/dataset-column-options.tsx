import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DatasetValueField } from './dataset-fields'
import { datasetSystemTime, type ColumnDraft, type DatasetDisplayFormat, type DatasetValidationRules } from '@/lib/datasets'

export function DatasetColumnOptions({ column, onChange }: { column: ColumnDraft; onChange: (next: ColumnDraft) => void }) {
  const { t } = useTranslation()
  const id = useId()
  const rules = column.validation_rules ?? {}
  const formatting = column.display_format ?? {}
  const text = column.kind === 'text' || column.kind === 'long_text'
  const number = column.kind === 'number'
  const date = column.kind === 'date' || column.kind === 'datetime'
  const email = column.kind === 'email'
  const updateRule = (next: DatasetValidationRules) => onChange({ ...column, validation_rules: { ...rules, ...next } })
  const updateFormat = (next: DatasetDisplayFormat) => onChange({ ...column, display_format: { ...formatting, ...next } })

  return <>
    {(text || number || date || email) && <fieldset className="grid gap-2 rounded-md border p-3 sm:col-span-2 sm:grid-cols-2">
      <legend className="px-1 text-sm">{t('dataset.columnRules')}</legend>
      {text && (['min_length', 'max_length'] as const).map(key => <div className="space-y-1" key={key}>
        <Label htmlFor={`${id}-${key}`}>{t(`dataset.rule.${key}`)}</Label>
        <Input id={`${id}-${key}`} type="number" min={0} max={16384} value={rules[key] ?? ''}
          onChange={event => updateRule({ [key]: event.target.value === '' ? undefined : event.target.valueAsNumber })} />
      </div>)}
      {(date || number) && (['min', 'max'] as const).map(key => <div className="space-y-1" key={key}>
        <Label htmlFor={`${id}-${key}`}>{t(`dataset.rule.${key}`)}</Label>
        <DatasetValueField id={`${id}-${key}`} label={t(`dataset.rule.${key}`)} column={column} value={rules[key] ?? null}
          nullable onChange={value => updateRule({ [key]: value ?? undefined })} />
      </div>)}
      {number && <Label className="gap-2">
        <Checkbox checked={rules.integer ?? false} onCheckedChange={value => updateRule({ integer: value === true || undefined })} />
        {t('dataset.rule.integer')}
      </Label>}
      {email && <div className="space-y-1 sm:col-span-2">
        <Label htmlFor={`${id}-domains`}>{t('dataset.rule.domains')}</Label>
        <Input id={`${id}-domains`} defaultValue={rules.domains?.join(', ') ?? ''}
          onChange={event => updateRule({ domains: event.target.value.trim() ? event.target.value.split(',').map(item => item.trim()).filter(Boolean) : undefined })} />
      </div>}
    </fieldset>}
    {(number || date || datasetSystemTime(column.kind)) && <fieldset className="grid gap-2 rounded-md border p-3 sm:col-span-2 sm:grid-cols-2">
      <legend className="px-1 text-sm">{t('dataset.columnFormat')}</legend>
      {number && <>
        <div className="space-y-1">
          <Label htmlFor={`${id}-decimals`}>{t('dataset.format.decimals')}</Label>
          <Input id={`${id}-decimals`} min={0} max={12} type="number" value={formatting.decimals ?? ''}
            onChange={event => updateFormat({ decimals: event.target.value === '' ? undefined : event.target.valueAsNumber })} />
        </div>
        <div className="space-y-1">
          <Label htmlFor={`${id}-style`}>{t('dataset.format.style')}</Label>
          <Select value={formatting.style ?? 'decimal'} onValueChange={style => updateFormat({ style: style as DatasetDisplayFormat['style'], currency: style === 'currency' ? formatting.currency ?? 'USD' : undefined })}>
            <SelectTrigger id={`${id}-style`} className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>{['decimal', 'percent', 'currency'].map(style =>
              <SelectItem key={style} value={style}>{t(`dataset.format.${style}`)}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        {formatting.style === 'currency' && <div className="space-y-1">
          <Label htmlFor={`${id}-currency`}>{t('dataset.format.currencyCode')}</Label>
          <Input id={`${id}-currency`} required maxLength={3} pattern="[A-Z]{3}" value={formatting.currency ?? ''}
            onChange={event => updateFormat({ currency: event.target.value.toUpperCase() })} />
        </div>}
        <Label className="gap-2">
          <Checkbox checked={formatting.thousands ?? false} onCheckedChange={value => updateFormat({ thousands: value === true })} />
          {t('dataset.format.thousands')}
        </Label>
      </>}
      {!number && <div className="space-y-1">
        <Label htmlFor={`${id}-date-style`}>{t('dataset.format.dateStyle')}</Label>
        <Select value={formatting.date_style ?? '$default'} onValueChange={value =>
          updateFormat({ date_style: value === '$default' ? undefined : value as DatasetDisplayFormat['date_style'] })}>
          <SelectTrigger id={`${id}-date-style`} className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="$default">{t('dataset.format.default')}</SelectItem>
            {['short', 'medium', 'long', 'iso'].map(value =>
              <SelectItem key={value} value={value}>{t(`dataset.format.${value}`)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>}
    </fieldset>}
  </>
}
