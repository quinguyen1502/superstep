import { useId, type ReactNode } from 'react'
import { Layers, Plus, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  DATASET_FILTER_DEPTH, DATASET_FILTER_RULES, DATASET_FILTER_VALUES, datasetFilterOperators, datasetFilterRules,
  datasetListFilter, datasetSubstringFilter, datasetValueFreeFilter, emptyDatasetFilters,
  type ScalarCellValue, type DatasetColumn, type DatasetFilterRule, type DatasetFilters,
} from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetValueField } from './dataset-fields'

type ValueProps = {
  id: string
  label: string
  column: DatasetColumn
  op: string
  value: ScalarCellValue
  onChange: (value: ScalarCellValue) => void
  disabled: boolean
}

function ruleError(rule: DatasetFilterRule, column?: DatasetColumn): string | undefined {
  if (!column) return 'dataset.filterChooseColumn'
  if (!datasetFilterOperators(column.kind).includes(rule.op)) return 'dataset.filterChooseOperator'
  if (datasetValueFreeFilter(rule.op)) return
  const values = datasetListFilter(rule.op) ? rule.value : [rule.value]
  if (!Array.isArray(values) || !values.length || values.some(value => value === null || value === '')) {
    return 'dataset.filterEnterValue'
  }
}

export function validDatasetFilters(tree: DatasetFilters, columns: DatasetColumn[], depth = 1): boolean {
  return (depth === 1 || tree.children.length > 0) && tree.children.every(child => child.type === 'group'
    ? validDatasetFilters(child, columns, depth + 1)
    : !ruleError(child, columns.find(column => column.key === child.field)))
}

function LiteralFilterValue({ id, label, column, op, value, disabled, onChange }: ValueProps) {
  if (datasetSubstringFilter(op)) {
    return <Input id={id} aria-label={label} required maxLength={120} disabled={disabled}
      value={String(value ?? '')} onChange={event => onChange(event.target.value)} />
  }
  return <DatasetValueField id={id} label={label} column={column} value={value}
    nullable={false} filter disabled={disabled} onChange={next => { if (!Array.isArray(next)) onChange(next) }} />
}

export function DatasetFilterBuilder({ tree, columns, onChange, disabled = false, renderValue }: {
  tree: DatasetFilters
  columns: DatasetColumn[]
  onChange: (tree: DatasetFilters) => void
  disabled?: boolean
  renderValue?: (props: ValueProps) => ReactNode
}) {
  const { t } = useTranslation()
  const id = useId()
  const ruleCount = datasetFilterRules(tree).length

  function renderGroup(group: DatasetFilters, change: (next: DatasetFilters) => void, path: number[], remove?: () => void) {
    const position = path.join('.')
    const changeChild = (index: number, next: DatasetFilters['children'][number]) =>
      change({ ...group, children: group.children.map((child, current) => current === index ? next : child) })
    const removeChild = (index: number) =>
      change({ ...group, children: group.children.filter((_, current) => current !== index) })
    const canAdd = !disabled && !!columns.length && ruleCount < DATASET_FILTER_RULES && group.children.length < DATASET_FILTER_RULES
    const newRule = (): DatasetFilterRule => ({ type: 'rule', field: renderValue ? columns[0]?.key ?? '' : '', op: renderValue && columns.length ? datasetFilterOperators(columns[0].kind)[0] : 'eq', value: null })
    const matchLabel = path.length ? t('dataset.filterGroupMatch', { number: position }) : t('dataset.filterMatch')

    return <div role={remove ? 'group' : undefined} aria-label={remove ? t('dataset.filterGroup', { number: position }) : undefined}
      className={remove ? 'grid min-w-0 gap-2 rounded-md border border-border p-2' : 'grid min-w-0 gap-2'}>
      <div className="flex items-start gap-2">
        <Select value={group.conjunction} disabled={disabled} onValueChange={value => change({ ...group, conjunction: value === 'or' ? 'or' : 'and' })}>
          <SelectTrigger aria-label={matchLabel} className="w-fit min-w-0 max-w-full"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="and">{t('dataset.filterMatchAll')}</SelectItem>
            <SelectItem value="or">{t('dataset.filterMatchAny')}</SelectItem>
          </SelectContent>
        </Select>
        {remove && <Button type="button" variant="ghost" size="icon" disabled={disabled} aria-label={t('dataset.removeFilterGroup')}
          onClick={remove}><X /></Button>}
      </div>
      {!group.children.length && <Empty className="p-3"><EmptyDescription>{t('dataset.noFilterConditions')}</EmptyDescription></Empty>}
      {group.children.map((child, index) => {
        const childPath = [...path, index + 1]
        const key = childPath.join('.')
        if (child.type === 'group') {
          return <div key={key} className="min-w-0">{renderGroup(child, next => changeChild(index, next), childPath, () => removeChild(index))}</div>
        }
        const column = columns.find(item => item.key === child.field)
        const ops = column ? datasetFilterOperators(column.kind) : []
        const error = ruleError(child, column)
        const replace = (patch: Partial<DatasetFilterRule>) => changeChild(index, { ...child, ...patch })
        const list = datasetListFilter(child.op)
        const values: ScalarCellValue[] = Array.isArray(child.value) ? child.value : [child.value]
        const valueControls = column?.kind === 'multi_select' && !datasetValueFreeFilter(child.op)
          ? <DatasetValueField id={`${id}-${key}`} label={t('dataset.filterValue')} column={column} value={Array.isArray(child.value) ? child.value.filter(item => typeof item === 'string') : null}
              disabled={disabled} filter nullable={false} onChange={value => replace({ value: Array.isArray(value) ? value : null })} />
          : column && !datasetValueFreeFilter(child.op) && <div className="grid min-w-0 gap-2">
          {values.map((value, valueIndex) => {
            const props: ValueProps = {
              id: `${id}-${key}-${valueIndex}`, label: list ? t('dataset.filterListValue', { number: valueIndex + 1 }) : t('dataset.filterValue'),
              column, op: child.op, value, disabled,
              onChange: next => replace({ value: list ? values.map((item, current) => current === valueIndex ? next : item) : next }),
            }
            return <div className="flex min-w-0 items-start gap-1" key={valueIndex}>
              <div className="min-w-0 flex-1" key={`${column.key}-${child.op}`}>
                {renderValue ? renderValue(props) : <LiteralFilterValue {...props} />}
              </div>
              {list && <Button type="button" variant="ghost" size="icon" disabled={disabled || values.length === 1}
                aria-label={t('dataset.removeFilterValue', { number: valueIndex + 1 })}
                onClick={() => replace({ value: values.filter((_, current) => current !== valueIndex) })}><X /></Button>}
            </div>
          })}
          {list && <Button type="button" variant="outline" className="justify-self-start" disabled={disabled || values.length >= DATASET_FILTER_VALUES}
            onClick={() => replace({ value: [...values, null] })}><Plus />{t('dataset.addFilterValue')}</Button>}
        </div>

        return <fieldset key={key} className={renderValue ? 'grid min-w-0 gap-2 rounded-md border p-2' : 'grid min-w-0 gap-2'}>
          <legend className={renderValue ? 'px-1 text-xs' : 'sr-only'}>{t('dataset.filterCondition', { number: key })}</legend>
          <div className="flex min-w-0 items-start gap-2">
            <div className={renderValue ? 'grid min-w-0 flex-1 gap-2' : 'grid min-w-0 flex-1 gap-2 sm:grid-cols-3'}>
              <Select value={column?.key ?? ''} disabled={disabled} onValueChange={field => replace({ field, op: datasetFilterOperators(columns.find(column => column.key === field)!.kind)[0], value: null })}>
                <SelectTrigger aria-label={t('dataset.filterColumn')} className="w-full min-w-0"><SelectValue placeholder={t('dataset.filterColumn')} /></SelectTrigger>
                <SelectContent>{columns.map(item => <SelectItem key={item.key} value={item.key}><DatasetFieldIcon kind={item.kind} /><span className="truncate">{item.label}</span></SelectItem>)}</SelectContent>
              </Select>
              <Select value={ops.includes(child.op) ? child.op : ''} disabled={disabled || !column}
                onValueChange={op => replace({ op, value: datasetListFilter(op) && column?.kind !== 'multi_select' ? [null] : null })}>
                <SelectTrigger aria-label={t('dataset.filterOperator')} className="w-full min-w-0"><SelectValue placeholder={t('dataset.filterOperator')} /></SelectTrigger>
                <SelectContent>{ops.map(op => <SelectItem key={op} value={op}>{t(`datasetNode.filterOps.${op}`)}</SelectItem>)}</SelectContent>
              </Select>
              {!renderValue && (column ? valueControls : <Input disabled aria-label={t('dataset.filterValue')} placeholder={t('dataset.filterValue')} />)}
            </div>
            <Button type="button" variant="ghost" size="icon" disabled={disabled} aria-label={t('dataset.removeFilterCondition')}
              onClick={() => removeChild(index)}><X /></Button>
          </div>
          {renderValue && ops.includes(child.op) && <p className="text-xs text-muted-foreground">{t(`datasetNode.filterOpHelp.${child.op}`)}</p>}
          {renderValue && valueControls}
          {error && <p role="status" className="text-xs text-destructive">{t(error)}</p>}
        </fieldset>
      })}
      <div className="flex flex-wrap gap-1">
        <Button type="button" variant="ghost" disabled={!canAdd}
          onClick={() => change({ ...group, children: [...group.children, newRule()] })}><Plus />{t('dataset.addFilterCondition')}</Button>
        <Button type="button" variant="ghost" disabled={!canAdd || path.length + 1 >= DATASET_FILTER_DEPTH}
          onClick={() => change({ ...group, children: [...group.children, { ...emptyDatasetFilters(), children: [newRule()] }] })}><Layers />{t('dataset.addFilterGroup')}</Button>
      </div>
    </div>
  }

  return renderGroup(tree, onChange, [])
}
