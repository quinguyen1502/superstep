import { useEffect, useState } from 'react'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { datasetUrl, type DatasetPage, type DatasetSummary } from '@/lib/datasets'
import type { BindingLookup } from './use-dataset-node-binding'

export function DatasetPicker({ id, value, binding, disabled, onChange }: {
  id: string; value?: string; binding: BindingLookup | null; disabled?: boolean; onChange: (value: string) => void
}) {
  const { t } = useTranslation()
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
  const orphaned = value && !catalog?.items.some(item => item.id === value)
  return <div className="space-y-1.5">
    <Label htmlFor={id}>{t('datasetNode.dataset')}</Label>
    <Select value={value || ''} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger id={id} className="w-full"><SelectValue placeholder={t('datasetNode.chooseDataset')} /></SelectTrigger>
      <SelectContent emptyMessage={error || (catalog === null ? t('common.loading') : t('dataset.noDatasets'))}>
        {orphaned && <SelectItem value={value!} disabled={!binding?.dataset}>{binding?.dataset?.name ?? t('datasetNode.unavailable')}</SelectItem>}
        {catalog?.items.map(item => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
      </SelectContent>
    </Select>
    {catalog?.next_offset != null && <Button variant="ghost" size="sm" disabled={loading} onClick={() => void more()}>{t('dataset.moreDatasets')}</Button>}
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
  </div>
}

export function DatasetBindingNotice({ value, binding, permission }: {
  value?: string; binding: BindingLookup | null; permission: 'read' | 'write'
}) {
  const { t } = useTranslation()
  const missingGrant = binding?.permission !== undefined && binding.permission !== 'read_write' && binding.permission !== permission
  return <>
    {!value && <Alert variant="warning"><AlertTriangle /><AlertDescription>{t('datasetNode.rebind')}</AlertDescription></Alert>}
    {binding?.error && <Alert variant="destructive"><AlertDescription>{binding.error} {t('datasetNode.rebind')}</AlertDescription></Alert>}
    {binding?.dataset && !binding.workflowId && <p className="text-xs text-muted-foreground">{t('datasetNode.saveForGrant')}</p>}
    {binding?.grantError && <Alert variant="warning"><AlertTriangle /><AlertDescription>{binding.grantError}</AlertDescription></Alert>}
    {missingGrant && <Alert variant="warning"><AlertTriangle /><AlertDescription>{t(`datasetNode.grantMissing.${permission}`)}</AlertDescription></Alert>}
    {binding?.dataset && <Button variant="outline" size="sm" asChild>
      <Link to={`/datasets/${encodeURIComponent(binding.dataset.id)}`} target="_blank" rel="noopener"><ExternalLink />{t('datasetNode.openDataset')}</Link>
    </Button>}
  </>
}
