import { useEffect, useId, useState } from 'react'
import { AlertTriangle, ExternalLink, Plus, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StateFieldPicker } from '@/components/state-field-action'
import { TemplateEditor } from '@/components/template-editor'
import type { Field } from '@/components/editor/meta'
import { api } from '@/lib/api'
import {
  DATASET_QUERY_LIMIT, datasetOperations, datasetUrl, datasetWriteOperation, type CellValue,
  type DatasetColumn, type DatasetNodeConfig, type DatasetOperation, type DatasetPage,
  type DatasetSummary,
} from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetValueField } from './dataset-fields'

import type { BindingLookup } from './use-dataset-node-binding'

type Patch = (patch: Partial<DatasetNodeConfig>) => void

const keyPresent = (columns: DatasetColumn[], key: string) => columns.some(column => column.key === key)

export function DatasetNodeSettings({ data, binding, disabled, onChange }: {
  data: DatasetNodeConfig; binding: BindingLookup | null; disabled: boolean; onChange: Patch
}) {
  const { t } = useTranslation()
  const id = useId()
  const [catalog, setCatalog] = useState<DatasetPage<DatasetSummary> | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    let active = true
    api<DatasetPage<DatasetSummary>>(datasetUrl()).then(page => { if (active) setCatalog(page) })
      .catch(failure => { if (active) setError(failure.message) })
    return () => { active = false }
  }, [])
  async function more() {
    if (catalog?.next_offset == null || loading) return
    setLoading(true)
    setError('')
    try {
      const next = await api<DatasetPage<DatasetSummary>>(`${datasetUrl()}?offset=${catalog.next_offset}`)
      setCatalog({ ...next, items: [...catalog.items, ...next.items] })
    } catch (failure) { setError((failure as Error).message) }
    finally { setLoading(false) }
  }
  const permission = datasetWriteOperation(data.operation) ? 'write' : 'read'
  const missingGrant = binding?.permission !== undefined && binding.permission !== 'read_write' && binding.permission !== permission
  const orphaned = data.dataset_id && !catalog?.items.some(item => item.id === data.dataset_id)
  return <div className="space-y-3">
    <div className="space-y-1.5">
      <Label htmlFor={`${id}-dataset`}>{t('datasetNode.dataset')}</Label>
      <Select value={data.dataset_id || ''} onValueChange={dataset_id => onChange({ dataset_id })} disabled={disabled}>
        <SelectTrigger id={`${id}-dataset`} className="w-full"><SelectValue placeholder={t('datasetNode.chooseDataset')} /></SelectTrigger>
        <SelectContent emptyMessage={error || (catalog === null ? t('common.loading') : t('dataset.noDatasets'))}>
          {orphaned && <SelectItem value={data.dataset_id!} disabled={!binding?.dataset}>{binding?.dataset?.name ?? t('datasetNode.unavailable')}</SelectItem>}
          {catalog?.items.map(item => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
        </SelectContent>
      </Select>
      {catalog?.next_offset != null && <Button variant="ghost" size="sm" disabled={loading} onClick={() => void more()}>{t('dataset.moreDatasets')}</Button>}
    </div>
    <div className="space-y-1.5">
      <Label htmlFor={`${id}-operation`}>{t('datasetNode.operation')}</Label>
      <Select value={data.operation || 'find_rows'} disabled={disabled} onValueChange={value => {
        const operation = value as DatasetOperation
        onChange({ operation, arguments: operation === 'find_rows' ? { limit: 10, filters: [] } : operation === 'get_row' ? { row_id: '' } : { values: {} } })
      }}>
        <SelectTrigger id={`${id}-operation`} className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>{datasetOperations.map(operation =>
          <SelectItem key={operation} value={operation}>{t(`datasetNode.operations.${operation}`)}</SelectItem>)}</SelectContent>
      </Select>
    </div>
    {!data.dataset_id && <Alert variant="warning"><AlertTriangle /><AlertDescription>{t('datasetNode.rebind')}</AlertDescription></Alert>}
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    {binding?.error && <Alert variant="destructive"><AlertDescription>{binding.error} {t('datasetNode.rebind')}</AlertDescription></Alert>}
    {binding?.dataset && !binding.workflowId && <p className="text-xs text-muted-foreground">{t('datasetNode.saveForGrant')}</p>}
    {binding?.grantError && <Alert variant="warning"><AlertTriangle /><AlertDescription>{binding.grantError}</AlertDescription></Alert>}
    {missingGrant && <Alert variant="warning"><AlertTriangle /><AlertDescription>{t(`datasetNode.grantMissing.${permission}`)}</AlertDescription></Alert>}
    {binding?.dataset && <Button variant="outline" size="sm" asChild>
      <Link to={`/datasets/${encodeURIComponent(binding.dataset.id)}`} target="_blank" rel="noopener"><ExternalLink />{t('datasetNode.openDataset')}</Link>
    </Button>}
  </div>
}

function ColumnSelect({ id, value, columns, onChange, disabled }: {
  id: string; value?: string; columns: DatasetColumn[]; onChange: (value: string) => void; disabled: boolean
}) {
  const { t } = useTranslation()
  return <Select value={value || ''} disabled={disabled} onValueChange={onChange}>
    <SelectTrigger id={id} className="w-full min-w-0"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
    <SelectContent>{columns.map(column => <SelectItem key={column.key} value={column.key}>
      <DatasetFieldIcon kind={column.kind} /><span className="truncate">{column.label}</span>
    </SelectItem>)}</SelectContent>
  </Select>
}

function MappedValue({ label, column, value, fields, disabled, onChange, substring }: {
  label: string; column: DatasetColumn; value: CellValue; fields: Field[]; disabled: boolean; onChange: (value: CellValue) => void; substring?: boolean
}) {
  const { t } = useTranslation()
  const id = useId()
  const [mode, setMode] = useState(() => typeof value === 'string' && value.includes('{{') ? 'template' : 'literal')
  return <div className="space-y-1.5">
    <Select value={mode} disabled={disabled} onValueChange={next => { setMode(next); onChange(next === 'template' ? '' : null) }}>
      <SelectTrigger aria-label={t('datasetNode.mappingMode', { label })} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="literal">{t('datasetNode.literal')}</SelectItem>
        <SelectItem value="template">{t('datasetNode.template')}</SelectItem>
      </SelectContent>
    </Select>
    {mode === 'template'
      ? <TemplateEditor id={id} fields={fields} readOnly={disabled} singleLine placeholder={t('template.placeholder', { open: '{{' })}
          value={typeof value === 'string' ? value : ''} onChange={onChange} />
      : substring ? <Input id={id} aria-label={label} disabled={disabled} maxLength={120}
          value={typeof value === 'string' ? value : ''} onChange={event => onChange(event.target.value)} />
      : <DatasetValueField id={id} label={label} column={column} value={value} nullable disabled={disabled} onChange={onChange} />}
  </div>
}

export function DatasetNodeData({ data, binding, state, disabled, onChange }: {
  data: DatasetNodeConfig; binding: BindingLookup | null; state: Field[]; disabled: boolean; onChange: Patch
}) {
  const { t } = useTranslation()
  const id = useId()
  const dataset = binding?.dataset
  const columns = dataset?.columns ?? []
  const args = data.arguments ?? {}
  const operation = data.operation ?? 'find_rows'
  const fields = data.fields ?? []
  const values = args.values ?? {}
  const filters = args.filters ?? []
  const sorts = args.sorts ?? []
  const patchArgs = (patch: DatasetNodeConfig['arguments']) => onChange({ arguments: { ...args, ...patch } })
  const referenced = [...new Set([...fields, ...Object.keys(values), ...filters.map(rule => rule.field), ...sorts.map(rule => rule.field), args.key ?? ''])]
  const missing = referenced.filter(key => key && !keyPresent(columns, key))
  const invalidKey = operation === 'upsert_row' && !!args.key && !columns.some(column => column.key === args.key && column.unique)
  const availableOutputFields = state.filter(field => field.type === 'object').map(field => field.name)

  return <div className="space-y-3">
    {!dataset ? <p className="text-sm text-muted-foreground">{data.dataset_id && !binding ? t('common.loading') : t('datasetNode.chooseFirst')}</p> : <>
      {missing.length > 0 && <Alert variant="warning"><AlertTriangle /><AlertDescription>
        {t('datasetNode.missingFields', { fields: missing.join(', ') })}
        {!disabled && <Button size="sm" variant="outline" onClick={() => onChange({
          fields: fields.filter(field => !missing.includes(field)),
          arguments: {
            ...args,
            ...(args.values ? { values: Object.fromEntries(Object.entries(values).filter(([field]) => !missing.includes(field))) } : {}),
            ...(args.filters ? { filters: filters.filter(rule => !missing.includes(rule.field)) } : {}),
            ...(args.sorts ? { sorts: sorts.filter(rule => !missing.includes(rule.field)) } : {}),
            ...(args.key && missing.includes(args.key) ? { key: '' } : {}),
          },
        })}>{t('datasetNode.removeMissing')}</Button>}
      </AlertDescription></Alert>}
      {operation === 'get_row' && <div className="space-y-1.5">
        <Label htmlFor={`${id}-row`}>{t('dataset.rowId')}</Label>
        <TemplateEditor id={`${id}-row`} singleLine fields={state} value={args.row_id ?? ''} readOnly={disabled}
          placeholder={t('template.placeholder', { open: '{{' })} onChange={row_id => patchArgs({ row_id })} />
      </div>}
      {operation === 'find_rows' && <div className="space-y-2">
        <Label htmlFor={`${id}-limit`}>{t('datasetNode.maxRows')}</Label>
        <Input id={`${id}-limit`} type="number" min={1} max={100} disabled={disabled} value={args.limit ?? 10}
          onChange={event => patchArgs({ limit: Math.max(1, Math.min(100, Number(event.target.value) || 10)) })} />
        <div className="space-y-1.5">
          <Label htmlFor={`${id}-match`}>{t('dataset.filterMatch')}</Label>
          <Select value={args.filter_mode ?? 'and'} disabled={disabled} onValueChange={value => patchArgs({ filter_mode: value === 'or' ? 'or' : 'and' })}>
            <SelectTrigger id={`${id}-match`} className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="and">{t('dataset.filterMatchAll')}</SelectItem>
              <SelectItem value="or">{t('dataset.filterMatchAny')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {filters.map((rule, index) => {
          const column = columns.find(item => item.key === rule.field)
          const replace = (patch: Partial<typeof rule>) => patchArgs({ filters: filters.map((item, position) => position === index ? { ...item, ...patch } : item) })
          const ops = column?.kind === 'boolean' ? ['eq', 'ne', 'is_null', 'not_null'] : ['eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'is_null', 'not_null']
          if (column && ['text', 'email', 'select'].includes(column.kind)) ops.push('contains')
          return <fieldset className="space-y-2 rounded-md border p-2" key={index}>
            <legend className="px-1 text-xs">{t('dataset.filterCondition', { number: index + 1 })}</legend>
            <div className="flex items-center gap-1">
              <div className="min-w-0 flex-1">
                <Label htmlFor={`${id}-filter-${index}`} className="sr-only">{t('dataset.filterColumn')}</Label>
                <ColumnSelect id={`${id}-filter-${index}`} columns={columns} value={rule.field} disabled={disabled}
                  onChange={field => replace({ field, op: 'eq', value: null })} />
              </div>
              <Button variant="ghost" size="icon" disabled={disabled} aria-label={t('dataset.removeFilterCondition')}
                onClick={() => patchArgs({ filters: filters.filter((_, position) => position !== index) })}><X /></Button>
            </div>
            <Select value={rule.op} disabled={disabled || !column} onValueChange={op => replace({ op, value: null })}>
              <SelectTrigger aria-label={t('dataset.filterOperator')} className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>{ops.map(op => <SelectItem key={op} value={op}>{t(`datasetNode.filterOps.${op}`)}</SelectItem>)}</SelectContent>
            </Select>
            {column && !['is_null', 'not_null'].includes(rule.op) && <MappedValue key={rule.field} label={t('dataset.filterValue')}
              column={column} value={rule.value} fields={state} disabled={disabled} substring={rule.op === 'contains'} onChange={value => replace({ value })} />}
          </fieldset>
        })}
        <Button variant="outline" size="sm" disabled={disabled || !columns.length || filters.length >= DATASET_QUERY_LIMIT}
          onClick={() => patchArgs({ filters: [...filters, { field: columns[0].key, op: 'eq', value: null }] })}><Plus />{t('dataset.addFilterCondition')}</Button>
      </div>}
      {operation === 'upsert_row' && <div className="space-y-1.5">
        <Label htmlFor={`${id}-key`}>{t('datasetNode.upsertKey')}</Label>
        <ColumnSelect id={`${id}-key`} columns={columns.filter(column => column.unique)} value={args.key} disabled={disabled}
          onChange={key => patchArgs({ key, values: { ...values, [key]: values[key] ?? null } })} />
        {(!columns.some(column => column.unique) || invalidKey) && <Alert variant="warning"><AlertTriangle />
          <AlertDescription>{t('datasetNode.uniqueRequired')}</AlertDescription></Alert>}
      </div>}
      {datasetWriteOperation(operation) && <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t('datasetNode.mappedFields')}</legend>
        {columns.map(column => {
          const mapped = Object.hasOwn(values, column.key)
          return <div key={column.key} className="space-y-2 rounded-md border p-2">
            <Label className="gap-1.5"><Checkbox checked={mapped} disabled={disabled || (operation === 'upsert_row' && args.key === column.key)} onCheckedChange={checked => {
              const next = { ...values }
              if (checked) next[column.key] = null
              else delete next[column.key]
              patchArgs({ values: next })
            }} /><DatasetFieldIcon kind={column.kind} />{column.label}</Label>
            {mapped && <MappedValue label={column.label} column={column} value={values[column.key]} fields={state}
              disabled={disabled} onChange={value => patchArgs({ values: { ...values, [column.key]: value } })} />}
          </div>
        })}
      </fieldset>}
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t('datasetNode.returnFields')}</legend>
        {columns.map(column => <Label key={column.key} className="gap-1.5">
          <Checkbox checked={fields.includes(column.key)} disabled={disabled} onCheckedChange={checked =>
            onChange({ fields: checked ? [...fields, column.key] : fields.filter(field => field !== column.key) })} />
          <DatasetFieldIcon kind={column.kind} />{column.label}
        </Label>)}
      </fieldset>
    </>}
    <div className="space-y-1.5">
      <Label htmlFor={`${id}-output`}>{t('field.outputField')}</Label>
      <StateFieldPicker id={`${id}-output`} value={data.output_field} options={availableOutputFields} types={['object']}
        disabled={disabled} onChange={output_field => onChange({ output_field })} />
    </div>
    <p className="text-xs text-muted-foreground">{t('datasetNode.dryRun')}</p>
  </div>
}
