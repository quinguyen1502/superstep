import { AlertTriangle, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { AgentTool } from '@/lib/agent'
import { DATASET_AGENT_MAX_ROWS, datasetFilterOperators } from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetBindingNotice, DatasetPicker } from './dataset-picker'
import { useDatasetNodeBinding } from './use-dataset-node-binding'

export function DatasetAgentSettings({ id, tool, wid, disabled, onChange }: {
  id: string; tool: AgentTool; wid?: string; disabled?: boolean; onChange: (patch: Partial<AgentTool>) => void
}) {
  const { t } = useTranslation()
  const binding = useDatasetNodeBinding(tool.dataset_id, wid)
  const columns = binding?.dataset?.columns
  const fields = tool.fields ?? []
  const filterOps = tool.filter_ops ?? {}
  const validFields = fields.filter(field => columns?.some(column => column.key === field))
  const validFilters = Object.fromEntries((columns ?? []).flatMap(column => {
    const allowed = (filterOps[column.key] ?? []).filter(op => datasetFilterOperators(column.kind).includes(op))
    return allowed.length ? [[column.key, allowed]] : []
  }))
  const outdated = columns && (validFields.length !== fields.length
    || Object.entries(filterOps).some(([field, ops]) => ops.length !== validFilters[field]?.length))

  function toggleOperator(field: string, operator: string, checked: boolean) {
    const current = filterOps[field] ?? []
    const next = { ...filterOps }
    const operators = checked ? [...current, operator] : current.filter(op => op !== operator)
    if (operators.length) next[field] = operators
    else delete next[field]
    onChange({ filter_ops: next })
  }

  return <div className="space-y-3">
    <DatasetPicker id={`${id}-dataset`} value={tool.dataset_id} binding={binding} disabled={disabled}
      onChange={dataset_id => onChange({ dataset_id })} />
    <DatasetBindingNotice value={tool.dataset_id} binding={binding} permission="read" />
    {columns && <>
      <p className="text-xs text-muted-foreground">{t('datasetTool.readOnly')}</p>
      {outdated && <Alert variant="warning"><AlertTriangle /><AlertDescription>
        {t('datasetTool.outdated')}
        <Button variant="outline" size="sm" disabled={disabled} onClick={() =>
          onChange({ fields: validFields, filter_ops: validFilters })}>{t('datasetNode.removeMissing')}</Button>
      </AlertDescription></Alert>}
      <div className="space-y-1.5">
        <Label htmlFor={`${id}-dataset-limit`}>{t('datasetNode.maxRows')}</Label>
        <Input id={`${id}-dataset-limit`} type="number" min={1} max={DATASET_AGENT_MAX_ROWS} value={tool.limit ?? 10}
          disabled={disabled} onChange={event => onChange({
            limit: Math.max(1, Math.min(DATASET_AGENT_MAX_ROWS, Math.trunc(Number(event.target.value)) || 1)),
          })} />
      </div>
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">{t('datasetNode.returnFields')}</legend>
        {columns.map(column => <Label key={column.key} className="gap-1.5">
          <Checkbox checked={fields.includes(column.key)} disabled={disabled} onCheckedChange={checked =>
            onChange({ fields: checked ? [...fields, column.key] : fields.filter(field => field !== column.key) })} />
          <DatasetFieldIcon kind={column.kind} />{column.label}
        </Label>)}
        {!validFields.length && <p className="text-xs text-destructive">{t('datasetTool.fieldsRequired')}</p>}
      </fieldset>
      <fieldset className="space-y-1.5">
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
      </fieldset>
    </>}
  </div>
}
