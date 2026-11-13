import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, ExternalLink, Plus, Upload, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import { datasetUrl, displayValue, fromDraft, newDatasetColumn, toDraft, type CellValue, type Dataset, type DatasetColumn, type DatasetRow, type DatasetTeam } from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetColumnFields, DatasetValueField } from './dataset-fields'

const message = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export function DatasetFormDialog({ dataset, teams, onClose, onSave, onImportCsv }: {
  dataset?: Dataset
  teams: DatasetTeam[] | null
  onClose: () => void
  onSave: (dataset: Dataset) => void
  onImportCsv?: (initial: { name: string; teamId: string | null }) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const [name, setName] = useState(dataset?.name ?? '')
  const [description, setDescription] = useState(dataset?.description ?? '')
  const [scope, setScope] = useState('personal')
  const [columns, setColumns] = useState<{ id: number; draft: ReturnType<typeof toDraft> }[]>([])
  const [nextColumn, setNextColumn] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const memberTeams = teams?.filter(team => team.mine)

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await api<Dataset>(datasetUrl(dataset?.id), {
        method: dataset ? 'PUT' : 'POST',
        json: dataset ? { name, description, revision: dataset.revision } : {
          name, description, team_id: scope === 'personal' ? null : scope, columns: columns.map(({ draft }) => fromDraft(draft)),
        },
      })
      onSave(data)
    } catch (failure) {
      setError(message(failure, t('errors.INTERNAL_ERROR')))
    } finally {
      setBusy(false)
    }
  }

  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-xl">
      <DialogHeader><DialogTitle>{t(dataset ? 'dataset.editDataset' : 'dataset.createDataset')}</DialogTitle></DialogHeader>
      <DialogBody><form id={`${id}-form`} onSubmit={save} className="space-y-4">
        <div className="space-y-1"><Label htmlFor={`${id}-name`}>{t('dataset.name')}</Label>
          <Input id={`${id}-name`} value={name} maxLength={120} required onChange={event => setName(event.target.value)} />
        </div>
        <div className="space-y-1"><Label htmlFor={`${id}-description`}>{t('dataset.description')}</Label>
          <Textarea id={`${id}-description`} value={description} maxLength={2000} onChange={event => setDescription(event.target.value)} />
        </div>
        {!dataset && <>
          <div className="space-y-1"><Label htmlFor={`${id}-scope`}>{t('dataset.scope')}</Label>
            <Select value={scope} onValueChange={setScope}>
              <SelectTrigger id={`${id}-scope`} aria-describedby={`${id}-scope-help`} className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="personal">{t('dataset.personal')}</SelectItem>
                {memberTeams?.map(team => <SelectItem value={team.id} key={team.id}>{team.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <p id={`${id}-scope-help`} className="text-xs text-muted-foreground">
              {t('dataset.scopeHelp')}{memberTeams?.length === 0 && ` ${t('dataset.scopeNoTeams')}`}
            </p>
          </div>
          {columns.map(({ id: columnId, draft }) => <fieldset key={columnId} className="space-y-2 rounded-md border p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{t('dataset.columnDefinition')}</span>
              <Button type="button" variant="ghost" size="icon-sm" aria-label={t('dataset.discardColumn')}
                onClick={() => setColumns(current => current.filter(column => column.id !== columnId))}><X /></Button>
            </div>
            <DatasetColumnFields column={draft} onChange={next => setColumns(current => current.map(column => column.id === columnId ? { id: columnId, draft: next } : column))} />
          </fieldset>)}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" disabled={columns.length >= 100} onClick={() => {
              setColumns(current => [...current, { id: nextColumn, draft: toDraft(newDatasetColumn()) }])
              setNextColumn(current => current + 1)
            }}><Plus />{t('dataset.addColumn')}</Button>
            {onImportCsv && <Button type="button" variant="outline" onClick={() => onImportCsv({ name, teamId: scope === 'personal' ? null : scope })}>
              <Upload />{t('dataset.createFromCsv')}
            </Button>}
          </div>
        </>}
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      </form></DialogBody>
      <DialogFooter><Button type="button" variant="outline" disabled={busy} onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="submit" form={`${id}-form`} disabled={busy}>{t(dataset ? 'common.save' : 'dataset.createDataset')}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
}

export type DatasetDuplicateFilter = { field: string; value: CellValue }
type ColumnFailure = {
  message: string
  duplicates?: { field: string; value: CellValue; rows: string[]; count: number }
  workflow?: { id: string; name: string } | null
}

function columnFailure(failure: unknown, fallback: string): ColumnFailure {
  const result: ColumnFailure = { message: message(failure, fallback) }
  if (!(failure instanceof ApiError)) return result
  const details = failure.details ?? {}
  if (failure.code === 'DATASET_UNIQUE_DUPLICATES') {
    result.duplicates = { field: details.field, value: details.value ?? null, rows: details.rows ?? [], count: details.count ?? 0 }
  }
  if (failure.code === 'DATASET_SCHEMA_INCOMPATIBLE' && 'workflow' in details) {
    result.workflow = details.workflow_id ? { id: details.workflow_id, name: details.workflow } : null
  }
  return result
}

export function DatasetColumnDialog({ dataset, column, onClose, onSave, onShowDuplicates }: {
  dataset: Dataset
  column?: DatasetColumn
  onClose: () => void
  onSave: (dataset: Dataset) => void
  onShowDuplicates?: (filter: DatasetDuplicateFilter) => void
}) {
  const { t } = useTranslation()
  const formId = useId()
  const [draft, setDraft] = useState(() => toDraft(column ?? newDatasetColumn()))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ColumnFailure | null>(null)

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const url = `${datasetUrl(dataset.id)}/columns${column ? `/${encodeURIComponent(column.key)}` : ''}`
      onSave(await api<Dataset>(url, { method: column ? 'PUT' : 'POST', json: { revision: dataset.revision, column: fromDraft(draft) } }))
    } catch (failure) {
      setError(columnFailure(failure, t('errors.INTERNAL_ERROR')))
    } finally {
      setBusy(false)
    }
  }

  const duplicates = error?.duplicates
  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden">
      <DialogHeader><DialogTitle>{t(column ? 'dataset.editColumn' : 'dataset.addColumn')}</DialogTitle></DialogHeader>
      <DialogBody><form id={formId} className="space-y-4" onSubmit={save}>
        <DatasetColumnFields column={draft} existing={!!column} onChange={setDraft} />
        {duplicates ? <Alert variant="destructive" data-testid="dataset-unique-duplicates"><AlertTriangle />
          <AlertTitle>{t('dataset.uniqueDuplicatesTitle')}</AlertTitle>
          <AlertDescription>
            <p>{error.message}</p>
            <p>{t('dataset.uniqueDuplicatesHelp')}</p>
            {duplicates.rows.length > 0 && <p className="wrap-anywhere">
              {t('dataset.uniqueDuplicatesSample', { rows: duplicates.rows.join(', ') })}
            </p>}
            {onShowDuplicates && <Button type="button" variant="outline" size="sm" className="mt-1"
              onClick={() => onShowDuplicates({ field: duplicates.field, value: duplicates.value })}>
              {t('dataset.uniqueDuplicatesShow', { value: displayValue(duplicates.value, t('dataset.valueTrue'), t('dataset.valueFalse')) })}
            </Button>}
          </AlertDescription>
        </Alert> : error && <Alert variant="destructive"><AlertTriangle /><AlertDescription>
          <p>{error.message}</p>
          {error.workflow !== undefined && <p>{error.workflow
            ? <>{t('dataset.uniqueKeyInUse', { workflow: error.workflow.name })}{' '}
              <Link className="inline-flex items-center gap-1 underline" to={`/workflows/${encodeURIComponent(error.workflow.id)}`}>
                {t('dataset.openWorkflow')}<ExternalLink className="size-3" /></Link></>
            : t('dataset.uniqueKeyInUseHidden')}</p>}
        </AlertDescription></Alert>}
      </form></DialogBody>
      <DialogFooter><Button type="button" variant="outline" disabled={busy} onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="submit" form={formId} disabled={busy}>{t('common.save')}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
}

export function DatasetRowDialog({ dataset, row, editable, triggerId, onClose, onReload, onSave }: {
  dataset: Dataset
  row: DatasetRow
  editable: boolean
  triggerId: string
  onClose: () => void
  onReload: () => void
  onSave: (row: DatasetRow, values: Record<string, CellValue>, schemaRevision: number) => Promise<void>
}) {
  const { t } = useTranslation()
  const id = useId()
  const [{ source, schema }, setSnapshot] = useState({ source: row, schema: dataset })
  const [draft, setDraft] = useState<Record<string, CellValue>>({})
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<{ message: string; stale: boolean } | null>(null)
  const changes = Object.fromEntries(Object.entries(draft).filter(([key, value]) => !Object.is(source.values[key] ?? null, value)))
  const changed = Object.keys(changes).length > 0

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!editable || busy || failure?.stale || !changed) return
    setBusy(true)
    setFailure(null)
    try {
      await onSave(source, changes, schema.revision)
    } catch (error) {
      setFailure({
        message: message(error, t('errors.INTERNAL_ERROR')),
        stale: error instanceof ApiError && ['DATASET_ROW_CONFLICT', 'DATASET_SCHEMA_CONFLICT'].includes(error.code ?? ''),
      })
    } finally {
      setBusy(false)
    }
  }

  async function reload() {
    if (busy) return
    setBusy(true)
    try {
      const url = datasetUrl(dataset.id)
      const [freshRow, freshSchema] = await Promise.all([
        api<DatasetRow>(`${url}/rows/${source.id}`),
        api<Dataset>(url),
      ])
      setSnapshot({ source: freshRow, schema: freshSchema })
      setDraft({})
      setFailure(null)
      onReload()
    } catch (error) {
      setFailure({ message: message(error, t('errors.INTERNAL_ERROR')), stale: true })
    } finally {
      setBusy(false)
    }
  }

  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-xl" onCloseAutoFocus={event => {
      const trigger = document.getElementById(triggerId)
      if (trigger) {
        event.preventDefault()
        trigger.focus()
      }
    }}>
      <DialogHeader>
        <DialogTitle>{t(editable ? 'dataset.editRow' : 'dataset.rowDetails')}</DialogTitle>
        <DialogDescription>{schema.name}</DialogDescription>
      </DialogHeader>
      <DialogBody>
        {!schema.columns.length && <p className="text-sm text-muted-foreground">{t('dataset.noColumns')}</p>}
        <form key={`${schema.revision}-${source.revision}`} id={id} className="grid gap-4 sm:grid-cols-2" onSubmit={save}>
          {schema.columns.map((column, index) => {
            const fieldId = `${id}-${column.key}`
            return <div key={column.key} className="min-w-0 space-y-1">
              <Label htmlFor={fieldId} className="gap-1"><DatasetFieldIcon kind={column.kind} />{column.label}</Label>
              <DatasetValueField id={fieldId} label={column.label} column={column} disabled={busy || !editable} focus={editable && index === 0}
                value={Object.hasOwn(draft, column.key) ? draft[column.key] : source.values[column.key] ?? null}
                onChange={value => setDraft(current => ({ ...current, [column.key]: value }))} />
            </div>
          })}
          {failure && <Alert variant="destructive" className="sm:col-span-2"><AlertDescription>{failure.message}</AlertDescription></Alert>}
        </form>
      </DialogBody>
      <DialogFooter>
        <Button type="button" variant="outline" disabled={busy} onClick={onClose}>{t(editable ? 'common.cancel' : 'common.close')}</Button>
        {editable && (failure?.stale
          ? <Button type="button" disabled={busy} onClick={() => void reload()}>{t('dataset.discardAndReloadRow')}</Button>
          : <Button type="submit" form={id} disabled={busy || !changed}>{t('common.save')}</Button>)}
      </DialogFooter>
    </DialogContent>
  </Dialog>
}
