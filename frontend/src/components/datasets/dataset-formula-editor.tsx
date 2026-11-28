import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { datasetFormulaError, datasetFormulaInputKinds, datasetUrl, displayColumnValue, fromDraft, type CellValue, type ColumnDraft, type Dataset, type DatasetRow, type DatasetRowPage } from '@/lib/datasets'
import { DatasetValueField } from './dataset-fields'

type Result = { value: CellValue; error: string | null; inputs: string[] }
type Preview = { key: string; result?: Result; message?: string }

export function DatasetFormulaEditor({ dataset, column, onChange, saveError }: {
  dataset: Dataset
  column: ColumnDraft
  onChange: (next: ColumnDraft) => void
  saveError?: string
}) {
  const { t } = useTranslation()
  const id = useId()
  const expression = column.formula?.expression ?? ''
  const disabled = !dataset.formula_config_enabled
  const textarea = useRef<HTMLTextAreaElement>(null)
  const restoreCursor = useRef<number | null>(null)
  const request = useRef<AbortController | null>(null)
  const [rows, setRows] = useState<DatasetRow[] | null>(null)
  const [loadError, setLoadError] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [sample, setSample] = useState<Record<string, CellValue>>({})
  const [sampleSchema, setSampleSchema] = useState<{ expression: string; keys: string[] } | null>(null)
  const sampleInputs = sampleSchema?.expression === expression ? sampleSchema.keys : []
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<Preview | null>(null)
  const rowId = selected ?? rows?.[0]?.id ?? null
  const signature = (row: string | null) => JSON.stringify([fromDraft(column), row, sample])
  const shown = preview?.key === signature(rowId) ? preview : null
  const message = saveError || shown?.message
  const canPreview = !disabled && rows !== null && !!column.label.trim() && /^[a-z][a-z0-9_]{0,62}$/.test(column.key) && !!expression.trim()
  const eligible = dataset.columns.filter(field => field.key !== column.key &&
    datasetFormulaInputKinds.some(kind => kind === field.kind))

  const titleKey = dataset.columns.find(field => field.kind === 'text' && !field.formula)?.key
  const numberKey = dataset.columns.find(field => field.kind === 'auto_number')?.key

  useEffect(() => {
    if (disabled) return
    const controller = new AbortController()
    api<DatasetRowPage>(datasetUrl(dataset.id) + '/rows/query', {
      method: 'POST', json: { limit: 20, fields: [numberKey, titleKey].filter(key => key !== undefined) },
      signal: controller.signal,
    }).then(page => {
      if (controller.signal.aborted) return
      if (page.schema_revision === dataset.revision) {
        setRows(page.items)
        setLoadError('')
      } else {
        setLoadError(t('errors.DATASET_SCHEMA_CONFLICT'))
      }
    }).catch(failure => {
      if (!controller.signal.aborted) setLoadError(failure.message)
    })
    return () => { controller.abort(); request.current?.abort() }
  }, [dataset.id, dataset.revision, disabled, numberKey, titleKey, t])

  useEffect(() => { if (saveError) textarea.current?.focus() }, [saveError])

  function setExpression(next: string) {
    onChange({ ...column, formula: { version: 1, expression: next } })
  }

  function insertField(key: string) {
    const start = textarea.current?.selectionStart ?? expression.length
    const end = textarea.current?.selectionEnd ?? start
    const reference = '[' + key + ']'
    const next = expression.slice(0, start) + reference + expression.slice(end)
    if (next.length > 1024) return
    restoreCursor.current = start + reference.length
    setExpression(next)
  }

  async function calculate(row = rowId) {
    if (!canPreview) return
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    const key = signature(row)
    setBusy(true)
    try {
      const result = await api<Result>(datasetUrl(dataset.id) + '/columns/formula/preview', {
        method: 'POST', signal: controller.signal,
        json: { revision: dataset.revision, column: fromDraft(column), row_id: row,
          sample: row === null ? Object.fromEntries(Object.entries(sample).filter(([name]) => sampleInputs.includes(name))) : {} },
      })
      if (controller.signal.aborted) return
      setSampleSchema({ expression, keys: result.inputs })
      setPreview({ key, result })
    } catch (failure) {
      if (controller.signal.aborted) return
      const details = failure instanceof ApiError && failure.code === 'DATASET_FORMULA_INVALID' ? failure.details : undefined
      setPreview({ key, message: details?.reason ? datasetFormulaError(details.reason, details) :
        failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR') })
    } finally {
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  const previewText = shown?.result &&
    (shown.result.error ? datasetFormulaError(shown.result.error) : shown.result.value === null
      ? t('dataset.formula.emptyResult') : displayColumnValue(shown.result.value, column, t('dataset.valueTrue'), t('dataset.valueFalse')))

  return <div className="space-y-3 sm:col-span-2">
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>{t('dataset.formula.expression')}</Label>
        <DropdownMenu>
          <DropdownMenuTrigger asChild><Button type="button" variant="ghost" size="sm" disabled={disabled || !eligible.length}>
            <Plus />{t('dataset.formula.insertField')}
          </Button></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="max-h-64 max-w-72 overflow-auto" onCloseAutoFocus={event => {
            if (restoreCursor.current === null) return
            event.preventDefault()
            const cursor = restoreCursor.current
            restoreCursor.current = null
            requestAnimationFrame(() => {
              textarea.current?.focus()
              textarea.current?.setSelectionRange(cursor, cursor)
            })
          }}>
            {eligible.map(field => <DropdownMenuItem key={field.key} onSelect={() => insertField(field.key)}>
              <span className="min-w-0 truncate">{field.label}</span>
              <code className="ml-auto text-xs text-muted-foreground">{field.key}</code>
            </DropdownMenuItem>)}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <Textarea id={id} ref={textarea} value={expression} disabled={disabled} required maxLength={1024}
        spellCheck={false} rows={2} className="font-mono" aria-invalid={!!message}
        aria-describedby={message ? id + '-error' : undefined}
        onChange={event => setExpression(event.target.value)}
        onBlur={() => { if (!shown) void calculate() }} />
      {message && <p role="alert" id={id + '-error'} className="text-xs text-destructive">{message}</p>}
    </div>
    {!disabled && <div className="space-y-3 rounded-lg border bg-muted/50 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" size="sm" disabled={!canPreview || busy} onClick={() => void calculate()}>
          {t('dataset.formula.preview')}
        </Button>
        {!!rows?.length && <Select value={rowId ?? undefined} onValueChange={value => { setSelected(value); void calculate(value) }}>
          <SelectTrigger size="sm" className="min-w-0 flex-1" aria-label={t('dataset.formula.previewRow')}><SelectValue /></SelectTrigger>
          <SelectContent>{rows.map(row => {
            const number = numberKey && row.values[numberKey]
            const title = titleKey && row.values[titleKey]
            return <SelectItem key={row.id} value={row.id}>
              {typeof number === 'number' ? '#' + number : row.id.slice(0, 8)}
              {typeof title === 'string' && title ? ' · ' + title : ''}
            </SelectItem>
          })}</SelectContent>
        </Select>}
      </div>
      {rows?.length === 0 && !!sampleInputs.length && <fieldset className="grid gap-2 sm:grid-cols-2">
        <legend className="pb-1 text-xs text-muted-foreground">{t('dataset.formula.sampleInputs')}</legend>
        {dataset.columns.filter(field => sampleInputs.includes(field.key)).map(field => {
          const inputId = id + '-sample-' + field.key
          return <div className="space-y-1" key={field.key}>
            <Label htmlFor={inputId}>{field.label}</Label>
            <DatasetValueField id={inputId} label={field.label} column={{ ...field, required: false }}
              value={Object.hasOwn(sample, field.key) ? sample[field.key] : field.default} nullable
              onChange={value => setSample(previous => ({ ...previous, [field.key]: value }))} />
          </div>
        })}
      </fieldset>}
      <output role="status" className={cn('block text-sm text-muted-foreground',
        (shown?.result?.error || loadError) && 'text-destructive',
        !busy && shown?.result && !shown.result.error && shown.result.value !== null && 'text-right text-lg font-semibold tabular-nums text-foreground')}>
        {loadError || (busy || rows === null ? t('common.loading') : previewText || t('dataset.formula.previewHint'))}
      </output>
    </div>}
  </div>
}
