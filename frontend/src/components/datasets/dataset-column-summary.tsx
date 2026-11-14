import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { displayValue, datasetSummaryFunctions, type CellValue, type DatasetColumn, type DatasetSummaryFunction } from '@/lib/datasets'

export function DatasetColumnSummary({ column, operation, value, loading, failed, disabled, onChange }: {
  column: DatasetColumn
  operation?: DatasetSummaryFunction
  value?: CellValue
  loading: boolean
  failed: boolean
  disabled: boolean
  onChange: (operation?: DatasetSummaryFunction) => void
}) {
  const { t, i18n } = useTranslation()
  const label = t('dataset.summaryForColumn', { column: column.label })
  const operations = datasetSummaryFunctions(column.kind)
  const format = typeof value === 'number'
    ? new Intl.NumberFormat(i18n.resolvedLanguage, operation === 'empty_percent'
      ? { style: 'percent', maximumFractionDigits: 2 }
      : { maximumFractionDigits: 8 }).format(operation === 'empty_percent' ? value / 100 : value)
    : typeof value === 'string' ? displayValue(value, t('dataset.valueTrue'), t('dataset.valueFalse'), column.kind) : t('dataset.summaryNoValue')
  return <div className="grid gap-1">
    <Select value={operation ?? 'none'} disabled={disabled} onValueChange={selection => onChange(operations.find(item => item === selection))}>
      <SelectTrigger size="sm" aria-label={label} className="w-full min-w-0"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="none">{t('dataset.summaryNone')}</SelectItem>
        {operations.map(item => <SelectItem key={item} value={item}>{t(`dataset.summaryFunctions.${item}`)}</SelectItem>)}
      </SelectContent>
    </Select>
    {operation && <output aria-label={label} className="truncate text-sm tabular-nums"
      title={!loading && !failed ? format : undefined}>
      {failed ? t('dataset.summaryNoValue') : loading ? t('common.loading') : format}
    </output>}
  </div>
}
