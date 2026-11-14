import { useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { enUS, vi } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Input } from '@/components/ui/input'
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from '@/components/ui/input-group'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Textarea } from '@/components/ui/textarea'
import { datasetKinds, fromDraft, type CellValue, type ColumnDraft, type DatasetColumn, type DatasetKind } from '@/lib/datasets'
import { cn } from '@/lib/utils'
import { DatasetFieldIcon } from './dataset-field-icon'

function localDatetime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 23)
}

function DatasetCalendar({ inputId, value, nullable, disabled, kind, onPick }: {
  inputId: string
  value: string
  nullable: boolean
  disabled?: boolean
  kind: 'date' | 'datetime'
  onPick: (day: string | null) => void
}) {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const picked = useRef(false)
  const date = parseISO(value.slice(0, 10))
  const selected = Number.isNaN(date.getTime()) ? undefined : date
  const pick = (day: string | null) => { picked.current = true; onPick(day); setOpen(false) }
  return <Popover open={open} onOpenChange={setOpen}>
    <PopoverTrigger asChild>
      <InputGroupButton size="icon-xs" disabled={disabled} aria-label={t('dataset.pickDate')}>
        <DatasetFieldIcon kind={kind} />
      </InputGroupButton>
    </PopoverTrigger>
    <PopoverContent align="start" className="w-fit" aria-label={t('dataset.pickDate')} data-dataset-calendar=""
      onCloseAutoFocus={event => {
        if (!picked.current) return
        picked.current = false
        const input = document.getElementById(inputId)
        if (input instanceof HTMLInputElement && !input.disabled) {
          event.preventDefault()
          input.focus()
        }
      }}>
      <Calendar mode="single" selected={selected} defaultMonth={selected} locale={i18n.language.startsWith('vi') ? vi : enUS}
        onSelect={day => { if (day) pick(format(day, 'yyyy-MM-dd')) }} />
      {nullable && value && <Button type="button" variant="ghost" size="sm" onClick={() => pick(null)}>{t('dataset.clearValue')}</Button>}
    </PopoverContent>
  </Popover>
}

export function DatasetValueField({ id, label, column, value, onChange, nullable = !column.required, focus, disabled, inline, openPicker, onCalendarPick, error }: {
  id: string
  label: string
  column: DatasetColumn
  value: CellValue
  onChange: (value: CellValue) => void
  nullable?: boolean
  focus?: boolean
  disabled?: boolean
  inline?: boolean
  openPicker?: boolean
  onCalendarPick?: (value: CellValue) => void
  error?: string
}) {
  const { t } = useTranslation()
  const [validation, setValidation] = useState('')
  const [multiline, setMultiline] = useState(() => typeof value === 'string' && (value.length > 80 || value.includes('\n')))
  const inlineStyle = inline && 'rounded-none border-0 bg-transparent px-2 text-sm font-normal shadow-none focus-visible:ring-0 aria-invalid:ring-0 dark:bg-transparent dark:aria-invalid:ring-0'
  const message = validation || error
  const invalidProps = { 'aria-invalid': !!message, 'aria-describedby': message ? `${id}-error` : undefined }
  const feedback = message && <p id={`${id}-error`} role="alert"
    className={cn('text-xs wrap-anywhere text-destructive', inline ? 'px-2 pb-1' : 'mt-1')}>{message}</p>
  if (column.kind === 'boolean' || column.kind === 'select') {
    const items = column.kind === 'boolean'
      ? [{ value: true, label: t('dataset.valueTrue') }, { value: false, label: t('dataset.valueFalse') }]
      : column.options.map(option => ({ value: option, label: option }))
    const selected = items.findIndex(item => item.value === value)
    return <div className="min-w-0"><Select disabled={disabled} defaultOpen={openPicker} value={selected >= 0 ? String(selected) : nullable ? 'null' : ''} onValueChange={next => onChange(next === 'null' ? null : items[Number(next)].value)}>
      <SelectTrigger id={id} aria-label={label} className={cn('w-full', inlineStyle)} autoFocus={focus} {...invalidProps}><SelectValue placeholder={t('dataset.chooseValue')} /></SelectTrigger>
      <SelectContent>
        {nullable && <SelectItem value="null">{t('dataset.emptyValue')}</SelectItem>}
        {items.map((item, index) => <SelectItem key={String(item.value)} value={String(index)}>{item.label}</SelectItem>)}
      </SelectContent>
    </Select>{feedback}</div>
  }
  if (column.kind === 'text' && multiline) {
    return <div className="min-w-0">
      <Textarea id={id} aria-label={label} className={cn(inlineStyle)} value={String(value ?? '')} autoFocus={focus}
        required={!nullable} disabled={disabled} {...invalidProps} onChange={event => onChange(event.target.value)} />
      {nullable && <Button type="button" variant="ghost" size="sm" disabled={disabled}
        onClick={() => onChange(null)}>{t('dataset.clearValue')}</Button>}
      {feedback}
    </div>
  }
  const type = column.kind === 'datetime' ? 'datetime-local' : column.kind
  const inputValue = column.kind === 'datetime' && typeof value === 'string' ? localDatetime(value) : String(value ?? '')
  const calendarKind = column.kind === 'date' || column.kind === 'datetime' ? column.kind : undefined
  function change(next: string, numeric = 0, update = onChange) {
    if (column.kind === 'number') update(next === '' ? null : numeric)
    else if (column.kind === 'datetime') {
      const date = new Date(next)
      update(Number.isNaN(date.getTime()) ? null : date.toISOString())
    }
    else update(next === '' && column.kind !== 'text' ? null : next)
  }
  const clearable = column.kind === 'text' && nullable
  const grouped = calendarKind || clearable
  const Control = grouped ? InputGroupInput : Input
  const input = <Control id={id} type={type} aria-label={label} value={inputValue}
    className={cn(inlineStyle, calendarKind && 'min-w-0 [&::-webkit-calendar-picker-indicator]:hidden')}
    step={type === 'number' ? 'any' : type === 'datetime-local' ? '0.001' : undefined}
    min={type === 'number' ? Number.MIN_SAFE_INTEGER : undefined} max={type === 'number' ? Number.MAX_SAFE_INTEGER : undefined}
    maxLength={type === 'email' ? 254 : undefined} pattern={type === 'email' ? String.raw`[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+` : undefined}
    autoFocus={focus} disabled={disabled} required={!nullable}
    {...invalidProps}
    onBlur={event => {
      const input = event.currentTarget
      if (input.value || input.validity.badInput) input.checkValidity()
    }}
    onInvalid={event => {
      event.preventDefault()
      const validity = event.currentTarget.validity
      const formatError = column.kind === 'email' ? 'dataset.invalidEmail' : column.kind === 'number' ? 'dataset.invalidNumber'
        : calendarKind ? 'dataset.invalidDate' : 'dataset.invalidValue'
      setValidation(t(validity.badInput || !validity.valueMissing ? formatError : 'dataset.valueRequired'))
    }} onChange={event => {
      const input = event.currentTarget
      if (input.validity.valid) setValidation('')
      if (column.kind === 'text' && input.value.length > 80) setMultiline(true)
      change(input.value, input.valueAsNumber)
    }} />
  return <div className="min-w-0">
    {grouped ? <InputGroup className={cn(inline && 'rounded-none border-0 bg-transparent has-[[data-slot=input-group-control]:focus-visible]:ring-0 has-[[data-slot][aria-invalid=true]]:ring-0 dark:bg-transparent dark:has-[[data-slot][aria-invalid=true]]:ring-0')}>
      {input}
      {calendarKind ? <InputGroupAddon align="inline-end">
        <DatasetCalendar inputId={id} value={inputValue} nullable={nullable} kind={calendarKind} disabled={disabled} onPick={day => {
          setValidation('')
          change(day && column.kind === 'datetime' ? `${day}T${inputValue.slice(11) || '00:00'}` : day ?? '', 0, onCalendarPick)
        }} />
      </InputGroupAddon> : value !== null && !disabled && <InputGroupAddon align="inline-end">
        <InputGroupButton size="icon-xs" aria-label={t('dataset.clearValue')} onClick={() => {
          document.getElementById(id)?.focus()
          onChange(null)
        }}><X /></InputGroupButton>
      </InputGroupAddon>}
    </InputGroup> : input}
    {feedback}
  </div>
}

export function DatasetColumnFields({ column, onChange, existing }: {
  column: ColumnDraft
  onChange: (column: ColumnDraft) => void
  existing?: boolean
}) {
  const { t } = useTranslation()
  const id = useId()
  const options = fromDraft(column).options
  return <div className="grid gap-3 sm:grid-cols-2">
    <div className="space-y-1"><Label htmlFor={`${id}-label`}>{t('dataset.columnLabel')}</Label>
      <Input id={`${id}-label`} value={column.label} maxLength={120} required onChange={event => onChange({ ...column, label: event.target.value })} />
    </div>
    <div className="space-y-1"><Label htmlFor={`${id}-key`}>{t('dataset.fieldKey')}</Label>
      <Input id={`${id}-key`} value={column.key} pattern="[a-z][a-z0-9_]{0,62}" maxLength={63} required disabled={existing}
        className="disabled:pointer-events-auto disabled:cursor-not-allowed"
        onChange={event => onChange({ ...column, key: event.target.value })} />
    </div>
    <div className="space-y-1"><Label htmlFor={`${id}-kind`}>{t('dataset.columnType')}</Label>
      <Select value={column.kind} disabled={existing} onValueChange={kind => onChange({ ...column, kind: kind as DatasetKind, default: null, optionsText: '' })}>
        <SelectTrigger id={`${id}-kind`} className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>{datasetKinds.map(kind => <SelectItem value={kind} key={kind}><DatasetFieldIcon kind={kind} /><span>{t(`dataset.kind.${kind}`)}</span></SelectItem>)}</SelectContent>
      </Select>
    </div>
    <div className="space-y-1"><Label htmlFor={`${id}-default`}>{t('dataset.defaultValue')}</Label>
      <DatasetValueField id={`${id}-default`} label={t('dataset.defaultValue')} column={{ ...column, options }} value={column.default}
        onChange={value => onChange({ ...column, default: value })} nullable />
    </div>
    {column.kind === 'select' && <div className="space-y-1 sm:col-span-2">
      <Label htmlFor={`${id}-options`}>{t('dataset.options')}</Label>
      <Textarea id={`${id}-options`} required value={column.optionsText} onChange={event => onChange({ ...column, optionsText: event.target.value })} />
    </div>}
    <div className="space-y-1 sm:col-span-2">
      <div className="flex flex-wrap gap-4">
        <Label className={cn(existing && 'text-muted-foreground')}>
          <Checkbox checked={column.required} disabled={existing} aria-describedby={existing ? `${id}-required-help` : undefined}
            onCheckedChange={value => onChange({ ...column, required: value === true })} />{t('dataset.required')}
        </Label>
        <Label><Checkbox checked={column.unique} aria-describedby={existing ? `${id}-unique-help` : undefined}
          onCheckedChange={value => onChange({ ...column, unique: value === true })} />{t('dataset.unique')}</Label>
      </div>
      {!existing && column.required && <p className="text-xs text-muted-foreground">{t('dataset.requiredDefaultHelp')}</p>}
      {existing && <>
        <p id={`${id}-required-help`} className="text-xs text-muted-foreground">{t('dataset.requiredLocked')}</p>
        <p id={`${id}-unique-help`} className="text-xs text-muted-foreground">{t('dataset.uniqueLaterHelp')}</p>
      </>}
    </div>
  </div>
}
