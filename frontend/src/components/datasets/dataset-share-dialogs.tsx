import { useCallback, useId, useRef, useState, type FormEvent } from 'react'
import { Check, Copy, Eye, Link2, TriangleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { DialogBody, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { DATASET_SHARE_PAGE_SIZE, type DatasetShareInput, type DatasetSharePreview } from '@/lib/dataset-shares'
import { emptyDatasetFilters, type Dataset } from '@/lib/datasets'
import { errorText } from '@/lib/i18n'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetFilterBuilder, validDatasetFilters } from './dataset-filter-builder'
import { DatasetShareError, DatasetShareTable } from './dataset-share-table'

export function CreateDatasetShare({ dataset, path, saving, error, onClearError, onCreate, onClose }: {
  dataset: Dataset
  path: string
  saving: boolean
  error?: unknown
  onClearError: () => void
  onCreate: (input: DatasetShareInput) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const nameInput = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [fields, setFields] = useState<string[]>([])
  const [filter, setFilter] = useState(emptyDatasetFilters)
  const [preview, setPreview] = useState<DatasetShareInput>()
  const [ready, setReady] = useState(false)
  const focusPreview = useCallback((heading: HTMLHeadingElement | null) => { heading?.focus() }, [])
  const previewMatches = preview?.schema_revision === dataset.revision
  const columns = dataset.columns.filter(column => column.kind !== 'relation')
  const valid = !!name.trim() && !!fields.length && validDatasetFilters(filter, columns)

  const load = useCallback((search: string, offset: number, signal: AbortSignal) =>
    api<DatasetSharePreview>(`${path}/preview`, {
      method: 'POST', json: { ...preview, search: search || null, offset, limit: DATASET_SHARE_PAGE_SIZE }, signal,
    }), [path, preview])

  function showPreview(event: FormEvent) {
    event.preventDefault()
    if (!valid || saving) return
    onClearError()
    setReady(false)
    setPreview({
      name: name.trim(),
      fields,
      filter_tree: filter.children.length ? filter : null,
      schema_revision: dataset.revision,
    })
  }

  return <>
    <DialogHeader>
      <DialogTitle>{t('dataset.share.create')}</DialogTitle>
      <DialogDescription>{t(previewMatches ? 'dataset.share.previewHelp' : 'dataset.share.createHelp')}</DialogDescription>
    </DialogHeader>
    <DialogBody className="space-y-4">
      {!previewMatches && <form id={id} className="grid gap-4" onSubmit={showPreview}>
        <div className="grid gap-1.5">
          <Label htmlFor={`${id}-name`}>{t('dataset.share.name')}</Label>
          <Input id={`${id}-name`} ref={nameInput} value={name} maxLength={120} required disabled={saving} onChange={event => {
            setName(event.target.value)
            setPreview(undefined)
          }} />
        </div>
        <fieldset className="grid min-w-0 gap-2" disabled={saving}>
          <legend className="mb-1.5 font-medium">{t('dataset.share.columns')}</legend>
          <div className="grid min-w-0 gap-1 sm:grid-cols-2">
            {columns.map(column => {
              const checked = fields.includes(column.key)
              return <Label key={column.key} className="min-w-0 rounded-md border p-2">
                <Checkbox checked={checked} onCheckedChange={value => {
                  setFields(value === true ? [...fields, column.key] : fields.filter(field => field !== column.key))
                  setPreview(undefined)
                }} />
                <DatasetFieldIcon kind={column.formula ? 'formula' : column.kind} />
                <span className="wrap-anywhere">{column.label}</span>
              </Label>
            })}
          </div>
        </fieldset>
        <fieldset className="grid min-w-0 gap-2" disabled={saving}>
          <legend className="mb-1.5 font-medium">{t('dataset.share.filter')}</legend>
          <DatasetFilterBuilder tree={filter} columns={columns} disabled={saving} onChange={value => {
            setFilter(value)
            setPreview(undefined)
          }} />
        </fieldset>
      </form>}
      {preview && !previewMatches && <Alert variant="warning"><TriangleAlert /><AlertDescription>
        {errorText({ code: 'DATASET_SHARE_SCHEMA_CHANGED' })}
      </AlertDescription></Alert>}
      {previewMatches && <section className="grid min-w-0 gap-2">
        <h3 ref={focusPreview} tabIndex={-1} className="wrap-anywhere font-medium focus:outline-none">{preview.name}</h3>
        <DatasetShareTable load={load} onLoaded={setReady} />
      </section>}
      {!!error && <DatasetShareError error={error} />}
    </DialogBody>
    <DialogFooter>
      {previewMatches ? <>
        <Button variant="outline" disabled={saving} onClick={() => {
          onClearError()
          setPreview(undefined)
          requestAnimationFrame(() => nameInput.current?.focus())
        }}>{t('dataset.share.editView')}</Button>
        <Button disabled={saving || !ready} onClick={() => {
          if (preview && ready) onCreate(preview)
        }}><Link2 />{t('dataset.share.create')}</Button>
      </> : <>
        <Button variant="outline" disabled={saving} onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="submit" form={id} disabled={saving || !valid}><Eye />{t('dataset.share.preview')}</Button>
      </>}
    </DialogFooter>
  </>
}

export function DatasetShareLink({ url, rotated }: { url: string; rotated: boolean }) {
  const { t } = useTranslation()
  const id = useId()
  const focusLink = useCallback((input: HTMLInputElement | null) => { input?.focus(); input?.select() }, [])
  const [status, setStatus] = useState<'copied' | 'failed'>()
  return <>
    <DialogHeader>
      <DialogTitle>{t('dataset.share.link')}</DialogTitle>
      <DialogDescription>{t(rotated ? 'dataset.share.rotated' : 'dataset.share.linkOnce')}</DialogDescription>
    </DialogHeader>
    <DialogBody className="space-y-2">
      <Label htmlFor={id}>{t('dataset.share.link')}</Label>
      <div className="flex items-center gap-2">
        <Input id={id} value={url} readOnly className="min-w-0" ref={focusLink} />
        <Button variant="outline" size="icon" aria-label={t('dataset.share.copy')}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(url)
              setStatus('copied')
            } catch {
              setStatus('failed')
            }
          }}>{status === 'copied' ? <Check /> : <Copy />}</Button>
      </div>
      {status === 'copied' && <p role="status" className="text-sm text-muted-foreground">{t('dataset.share.copied')}</p>}
      {status === 'failed' && <Alert variant="destructive"><TriangleAlert /><AlertDescription>
        {t('dataset.share.copyFailed')}
      </AlertDescription></Alert>}
    </DialogBody>
    <DialogFooter showCloseButton />
  </>
}
