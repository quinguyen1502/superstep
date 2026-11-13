import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronRight, Download, Info, PanelLeftClose, PanelLeftOpen, Pencil, Plus, SearchX, Table2, Trash2, Upload, UserRoundCog, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Dialog, DialogBody, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { DatasetCsvDialog } from '@/components/datasets/dataset-csv-dialog'
import { DatasetColumnDialog, DatasetFormDialog } from '@/components/datasets/dataset-dialogs'
import { DatasetAccessDialog } from '@/components/datasets/dataset-access-dialog'
import { DatasetActionsMenu } from '@/components/datasets/dataset-actions-menu'
import { DatasetFieldIcon } from '@/components/datasets/dataset-field-icon'
import { DatasetGrid } from '@/components/datasets/dataset-grid'
import { DatasetOwnerDialog } from '@/components/datasets/dataset-owner-dialog'
import type { DatasetFilters } from '@/components/datasets/dataset-query-controls'
import { HandbookLink } from '@/components/handbook-link'
import { LanguageSwitcher } from '@/components/language-switcher'
import { Logo } from '@/components/logo'
import { StudioResourceNav } from '@/components/studio-resource-nav'
import { Tip } from '@/components/tip'
import { ThemeToggle } from '@/components/theme-toggle'
import { UserMenu } from '@/components/user-menu'
import { api, ApiError } from '@/lib/api'
import { canManageDataset, datasetUrl, displayValue, type Dataset, type DatasetColumn, type DatasetPage, type DatasetSummary, type DatasetTeam } from '@/lib/datasets'
import { can, useMe } from '@/lib/rbac'
import { useLoadWhen } from '@/lib/use-when'
import { cn } from '@/lib/utils'

const SIDEBAR_KEY = 'studio-dataset-sidebar-collapsed'

export function DatasetsPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useMe()
  const editable = can(me, 'resources.manage')
  const confirm = useConfirmDelete()
  const datasetMenu = useRef<HTMLButtonElement>(null)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_KEY) === '1')
  const [catalog, setCatalog] = useState<DatasetPage<DatasetSummary> | null>(null)
  const [catalogError, setCatalogError] = useState('')
  const [detailFailure, setDetailFailure] = useState<{ id: string; message: string; missing: boolean } | null>(null)
  const [teams, setTeams] = useState<DatasetTeam[] | null>(null)
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [datasetDialog, setDatasetDialog] = useState<'create' | 'edit' | null>(null)
  const [accessId, setAccessId] = useState<string | null>(null)
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [csv, setCsv] = useState<{ dataset?: Dataset; initial?: { name: string; teamId: string | null } } | null>(null)
  const [csvNotice, setCsvNotice] = useState<{ id: string; count: number } | null>(null)
  const [csvError, setCsvError] = useState('')
  const [schemaId, setSchemaId] = useState<string | null>(null)
  const [columnDialog, setColumnDialog] = useState<DatasetColumn | 'new' | null>(null)
  const [gridFilter, setGridFilter] = useState<{ id: string; seq: number; filters: DatasetFilters } | null>(null)
  const current = dataset?.id === id ? dataset : null
  const manageable = !!current && canManageDataset(me, current)
  const manageNote = editable && !manageable ? t('dataset.manageOnly') : undefined
  const detailError = detailFailure?.id === id ? detailFailure?.message : undefined
  const missing = detailFailure?.id === id && !!detailFailure?.missing
  const viewOnly = me && !editable ? t('dataset.viewOnlyReason') : undefined
  /** Why dataset-level controls (edit, access, delete, schema) are disabled: no permission at all, or not the owner. */
  const datasetNote = viewOnly ?? manageNote

  const loadCatalog = useCallback(async (offset = 0) => {
    try {
      const page = await api<DatasetPage<DatasetSummary>>(`${datasetUrl()}?offset=${offset}`)
      setCatalog(previous => ({ ...page, items: offset ? [...previous?.items ?? [], ...page.items] : page.items }))
      setCatalogError('')
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : t('errors.INTERNAL_ERROR'))
    }
  }, [t])

  useLoadWhen(true, () => { void loadCatalog() })
  useEffect(() => {
    let active = true
    api<{ teams: DatasetTeam[] }>('/api/teams').then(result => { if (active) setTeams(result.teams) })
      .catch(error => { if (active) setCatalogError(error.message) })
    return () => { active = false }
  }, [])

  const [detailRefresh, setDetailRefresh] = useState(0)
  const reloadDataset = useCallback(() => {
    setDetailFailure(null)
    setDetailRefresh(current => current + 1)
  }, [])
  useEffect(() => {
    let active = true
    if (id) api<Dataset>(datasetUrl(id))
      .then(data => { if (active) { setDataset(data); setDetailFailure(null) } })
      .catch(error => { if (active) { setDataset(null); setDetailFailure({ id, message: error.message, missing: error instanceof ApiError && error.code === 'DATASET_NOT_FOUND' }) } })
    return () => { active = false }
  }, [detailRefresh, id])

  function saveDataset(data: Dataset) {
    setDatasetDialog(null)
    setDataset(data)
    void loadCatalog()
    if (id !== data.id) navigate(`/datasets/${data.id}`)
  }

  async function exportCsv(data: Dataset) {
    setCsvError('')
    try {
      const blob = await api<Blob>(`${datasetUrl(data.id)}/csv`, { response: 'blob' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${data.name}.csv`
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch (failure) {
      setCsvError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR'))
    }
  }

  function askDeleteDataset(data: Dataset) {
    confirm.ask({ name: data.name, title: t('dataset.deleteDataset'), description: t('dataset.deleteDatasetBody'),
      onConfirm: async () => {
        await api(`${datasetUrl(data.id)}?revision=${data.revision}`, { method: 'DELETE' })
        setDataset(null)
        navigate('/datasets')
        void loadCatalog()
      },
    })
  }

  function askDeleteColumn(data: Dataset, column: DatasetColumn) {
    confirm.ask({ name: column.label, title: t('dataset.deleteColumn'), description: t('dataset.deleteColumnBody'),
      onConfirm: async () => {
        setDataset(await api<Dataset>(`${datasetUrl(data.id)}/columns/${encodeURIComponent(column.key)}?revision=${data.revision}`, { method: 'DELETE' }))
      },
    })
  }

  const scopeName = (item: DatasetSummary) => item.team_id
    ? teams?.find(team => team.id === item.team_id)?.name ?? t('dataset.team')
    : t('dataset.personal')

  const groups = new Map<string, DatasetSummary[]>()
  for (const item of catalog?.items ?? []) {
    const key = item.team_id ?? 'personal'
    const group = groups.get(key)
    if (group) group.push(item)
    else groups.set(key, [item])
  }

  return <div className="flex min-h-dvh flex-col bg-background text-foreground">
    <header className="flex min-h-14 flex-wrap items-center gap-3 border-b px-4 md:px-6">
      <Link to="/workflows"><Logo /></Link>
      <StudioResourceNav active="datasets" />
      <div className="ml-auto flex items-center gap-1"><LanguageSwitcher /><ThemeToggle /><UserMenu /></div>
    </header>
    <main className={cn('grid w-full flex-1 max-md:content-start', collapsed
      ? 'md:grid-cols-[3.25rem_minmax(0,1fr)]' : 'md:grid-cols-[13rem_minmax(0,1fr)]')}>
      <aside aria-label={t('dataset.catalog')} className="min-w-0 border-b bg-sidebar text-sidebar-foreground md:border-r md:border-b-0">
        <div className={cn('flex items-center gap-1 p-2', collapsed && 'md:flex-col')}>
          <Tip tip={t(collapsed ? 'dataset.expandCatalog' : 'dataset.collapseCatalog')}>
            <Button type="button" variant="ghost" size="icon" aria-label={t(collapsed ? 'dataset.expandCatalog' : 'dataset.collapseCatalog')}
              aria-controls="dataset-catalog-list" aria-expanded={!collapsed} onClick={() => {
                setCollapsed(!collapsed)
                localStorage.setItem(SIDEBAR_KEY, collapsed ? '0' : '1')
              }}>{collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}</Button>
          </Tip>
          <h1 className={cn('min-w-0 flex-1 truncate text-sm font-semibold', collapsed && 'sr-only')}>{t('dataset.title')}</h1>
          <Tip tip={viewOnly ?? t('dataset.createDataset')}>
            <span className={cn('inline-flex', collapsed && 'ml-auto md:ml-0')} tabIndex={viewOnly ? 0 : undefined}>
              <Button size="icon" variant="outline" disabled={!editable} aria-describedby={viewOnly ? 'dataset-view-only' : undefined}
                aria-label={t('dataset.createDataset')} onClick={() => setDatasetDialog('create')}><Plus /></Button>
            </span>
          </Tip>
        </div>
        <div id="dataset-catalog-list" className={cn('space-y-2 px-2 pb-2', collapsed && 'max-md:hidden')}>
          {catalogError && !collapsed && <Alert variant="destructive"><AlertDescription>{catalogError}
            <Button variant="outline" onClick={() => void loadCatalog()}>{t('common.retry')}</Button>
          </AlertDescription></Alert>}
          {!catalog && !catalogError && !collapsed && <p className="text-sm text-muted-foreground">{t('common.loading')}</p>}
          {catalog && !catalog.items.length && !collapsed && <p className="text-sm text-muted-foreground">{t('dataset.noDatasets')}</p>}
          {Array.from(groups, ([scope, items]) => <div key={scope} className="grid gap-1">
            {!collapsed && <span className="truncate px-2 text-xs font-medium text-muted-foreground">{scopeName(items[0])}</span>}
            {items.map(item => {
              const entry = <Button key={item.id} asChild size={collapsed ? 'icon' : 'default'} variant={item.id === id ? 'secondary' : 'ghost'}
                className={cn('min-w-0', !collapsed && 'justify-start')}>
                <Link to={`/datasets/${item.id}`} aria-label={item.name} aria-current={item.id === id ? 'page' : undefined}>
                  <Table2 />{!collapsed && <span className="truncate">{item.name}</span>}
                </Link>
              </Button>
              return collapsed ? <Tooltip key={item.id}>
                <TooltipTrigger asChild>{entry}</TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>{item.name}</TooltipContent>
              </Tooltip> : entry
            })}
          </div>)}
          {catalog?.next_offset != null && <Tip tip={t('dataset.moreDatasets')}>
            <Button variant="outline" size={collapsed ? 'icon' : 'default'} aria-label={t('dataset.moreDatasets')}
              onClick={() => void loadCatalog(catalog.next_offset!)}>{collapsed ? <Plus /> : t('dataset.moreDatasets')}</Button>
          </Tip>}
        </div>
      </aside>
      <section className="min-w-0 space-y-3">
        {viewOnly && <p id="dataset-view-only" className="flex items-start gap-2 px-4 pt-4 text-sm text-muted-foreground md:px-6">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" /><span>{viewOnly}</span>
        </p>}
        {missing && <Empty className="m-4 w-auto border" data-testid="dataset-not-found">
          <EmptyHeader>
            <EmptyMedia variant="icon"><SearchX /></EmptyMedia>
            <EmptyTitle>{t('dataset.notFoundTitle')}</EmptyTitle>
            <EmptyDescription>{t('dataset.notFoundDescription')}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent><Button asChild variant="outline"><Link to="/datasets">{t('dataset.backToDatasets')}</Link></Button></EmptyContent>
        </Empty>}
        {detailError && !missing && <Alert variant="destructive" className="m-4 w-auto"><AlertDescription>{detailError}
          <Button variant="outline" onClick={reloadDataset}>{t('common.retry')}</Button>
        </AlertDescription></Alert>}
        {!id && catalog && !catalog.items.length && <Empty className="m-4 w-auto border" data-testid="dataset-empty">
          <EmptyHeader>
            <EmptyMedia variant="icon"><Table2 /></EmptyMedia>
            <EmptyTitle>{t('dataset.emptyTitle')}</EmptyTitle>
            <EmptyDescription>{t('dataset.emptyDescription')}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <div className="flex flex-wrap justify-center gap-2">
              <Button disabled={!editable} aria-describedby={viewOnly ? 'dataset-view-only' : undefined}
                onClick={() => setDatasetDialog('create')}><Plus />{t('dataset.createDataset')}</Button>
              <Button variant="outline" disabled={!editable} aria-describedby={viewOnly ? 'dataset-view-only' : undefined}
                onClick={() => setCsv({ initial: { name: '', teamId: null } })}><Upload />{t('dataset.importCsv')}</Button>
            </div>
            <span className="text-sm text-muted-foreground"><HandbookLink page="guide/datasets" label={t('dataset.learnMore')} /></span>
          </EmptyContent>
        </Empty>}
        {!current && !detailError && !(!id && catalog && !catalog.items.length) && <Card className="m-4 gap-2 p-4">
          <h2 className="font-medium">{id || !catalog ? t('common.loading') : t('dataset.selectDataset')}</h2>
          {!id && catalog && <p className="text-sm text-muted-foreground">{t('dataset.selectDatasetDescription')}</p>}
        </Card>}
        {current && <>
          <div className="flex items-start justify-between gap-2 px-4 pt-4 md:px-6">
            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground"><span>{scopeName(current)}</span><ChevronRight className="size-3" /><span>{t('dataset.title')}</span></div>
              <h2 className="break-words text-2xl font-semibold tracking-tight">{current.name}</h2>
              {current.description && <p className="break-words text-sm text-muted-foreground">{current.description}</p>}
            </div>
            <DatasetActionsMenu size="icon" label={t('dataset.datasetActions')} triggerRef={datasetMenu}
              schema={{ label: t('dataset.viewSchema'), onSelect: () => setSchemaId(current.id) }}
              edit={{ label: t('dataset.editDataset'), onSelect: () => setDatasetDialog('edit'), disabled: !manageable }}
              access={{ label: t('dataset.access'), onSelect: () => setAccessId(current.id), disabled: !manageable }}
              actions={[
                { icon: Upload, label: t('dataset.importCsv'), onSelect: () => setCsv({ dataset: current }), disabled: !editable },
                { icon: Download, label: t('dataset.exportCsv'), onSelect: () => { void exportCsv(current) } },
                ...(current.team_id && can(me, 'org.manage') ? [{ icon: UserRoundCog, label: t('dataset.transferOwner'), onSelect: () => setOwnerId(current.id) }] : []),
              ]}
              note={datasetNote}
              remove={{ label: t('dataset.deleteDataset'), onSelect: () => askDeleteDataset(current), disabled: !manageable }} />
          </div>
          {csvError && <Alert variant="destructive" className="mx-4"><AlertDescription>{csvError}</AlertDescription></Alert>}
          {csvNotice?.id === current.id && <p role="status" className="px-4 text-sm text-muted-foreground">{t('dataset.csvImported', { count: csvNotice.count })}</p>}
          <div className="border-t"><DatasetGrid viewOnlyId={viewOnly ? 'dataset-view-only' : undefined} key={`${current.id}-${gridFilter?.id === current.id ? gridFilter.seq : 0}`} dataset={current} editable={editable}
            reloadDataset={reloadDataset} initialFilters={gridFilter?.id === current.id ? gridFilter.filters : undefined} /></div>
          <Dialog open={schemaId === current.id} onOpenChange={open => { if (!open) setSchemaId(null) }}>
            <DialogContent showCloseButton={false} className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-3xl" onCloseAutoFocus={event => {
              event.preventDefault()
              datasetMenu.current?.focus()
            }}>
              <DialogHeader className="flex-row items-start justify-between gap-2 pr-0">
                <div className="min-w-0 space-y-1">
                  <DialogTitle>{t('dataset.schema')}</DialogTitle>
                  <DialogDescription className="wrap-anywhere">{current.name}</DialogDescription>
                  <p className="text-xs text-muted-foreground">{t('dataset.columnCount', { count: current.columns.length, max: 100 })}</p>
                  {datasetNote && <p id={`${current.id}-schema-note`} className="text-xs text-muted-foreground">{datasetNote}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button disabled={!manageable} aria-describedby={datasetNote ? `${current.id}-schema-note` : undefined}
                    onClick={() => setColumnDialog('new')}><Plus />{t('dataset.addColumn')}</Button>
                  <DialogClose asChild><Button variant="ghost" size="icon" aria-label={t('common.close')}><X /></Button></DialogClose>
                </div>
              </DialogHeader>
              <DialogBody>
                <div className="rounded-md border">
                  <Table aria-label={t('dataset.schema')}>
                    <TableHeader><TableRow>
                      <TableHead scope="col">{t('dataset.columnLabel')}</TableHead>
                      <TableHead scope="col">{t('dataset.fieldKey')}</TableHead>
                      <TableHead scope="col">{t('dataset.columnType')}</TableHead>
                      <TableHead scope="col">{t('dataset.constraints')}</TableHead>
                      <TableHead scope="col">{t('dataset.defaultValue')}</TableHead>
                      <TableHead scope="col"><span className="sr-only">{t('dataset.actions')}</span></TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {!current.columns.length && <TableRow><TableCell colSpan={6}>{t('dataset.noColumns')}</TableCell></TableRow>}
                      {current.columns.map(column => <TableRow key={column.key}>
                        <TableCell><div className="flex items-center gap-1.5"><DatasetFieldIcon kind={column.kind} />{column.label}</div></TableCell>
                        <TableCell className="font-mono">{column.key}</TableCell>
                        <TableCell>{t(`dataset.kind.${column.kind}`)}</TableCell>
                        <TableCell><div className="flex flex-wrap gap-1">
                          {column.required && <Badge variant="outline">{t('dataset.required')}</Badge>}
                          {column.unique && <Badge variant="outline">{t('dataset.unique')}</Badge>}
                        </div></TableCell>
                        <TableCell>{displayValue(column.default, t('dataset.valueTrue'), t('dataset.valueFalse'))}</TableCell>
                        <TableCell><div className="flex gap-1">
                          <Button variant="ghost" size="icon-sm" disabled={!manageable} aria-describedby={datasetNote ? `${current.id}-schema-note` : undefined}
                            aria-label={t('dataset.editColumnNamed', { name: column.label })} onClick={() => setColumnDialog(column)}><Pencil /></Button>
                          <Button variant="ghost" size="icon-sm" className="text-destructive" disabled={!manageable}
                            aria-describedby={datasetNote ? `${current.id}-schema-note` : undefined}
                            aria-label={t('dataset.deleteColumn')} onClick={() => askDeleteColumn(current, column)}><Trash2 /></Button>
                        </div></TableCell>
                      </TableRow>)}
                    </TableBody>
                  </Table>
                </div>
              </DialogBody>
            </DialogContent>
          </Dialog>
        </>}
      </section>
    </main>
    {datasetDialog && (datasetDialog === 'create' || current) && <DatasetFormDialog dataset={datasetDialog === 'edit' ? current ?? undefined : undefined}
      teams={teams} onClose={() => setDatasetDialog(null)} onSave={saveDataset}
      onImportCsv={initial => { setDatasetDialog(null); setCsv({ initial }) }} />}
    {csv && <DatasetCsvDialog dataset={csv.dataset} initial={csv.initial} teams={teams} onClose={() => setCsv(null)}
      onImported={(data, count) => {
        setCsv(null)
        setCsvNotice({ id: data.id, count })
        saveDataset(data)
      }} />}
    {current && columnDialog && <DatasetColumnDialog dataset={current} column={columnDialog === 'new' ? undefined : columnDialog}
      onClose={() => setColumnDialog(null)} onSave={data => { setDataset(data); setColumnDialog(null) }}
      onShowDuplicates={({ field, value }) => {
        setColumnDialog(null)
        setSchemaId(null)
        setGridFilter(previous => ({ id: current.id, seq: (previous?.seq ?? 0) + 1, filters: { mode: 'and', rules: [{ field, op: 'eq', value }] } }))
      }} />}
    {current && ownerId === current.id && <DatasetOwnerDialog dataset={current} onClose={() => setOwnerId(null)}
      onSave={data => { saveDataset(data); setOwnerId(null) }} />}
    {current && accessId === current.id && <DatasetAccessDialog dataset={current} scope={scopeName(current)} onClose={() => setAccessId(null)} />}
    {confirm.dialog}
  </div>
}
