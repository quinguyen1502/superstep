import { AlertTriangle, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { AgentTool } from '@/lib/agent'
import { DATASET_AGENT_MAX_ROWS, datasetAgentOperations, datasetFilterOperators, datasetReadOnly, type DatasetAgentOperation } from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { ColumnSelect } from './dataset-node-settings'
import { DatasetBindingNotice, DatasetPicker } from './dataset-picker'
import { useDatasetNodeBinding } from './use-dataset-node-binding'

export function DatasetAgentSettings({ id, tool, wid, disabled, onChange }: {
  id: string; tool: AgentTool; wid?: string; disabled?: boolean; onChange: (patch: Partial<AgentTool>) => void
}) {
  const { t } = useTranslation()
  const binding = useDatasetNodeBinding(tool.dataset_id, wid)
  const columns = binding?.dataset?.columns
  const operations: DatasetAgentOperation[] = tool.operations?.length ? tool.operations : ['find_rows']
  const finds = operations.includes('find_rows')
  const aggregates = operations.includes('aggregate_rows')
  const upserts = operations.includes('upsert_row')
  const writes = upserts || operations.includes('insert_row')
  const fields = tool.fields ?? []
  const writeFields = tool.write_fields ?? []
  const filterOps = tool.filter_ops ?? {}
  const known = (field: string) => !!columns?.some(column => column.key === field)
  const validFields = fields.filter(known)
  const validWriteFields = writeFields.filter(known)
  const uniqueColumns = (columns ?? []).filter(column => column.unique)
  const keyValid = !upserts || uniqueColumns.some(column => column.key === tool.key)
  const validFilters = Object.fromEntries((columns ?? []).flatMap(column => {
    const allowed = (filterOps[column.key] ?? []).filter(op => datasetFilterOperators(column.kind).includes(op))
    return allowed.length ? [[column.key, allowed]] : []
  }))
  const outdated = columns && (validFields.length !== fields.length || (writes && validWriteFields.length !== writeFields.length)
    || (upserts && !!tool.key && !keyValid)
    || Object.entries(filterOps).some(([field, ops]) => ops.length !== validFilters[field]?.length))
  const permission = (finds || aggregates) && writes ? 'read_write' : writes ? 'write' : 'read'

  function toggleOperator(field: string, operator: string, checked: boolean) {
    const current = filterOps[field] ?? []
    const next = { ...filterOps }
    const selected = checked ? [...current, operator] : current.filter(op => op !== operator)
    if (selected.length) next[field] = selected
    else delete next[field]
    onChange({ filter_ops: next })
  }

  function toggleOperation(operation: DatasetAgentOperation, checked: boolean) {
    const next = datasetAgentOperations.filter(op => op === operation ? checked : operations.includes(op))
    if (!next.length) return
    const patch: Partial<AgentTool> = { operations: next }
    if (!next.includes('upsert_row')) patch.key = undefined
    if (!next.some(op => op === 'insert_row' || op === 'upsert_row')) patch.write_fields = undefined
    onChange(patch)
  }

  return <div className="space-y-3">
    <DatasetPicker id={`${id}-dataset`} value={tool.dataset_id} binding={binding} disabled={disabled}
      onChange={dataset_id => onChange({ dataset_id })} />
    <DatasetBindingNotice value={tool.dataset_id} binding={binding} permission={permission} />
    <fieldset className="space-y-2">
      <legend className="mb-2 text-sm font-medium">{t('datasetTool.operations')}</legend>
      {datasetAgentOperations.map(operation => <Label key={operation} className="gap-1.5">
        <Checkbox checked={operations.includes(operation)} disabled={disabled || (operations.length === 1 && operations[0] === operation)}
          onCheckedChange={checked => toggleOperation(operation, checked === true)} />
        {t(`datasetNode.operations.${operation}`)}
      </Label>)}
      <p className="text-xs text-muted-foreground">{t(writes ? 'datasetTool.writeAccess' : aggregates ? 'datasetTool.aggregateAccess' : 'datasetTool.readOnly')}</p>
    </fieldset>
    {columns && <>
      {outdated && <Alert variant="warning"><AlertTriangle /><AlertDescription>
        {t('datasetTool.outdated')}
        <Button variant="outline" size="sm" disabled={disabled} onClick={() => onChange({
          fields: validFields, filter_ops: validFilters,
          ...(writes ? { write_fields: validWriteFields } : {}),
          ...(upserts && !keyValid ? { key: undefined } : {}),
        })}>{t('datasetNode.removeMissing')}</Button>
      </AlertDescription></Alert>}
      {finds && <div className="space-y-1.5">
        <Label htmlFor={`${id}-dataset-limit`}>{t('datasetNode.maxRows')}</Label>
        <Input id={`${id}-dataset-limit`} type="number" min={1} max={DATASET_AGENT_MAX_ROWS} value={tool.limit ?? 10}
          disabled={disabled} onChange={event => onChange({
            limit: Math.max(1, Math.min(DATASET_AGENT_MAX_ROWS, Math.trunc(Number(event.target.value)) || 1)),
          })} />
      </div>}
      {upserts && <div className="space-y-1.5">
        <Label htmlFor={`${id}-dataset-key`}>{t('datasetNode.upsertKey')}</Label>
        <ColumnSelect id={`${id}-dataset-key`} columns={uniqueColumns} value={tool.key} disabled={!!disabled}
          onChange={key => onChange({ key, write_fields: writeFields.includes(key) ? writeFields : [...writeFields, key] })} />
        {(!uniqueColumns.length || !keyValid) && <Alert variant="warning"><AlertTriangle />
          <AlertDescription>{t('datasetNode.uniqueRequired')}</AlertDescription></Alert>}
      </div>}
      {writes && <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t('datasetTool.writeFields')}</legend>
        {columns.filter(column => !datasetReadOnly(column.kind)).map(column => <Label key={column.key} className="gap-1.5">
          <Checkbox checked={writeFields.includes(column.key)} disabled={disabled || (upserts && tool.key === column.key)}
            onCheckedChange={checked => onChange({
              write_fields: checked ? [...writeFields, column.key] : writeFields.filter(field => field !== column.key),
            })} />
          <DatasetFieldIcon kind={column.kind} />{column.label}
        </Label>)}
        {!validWriteFields.length && <p className="text-xs text-destructive">{t('datasetTool.writeFieldsRequired')}</p>}
      </fieldset>}
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t(aggregates ? 'datasetTool.allowedAggregateFields' : 'datasetNode.returnFields')}</legend>
        {columns.map(column => <Label key={column.key} className="gap-1.5">
          <Checkbox checked={fields.includes(column.key)} disabled={disabled} onCheckedChange={checked =>
            onChange({ fields: checked ? [...fields, column.key] : fields.filter(field => field !== column.key) })} />
          <DatasetFieldIcon kind={column.kind} />{column.label}
        </Label>)}
        {!validFields.length && <p className="text-xs text-destructive">{t('datasetTool.fieldsRequired')}</p>}
        {writes && !finds && <p className="text-xs text-muted-foreground">{t('datasetTool.writeWithoutFind')}</p>}
      </fieldset>
      {(finds || aggregates) && <fieldset className="space-y-1.5">
        <legend className="mb-2 text-sm font-medium">{t('datasetTool.filterPermissions')}</legend>
        {columns.map(column => <DropdownMenu key={column.key}>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={disabled} className="w-full justify-start"
              aria-label={t('datasetTool.operatorsFor', { field: column.label })}>
              <DatasetFieldIcon kind={column.kind} /><span className="flex-1 truncate text-left">{column.label}</span>
              <span className="tabular-nums text-muted-foreground">{validFilters[column.key]?.length ?? 0}</span><ChevronDown />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {datasetFilterOperators(column.kind).map(op => <DropdownMenuCheckboxItem key={op}
              checked={(filterOps[column.key] ?? []).includes(op)} onSelect={event => event.preventDefault()}
              onCheckedChange={checked => toggleOperator(column.key, op, checked)}>
              {t(`datasetNode.filterOps.${op}`)}
            </DropdownMenuCheckboxItem>)}
          </DropdownMenuContent>
        </DropdownMenu>)}
      </fieldset>}
    </>}
  </div>
}
