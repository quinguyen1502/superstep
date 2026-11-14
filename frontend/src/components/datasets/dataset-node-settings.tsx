import { useId, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StateFieldPicker } from '@/components/state-field-action'
import { TemplateEditor } from '@/components/template-editor'
import type { Field } from '@/components/editor/meta'
import {
  DATASET_QUERY_LIMIT, datasetFilterRules, datasetListFilter, datasetSubstringFilter, keepDatasetFilterFields, datasetNodePermission, datasetOperations, datasetWriteOperation, type CellValue,
  type DatasetColumn, type DatasetFilters, type DatasetNodeConfig, type DatasetOperation,
} from '@/lib/datasets'
import { DatasetFilterBuilder } from './dataset-filter-builder'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetValueField } from './dataset-fields'
import { DatasetBindingNotice, DatasetPicker } from './dataset-picker'

import type { BindingLookup } from './use-dataset-node-binding'

type Patch = (patch: Partial<DatasetNodeConfig>) => void

const keyPresent = (columns: DatasetColumn[], key: string) => columns.some(column => column.key === key)
// Delete returns only the row id, but the binding still names one schema field to validate against.
const deleteFields = (fields: string[] | undefined, columns: DatasetColumn[], preferred?: string) => {
  if (!columns.length) return fields ?? []
  const kept = (fields ?? []).filter(field => keyPresent(columns, field))
  return kept.length ? kept : preferred ? [preferred] : columns.slice(0, 1).map(column => column.key)
}

function defaultArguments(operation: DatasetOperation): DatasetNodeConfig['arguments'] {
  if (operation === 'find_rows') return { limit: 10, filters: [] }
  if (operation === 'get_row' || operation === 'delete_row') return { row_id: '' }
  return { values: {} }
}

export function DatasetNodeSettings({ data, binding, disabled, onChange }: {
  data: DatasetNodeConfig; binding: BindingLookup | null; disabled: boolean; onChange: Patch
}) {
  const { t } = useTranslation()
  const id = useId()
  const permission = datasetNodePermission(data.operation)
  return <div className="space-y-3">
    <DatasetPicker id={`${id}-dataset`} value={data.dataset_id} binding={binding} disabled={disabled} onChange={dataset_id => onChange({ dataset_id })} />
    <div className="space-y-1.5">
      <Label htmlFor={`${id}-operation`}>{t('datasetNode.operation')}</Label>
      <Select value={data.operation || 'find_rows'} disabled={disabled} onValueChange={value => {
        const operation = value as DatasetOperation
        onChange({
          operation, arguments: defaultArguments(operation),
          ...(operation === 'delete_row' ? { fields: deleteFields(data.fields, binding?.dataset?.columns ?? []) } : {}),
          // A write-only grant gets identifiers back, so a new write starts without returned fields.
          ...(datasetWriteOperation(operation) && binding?.permission === 'write' ? { fields: [] } : {}),
        })
      }}>
        <SelectTrigger id={`${id}-operation`} className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>{datasetOperations.map(operation =>
          <SelectItem key={operation} value={operation}>{t(`datasetNode.operations.${operation}`)}</SelectItem>)}</SelectContent>
      </Select>
    </div>
    <DatasetBindingNotice value={data.dataset_id} binding={binding} permission={permission} />
  </div>
}

export function ColumnSelect({ id, value, columns, onChange, disabled }: {
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

function MappedValue({ label, column, value, fields, disabled, onChange, substring, nullable = true }: {
  label: string; column: DatasetColumn; value: CellValue; fields: Field[]; disabled: boolean; onChange: (value: CellValue) => void; substring?: boolean; nullable?: boolean
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
      : <DatasetValueField id={id} label={label} column={column} value={value} nullable={nullable} disabled={disabled} onChange={onChange} />}
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
  const filterTree: DatasetFilters = args.filter_tree ?? {
    type: 'group', conjunction: args.filter_mode ?? 'and',
    children: (args.filters ?? []).map(rule => ({ type: 'rule', ...rule })),
  }
  const sorts = args.sorts ?? []
  const patchArgs = (patch: DatasetNodeConfig['arguments']) => onChange({ arguments: { ...args, ...patch } })
  function filterArguments(tree: DatasetFilters): DatasetNodeConfig['arguments'] {
    const useTree = tree.children.length > 0 && (args.filter_tree || tree.children.length > DATASET_QUERY_LIMIT
      || tree.children.some(child => child.type === 'group' || child.op === 'not_contains' || datasetListFilter(child.op)))
    if (useTree) return { filters: undefined, filter_mode: undefined, filter_tree: tree }
    return {
      filter_tree: undefined, filter_mode: tree.conjunction,
      filters: datasetFilterRules(tree).map(({ field, op, value }) => ({ field, op, value: Array.isArray(value) ? null : value })),
    }
  }
  const referenced = [...new Set([...fields, ...Object.keys(values), ...datasetFilterRules(filterTree).map(rule => rule.field), ...sorts.map(rule => rule.field), args.key ?? ''])]
  const missing = referenced.filter(key => key && !keyPresent(columns, key))
  const deleting = operation === 'delete_row'
  const writing = datasetWriteOperation(operation)
  const writeOnly = writing && binding?.permission === 'write'
  const invalidKey = (operation === 'upsert_row' || deleting) && !!args.key && !columns.some(column => column.key === args.key && column.unique)
  const uniqueColumns = columns.filter(column => column.unique)
  const deleteMode = deleting && 'key' in args ? 'key' : 'row_id'
  const deleteColumn = deleting ? columns.find(column => column.key === args.key) : undefined
  const missingTarget = deleting && (deleteMode === 'row_id'
    ? !(args.row_id ?? '').trim()
    : !args.key || args.value === null || args.value === undefined || args.value === '')
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
            ...((args.filters || args.filter_tree) ? filterArguments(keepDatasetFilterFields(filterTree, new Set(columns.map(column => column.key)))) : {}),
            ...(args.sorts ? { sorts: sorts.filter(rule => !missing.includes(rule.field)) } : {}),
            ...(args.key && missing.includes(args.key) ? { key: '' } : {}),
          },
          ...(deleting ? { fields: deleteFields(fields.filter(field => !missing.includes(field)), columns) } : {}),
        })}>{t('datasetNode.removeMissing')}</Button>}
      </AlertDescription></Alert>}
      {operation === 'get_row' && <div className="space-y-1.5">
        <Label htmlFor={`${id}-row`}>{t('dataset.rowId')}</Label>
        <TemplateEditor id={`${id}-row`} singleLine fields={state} value={args.row_id ?? ''} readOnly={disabled}
          placeholder={t('template.placeholder', { open: '{{' })} onChange={row_id => patchArgs({ row_id })} />
      </div>}
      {deleting && <div className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor={`${id}-delete-mode`}>{t('datasetNode.deleteBy')}</Label>
          <Select value={deleteMode} disabled={disabled} onValueChange={mode => {
            const key = uniqueColumns[0]?.key ?? ''
            onChange(mode === 'key'
              ? { arguments: { key, value: null }, fields: deleteFields(fields, columns, key || undefined) }
              : { arguments: { row_id: '' }, fields: deleteFields(fields, columns) })
          }}>
            <SelectTrigger id={`${id}-delete-mode`} className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="row_id">{t('datasetNode.deleteModes.row_id')}</SelectItem>
              <SelectItem value="key">{t('datasetNode.deleteModes.key')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {deleteMode === 'row_id' ? <div className="space-y-1.5">
          <Label htmlFor={`${id}-delete-row`}>{t('dataset.rowId')}</Label>
          <TemplateEditor id={`${id}-delete-row`} singleLine fields={state} value={args.row_id ?? ''} readOnly={disabled}
            placeholder={t('template.placeholder', { open: '{{' })} onChange={row_id => onChange({ arguments: { row_id } })} />
        </div> : <>
          <div className="space-y-1.5">
            <Label htmlFor={`${id}-delete-key`}>{t('datasetNode.deleteKey')}</Label>
            <ColumnSelect id={`${id}-delete-key`} columns={uniqueColumns} value={args.key} disabled={disabled}
              onChange={key => onChange({ arguments: { key, value: null }, fields: deleteFields(fields, columns, key) })} />
          </div>
          {deleteColumn?.unique && <MappedValue key={deleteColumn.key} label={t('datasetNode.deleteValue', { label: deleteColumn.label })}
            column={deleteColumn} value={args.value ?? null} fields={state} disabled={disabled}
            onChange={value => onChange({ arguments: { key: args.key, value } })} />}
          {(!uniqueColumns.length || invalidKey) && <Alert variant="warning"><AlertTriangle />
            <AlertDescription>{t('datasetNode.deleteUniqueRequired')}</AlertDescription></Alert>}
        </>}
        {missingTarget && <Alert variant="warning"><AlertTriangle /><AlertDescription>{t('datasetNode.deleteTargetMissing')}</AlertDescription></Alert>}
        <p className="text-xs text-muted-foreground">{t('datasetNode.deleteResult')}</p>
      </div>}
      {operation === 'find_rows' && <div className="space-y-2">
        <Label htmlFor={`${id}-limit`}>{t('datasetNode.maxRows')}</Label>
        <Input id={`${id}-limit`} type="number" min={1} max={100} disabled={disabled} value={args.limit ?? 10}
          onChange={event => patchArgs({ limit: Math.max(1, Math.min(100, Number(event.target.value) || 10)) })} />
        <DatasetFilterBuilder tree={filterTree} columns={columns} disabled={disabled}
          onChange={tree => patchArgs(filterArguments(tree))}
          renderValue={({ label, column, value, onChange, op }) => <MappedValue label={label} column={column}
            value={value} fields={state} disabled={disabled} onChange={onChange} substring={datasetSubstringFilter(op)} nullable={false} />} />
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
      {writeOnly ? <div className="space-y-2" data-testid="dataset-write-only-result">
        <p className="text-xs text-muted-foreground">{t('datasetNode.writeOnlyResult')}</p>
        {fields.length > 0 && <Alert variant="warning"><AlertTriangle /><AlertDescription>
          {t('datasetNode.writeOnlyFields')}
          {!disabled && <Button size="sm" variant="outline" onClick={() => onChange({ fields: [] })}>{t('datasetNode.returnIdentifiersOnly')}</Button>}
        </AlertDescription></Alert>}
      </div> : !deleting && <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t('datasetNode.returnFields')}</legend>
        {columns.map(column => <Label key={column.key} className="gap-1.5">
          <Checkbox checked={fields.includes(column.key)} disabled={disabled} onCheckedChange={checked =>
            onChange({ fields: checked ? [...fields, column.key] : fields.filter(field => field !== column.key) })} />
          <DatasetFieldIcon kind={column.kind} />{column.label}
        </Label>)}
        {writing && !fields.length && <p className="text-xs text-muted-foreground">{t('datasetNode.identifiersOnly')}</p>}
      </fieldset>}
    </>}
    <div className="space-y-1.5">
      <Label htmlFor={`${id}-output`}>{t('field.outputField')}</Label>
      <StateFieldPicker id={`${id}-output`} value={data.output_field} options={availableOutputFields} types={['object']}
        disabled={disabled} onChange={output_field => onChange({ output_field })} />
    </div>
    <p className="text-xs text-muted-foreground">{t('datasetNode.dryRun')}</p>
  </div>
}
