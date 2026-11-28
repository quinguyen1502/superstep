import { useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Table2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { datasetTextKind, datasetUrl, type ColumnDraft, type Dataset } from '@/lib/datasets'
import { errorText } from '@/lib/i18n'
import { DatasetFieldIcon } from './dataset-field-icon'
import type { useDatasetRelationTargets } from './use-dataset-relations'

export function DatasetRelationDefinition({ column, targets, existing, enabled, onChange }: {
  column: ColumnDraft
  targets: ReturnType<typeof useDatasetRelationTargets>
  existing: boolean
  enabled: boolean
  onChange: (next: ColumnDraft) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const targetId = column.relation?.target_dataset_id ?? ''
  const displayKey = column.relation?.display_key ?? ''
  const target = targets.items.find(item => item.id === targetId)
  const [attempt, setAttempt] = useState(0)
  const [detail, setDetail] = useState<{ targetId: string; data?: Dataset; error?: string }>()

  useEffect(() => {
    if (!target) return
    const controller = new AbortController()
    void api<Dataset>(datasetUrl(target.id), { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setDetail({ targetId: target.id, data }) })
      .catch(error => {
        if (!controller.signal.aborted) setDetail({ targetId: target.id, error: error instanceof Error ? error.message : errorText({ code: 'INTERNAL_ERROR' }) })
      })
    return () => controller.abort()
  }, [attempt, target])

  const current = detail?.targetId === targetId ? detail : undefined
  const displayColumns = current?.data?.columns.filter(field => datasetTextKind(field.kind)) ?? []
  const error = targets.error || current?.error
  const targetPlaceholder = targets.loading ? t('common.loading') : t(targetId && !target ? 'dataset.relation.unavailable' : 'dataset.relation.chooseTarget')

  return <>
    <div className="min-w-0 space-y-1">
      <Label htmlFor={id + '-target'}>{t('dataset.relation.target')}</Label>
      <Select value={target ? targetId : ''} disabled={existing || !enabled || targets.loading || !!targets.error} onValueChange={next =>
        onChange({ ...column, relation: { target_dataset_id: next, display_key: '' } })}>
        <SelectTrigger id={id + '-target'} className="w-full"><SelectValue placeholder={targetPlaceholder} /></SelectTrigger>
        <SelectContent emptyMessage={t('dataset.relation.noTargets')}>
          {targets.items.map(item => <SelectItem value={item.id} key={item.id}><Table2 /><span className="truncate">{item.name}</span></SelectItem>)}
        </SelectContent>
      </Select>
    </div>
    <div className="min-w-0 space-y-1 sm:col-span-2">
      <Label htmlFor={id + '-display'}>{t('dataset.relation.displayColumn')}</Label>
      <Select value={displayColumns.some(field => field.key === displayKey) ? displayKey : ''} disabled={!target || !enabled || !current?.data}
        onValueChange={next => onChange({ ...column, relation: { target_dataset_id: targetId, display_key: next } })}>
        <SelectTrigger id={id + '-display'} className="w-full"><SelectValue
          placeholder={t(target && !current ? 'common.loading' : 'dataset.relation.chooseDisplay')} /></SelectTrigger>
        <SelectContent emptyMessage={t('dataset.relation.noDisplayColumns')}>
          {displayColumns.map(field => <SelectItem value={field.key} key={field.key}>
            <DatasetFieldIcon kind={field.kind} /><span className="truncate">{field.label}</span>
          </SelectItem>)}
        </SelectContent>
      </Select>
      <p className="text-xs text-muted-foreground">{t('dataset.relation.definitionHelp')}</p>
    </div>
    {error && <div className="space-y-2 sm:col-span-2">
      <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
      <Button type="button" variant="outline" size="sm" onClick={() => {
        if (targets.error) targets.retry()
        else { setDetail(undefined); setAttempt(value => value + 1) }
      }}>{t('common.retry')}</Button>
    </div>}
  </>
}
