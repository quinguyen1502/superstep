import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, ApiError } from '@/lib/api'
import { datasetUrl, fromDraft, toDraft, type ColumnDraft, type Dataset, type DatasetColumn, type DatasetTeam } from '@/lib/datasets'
import { errorText, type ApiErrorBody } from '@/lib/i18n'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetColumnFields } from './dataset-fields'

const MAX_CSV_BYTES = 1_048_576
const SKIP = '__skip__'
type CsvIssue = { row: number; field: string | null; error: ApiErrorBody }
type CsvPreview = {
  headers: string[]
  columns: DatasetColumn[]
  mapping: (string | null)[]
  schema_revision: number | null
  total_rows: number
  invalid_rows: number
  issues: CsvIssue[]
  sample: { row: number; cells: string[] }[]
}

export function DatasetCsvDialog({ dataset, teams, initial, onClose, onImported }: {
  dataset?: Dataset
  teams: DatasetTeam[] | null
  initial?: { name: string; teamId: string | null }
  onClose: () => void
  onImported: (dataset: Dataset, count: number) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const [text, setText] = useState<string | null>(null)
  const [name, setName] = useState(initial?.name ?? '')
  const [teamId, setTeamId] = useState(initial?.teamId ?? 'personal')
  const [columns, setColumns] = useState<ColumnDraft[]>([])
  const [mapping, setMapping] = useState<(string | null)[]>([])
  const [preview, setPreview] = useState<CsvPreview | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [importIssues, setImportIssues] = useState<CsvIssue[] | null>(null)
  const issues = importIssues ?? preview?.issues ?? []
  const members = teams?.filter(team => team.mine) ?? []
  const canImport = !!preview && !dirty && !preview.invalid_rows && !importIssues && mapping.some(Boolean)
    && (!dataset || preview.total_rows > 0)
  const path = `${datasetUrl()}/csv`

  function showError(failure: unknown) {
    setError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR'))
    if (failure instanceof ApiError && Array.isArray(failure.details?.issues)) setImportIssues(failure.details.issues)
  }

  async function loadFile(file: File) {
    setText(null)
    setPreview(null)
    setError('')
    setImportIssues(null)
    setBusy(true)
    try {
      if (file.size > MAX_CSV_BYTES) throw new ApiError({ code: 'DATASET_CSV_LIMIT', details: { max: MAX_CSV_BYTES } }, 413)
      const buffer = await file.arrayBuffer()
      let contents: string
      try { contents = new TextDecoder('utf-8', { fatal: true }).decode(buffer) }
      catch { throw new Error(t('dataset.csvUtf8')) }
      const result = await api<CsvPreview>(`${path}/preview`, { method: 'POST', json: {
        text: contents, dataset_id: dataset?.id, schema_revision: dataset?.revision,
      } })
      if (!name) setName(file.name.replace(/\.csv$/i, '').slice(0, 120))
      setText(contents)
      setColumns(result.columns.map(toDraft))
      setMapping(result.mapping)
      setPreview(result)
      setDirty(!dataset)
    } catch (failure) {
      showError(failure)
    } finally {
      setBusy(false)
    }
  }

  function changeDraft() {
    setDirty(true)
    setError('')
    setImportIssues(null)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (text === null || busy) return
    const importNow = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-csv-action') === 'import'
    if (importNow && !canImport) return
    const json = {
      text, mapping, dataset_id: dataset?.id, schema_revision: preview?.schema_revision ?? dataset?.revision,
      create: dataset ? undefined : { name, team_id: teamId === 'personal' ? null : teamId, columns: columns.map(fromDraft) },
    }
    setBusy(true)
    setError('')
    setImportIssues(null)
    try {
      if (importNow) {
        const result = await api<{ dataset: Dataset; imported: number }>(`${path}/import`, { method: 'POST', json })
        onImported(result.dataset, result.imported)
      } else {
        setPreview(await api<CsvPreview>(`${path}/preview`, { method: 'POST', json }))
        setDirty(false)
      }
    } catch (failure) {
      showError(failure)
    } finally {
      setBusy(false)
    }
  }

  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle>{t(dataset ? 'dataset.importCsv' : 'dataset.createFromCsv')}</DialogTitle>
        <DialogDescription>{t('dataset.csvLimits')}</DialogDescription>
      </DialogHeader>
      <DialogBody>
        <form id={id} className="space-y-4" onSubmit={submit}>
          <div className="space-y-1">
            <Label htmlFor={`${id}-file`}>{t('dataset.csvFile')}</Label>
            <Input id={`${id}-file`} type="file" accept=".csv,text/csv" disabled={busy} onChange={event => {
              const file = event.currentTarget.files?.[0]
              if (file) void loadFile(file)
            }} />
          </div>
          {preview && <>
            {!dataset && <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1"><Label htmlFor={`${id}-name`}>{t('dataset.name')}</Label>
                <Input id={`${id}-name`} value={name} maxLength={120} required disabled={busy} onChange={event => { setName(event.target.value); changeDraft() }} />
              </div>
              <div className="space-y-1"><Label htmlFor={`${id}-scope`}>{t('dataset.scope')}</Label>
                <Select value={teamId} disabled={busy} onValueChange={value => { setTeamId(value); changeDraft() }}>
                  <SelectTrigger id={`${id}-scope`} className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="personal">{t('dataset.personal')}</SelectItem>
                    {members.map(team => <SelectItem key={team.id} value={team.id}>{team.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>}
            <div className="rounded-md border">
              <Table>
                <TableHeader><TableRow>
                  <TableHead scope="col">{t('dataset.csvSource')}</TableHead>
                  <TableHead scope="col">{t('dataset.csvTarget')}</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {preview.headers.map((header, index) => <TableRow key={index}>
                    <TableCell className="max-w-60 whitespace-normal wrap-anywhere">{header}</TableCell>
                    <TableCell><Select value={mapping[index] ?? SKIP} disabled={busy} onValueChange={value => {
                      setMapping(current => current.map((key, item) => item === index ? value === SKIP ? null : value : key))
                      changeDraft()
                    }}>
                      <SelectTrigger aria-label={t('dataset.csvMapColumn', { column: index + 1, name: header })} className="w-full min-w-36"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={SKIP}>{t('dataset.csvSkip')}</SelectItem>
                        {columns.filter(column => column.key).map((column, columnIndex) =>
                          <SelectItem key={columnIndex} value={column.key} disabled={mapping.some((key, item) => item !== index && key === column.key)}>
                            <DatasetFieldIcon kind={column.kind} /><span className="truncate">{column.label}</span>
                          </SelectItem>)}
                      </SelectContent>
                    </Select></TableCell>
                  </TableRow>)}
                </TableBody>
              </Table>
            </div>
            {!dataset && <fieldset disabled={busy} className="space-y-3">
              <legend className="mb-2 text-sm font-medium">{t('dataset.schema')}</legend>
              {columns.map((column, index) => <fieldset key={index} className="rounded-md border p-3">
                <legend className="px-1 text-sm font-medium">{preview.headers[index]}</legend>
                <DatasetColumnFields column={column} onChange={next => {
                  setColumns(current => current.map((item, position) => position === index ? next : item))
                  if (next.key !== column.key) setMapping(current => current.map(key => key === column.key ? next.key || null : key))
                  changeDraft()
                }} />
              </fieldset>)}
            </fieldset>}
            <p role="status" className="text-sm text-muted-foreground">
              {t('dataset.csvSummary', { total: preview.total_rows, invalid: preview.invalid_rows })}
            </p>
            {!!issues.length && <Alert variant="destructive"><AlertDescription>
              <ul className="space-y-1">
                {issues.map((issue, index) => <li key={index}>
                  {t('dataset.csvRowError', { row: issue.row, message: errorText(issue.error) })}
                </li>)}
              </ul>
            </AlertDescription></Alert>}
            {!!preview.sample.length && <div className="rounded-md border">
              <Table aria-label={t('dataset.csvPreview')}>
                <TableHeader><TableRow>
                  <TableHead scope="col">{t('dataset.csvLine')}</TableHead>
                  {preview.headers.map((header, index) => <TableHead key={index} scope="col" className="max-w-48 truncate">{header}</TableHead>)}
                </TableRow></TableHeader>
                <TableBody>{preview.sample.map(record => <TableRow key={record.row}>
                  <TableCell>{record.row}</TableCell>
                  {preview.headers.map((_, index) => <TableCell key={index} className="max-w-48 truncate">{record.cells[index] ?? '—'}</TableCell>)}
                </TableRow>)}</TableBody>
              </Table>
            </div>}
          </>}
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        </form>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" disabled={busy} onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="submit" form={id} variant="outline" disabled={busy || !preview || !mapping.some(Boolean)}>{t('dataset.csvCheck')}</Button>
        <Button type="submit" form={id} data-csv-action="import" disabled={busy || !canImport}>{t('dataset.importCsv')}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
}
