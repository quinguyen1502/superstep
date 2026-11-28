import { Fragment, useEffect, useEffectEvent, useId, useLayoutEffect, useMemo, useRef, useState, type ClipboardEvent, type CSSProperties, type KeyboardEvent, type RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import {
  cellSelectionFeature, columnGroupingFeature, columnOrderingFeature, columnPinningFeature, columnResizingFeature, columnSizingFeature,
  columnVisibilityFeature, rowExpandingFeature, rowPaginationFeature, rowSelectionFeature, rowSortingFeature,
  tableFeatures, useTable, type CellSelectionDirection, type ColumnPinningState, type ColumnVisibilityState, type ExpandedState, type GroupingState,
  type ColumnOrderState, type ColumnSizingState, type PaginationState, type RowSelectionState, type SortingState, type Updater,
} from '@tanstack/react-table'
import { defaultRangeExtractor, useVirtualizer } from '@tanstack/react-virtual'
import { CircleAlert, ArrowDown, ArrowUp, ArrowUpDown, Check, ChevronDown, ChevronLeft, ChevronRight, ExternalLink, Clipboard, Keyboard, Pin, PinOff, Plus, Rows2, Rows3, Rows4, Search, Settings2, Sigma, Ungroup, WifiOff, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Checkbox } from '@/components/ui/checkbox'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import { Label } from '@/components/ui/label'
import { Popover, PopoverAnchor, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { ShortcutCheatsheet } from '@/components/shortcut-cheatsheet'
import { api, ApiError } from '@/lib/api'
import { datasetFormulaError, DATASET_QUERY_LIMIT, datasetGroupable, datasetSummaryFunctions, datasetReadOnly, datasetTextKind, datasetUrl, deleteRowName, displayColumnValue, displayValue, emptyDatasetFilters, keepDatasetFilterFields, type DatasetFilters, type DatasetGroupsPage, type DatasetRowGroup, type CellValue, type Dataset, type DatasetColumn, type DatasetColumnSummaries, type DatasetSummaryResult, type DatasetKind, type DatasetRow, type DatasetRowPage, type DatasetRowResult } from '@/lib/datasets'
import { errorText, type ApiErrorBody } from '@/lib/i18n'
import { datasetClipboardRows, datasetClipboardText, datasetClipboardValue, type DatasetBatchResult, type DatasetBatchRow } from '@/lib/dataset-clipboard'
import { cn } from '@/lib/utils'
import { useShortcuts } from '@/lib/use-shortcuts'
import type { Shortcut } from '@/lib/shortcuts'
import { DatasetColumnSummary } from './dataset-column-summary'
import { DatasetActionsMenu } from './dataset-actions-menu'
import { DatasetRowDialog } from './dataset-dialogs'
import { DatasetColumnControls, DatasetUniqueBadge } from './dataset-column-controls'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetValueField } from './dataset-fields'
import { DatasetQueryControls } from './dataset-query-controls'
import { DatasetRelationPicker } from './dataset-relation-picker'
import { useDatasetRelationLabels } from './use-dataset-relations'
import { isDatasetAccessError, useDatasetLive } from './use-dataset-live'

const NO_ROWS: DatasetRow[] = []
const features = tableFeatures({
  cellSelectionFeature, columnGroupingFeature, columnOrderingFeature, columnPinningFeature, columnSizingFeature, columnResizingFeature,
  columnVisibilityFeature, rowExpandingFeature, rowPaginationFeature, rowSelectionFeature, rowSortingFeature,
})
type Edit = { row: DatasetRow; column: DatasetColumn; value: CellValue; schemaRevision: number }
type Cell = { row: string; column: string }
const DIRECTIONS: Record<string, CellSelectionDirection> = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' }
const MOVEMENT: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }
const DIVIDER = 'border-e border-border'
const CELL_BUTTON = 'w-full justify-start rounded-none hover:bg-transparent dark:hover:bg-transparent'
const CELL_RANGE_BACKGROUND = 'bg-[color-mix(in_oklch,var(--foreground)_8%,var(--background))]'
const MIN_COLUMN_WIDTH = 100
const MAX_COLUMN_WIDTH = 4096
const ROW_NUMBER_WIDTH = 56
const ROW_ID_WIDTH = 112
const ROW_ACTIONS_WIDTH = 80
const HEIGHTS = { short: 32, medium: 40, tall: 56 }
const ROW_HEIGHT_ICONS = { short: Rows4, medium: Rows3, tall: Rows2 }
type GridRowHeight = keyof typeof HEIGHTS
const DEFAULT_WIDTH: Record<DatasetKind, number> = { text: 200, number: 120, boolean: 104, date: 152, datetime: 216, email: 232, select: 160, long_text: 320, url: 250, created_time: 216, updated_time: 216, multi_select: 240, auto_number: 140, relation: 200 }
const PAGE_SIZES = [25, 50, 100]
const SHORTCUT_HELP: Shortcut[] = [{ id: 'cheatsheet', keys: ['?', 'mod+/'], group: 'general' }]
const DATASET_VIEW_SHORTCUTS: Shortcut[] = [
  ...SHORTCUT_HELP,
  { id: 'datasetMove', keys: ['arrows'], group: 'general' },
  { id: 'datasetSelectRange', keys: ['shift+arrows'], group: 'general' },
  { id: 'copyCells', keys: ['mod+c'], group: 'clipboard', labelKey: 'dataset.clipboardCopy' },
]
const DATASET_EDIT_SHORTCUTS: Shortcut[] = [
  ...DATASET_VIEW_SHORTCUTS,
  { id: 'datasetEdit', keys: ['enter', 'f2'], group: 'general' },
  { id: 'datasetSaveEdit', keys: ['enter'], group: 'general' },
  { id: 'datasetSaveText', keys: ['mod+enter'], group: 'general' },
  { id: 'datasetDiscardEdit', keys: ['escape'], group: 'general' },
  { id: 'pasteCells', keys: ['mod+v'], group: 'clipboard', labelKey: 'dataset.clipboardPaste' },
  { id: 'fillDown', keys: ['mod+d'], group: 'clipboard', labelKey: 'dataset.clipboardFillDown' },
  { id: 'fillRight', keys: ['mod+r'], group: 'clipboard', labelKey: 'dataset.clipboardFillRight' },
  { id: 'undoBatch', keys: ['mod+z'], group: 'clipboard', labelKey: 'dataset.clipboardUndo' },
]

function readLayout(key: string): { order?: ColumnOrderState; sizes?: ColumnSizingState; visibility?: ColumnVisibilityState; summaries?: DatasetColumnSummaries; showSummaries?: boolean; groupBy?: string; pinned?: string[]; rowHeight?: GridRowHeight } {
  try {
    return JSON.parse(localStorage.getItem(key) ?? '{}') ?? {}
  } catch {
    return {}
  }
}

const GROUP_PAGE_SIZE = 50
const SNAPSHOT_RETRY = 5_000

function queryRows(url: string, request: string, offset: number, signal: AbortSignal) {
  const query = JSON.parse(request)
  return api<DatasetRowPage>(url, { method: 'POST', json: { ...query, offset }, signal })
}
const groupKey = (value: CellValue) => JSON.stringify(value)

const ROW_INDEX = 'sticky start-0 z-20 border-e border-border bg-background'
const ROW_ACTIONS = 'sticky end-0 z-20 border-s border-border bg-background'

function inDatasetCell(target: EventTarget | null) {
  return target instanceof Element && !!target.closest('[data-dataset-cell]')
}

function inDatasetCalendar(target: EventTarget | null) {
  return target instanceof Element && !!target.closest('[data-dataset-calendar]')
}


function inEditorPopup(target: EventTarget | null) {
  return inDatasetCalendar(target) || (target instanceof Element && !!target.closest('[data-dataset-editor-popup]'))
}

function inCellPreview(target: EventTarget | null) {
  return target instanceof Element && !!target.closest('[data-dataset-cell-preview]')
}

function DatasetCellPreview({ anchor, content, value, className, onClose }: {
  anchor: RefObject<HTMLTableCellElement | null>
  content: RefObject<HTMLDivElement | null>
  value: string
  className: string
  onClose: () => void
}) {
  const [truncated, setTruncated] = useState(false)
  useEffect(() => {
    const label = anchor.current?.querySelector('[data-dataset-cell-label]')
    if (!label) return
    const observer = new ResizeObserver(() => setTruncated(label.scrollWidth > label.clientWidth))
    observer.observe(label)
    return () => observer.disconnect()
  }, [anchor, value])

  if (!truncated && !value.includes('\n')) return null
  return <Popover open onOpenChange={open => { if (!open) onClose() }}>
    <PopoverAnchor virtualRef={anchor} />
    <PopoverContent ref={content} data-dataset-cell-preview="" aria-hidden="true"
      // Overlap the focus outline at the join, including its 2px keyboard state.
      side="bottom" align="start" sideOffset={-2} collisionPadding={8} hideWhenDetached
      className={cn('max-h-[min(9rem,var(--radix-popover-content-available-height,9rem))] w-(--radix-popover-trigger-width) min-w-0 max-w-(--radix-popover-content-available-width) overflow-y-auto overscroll-contain rounded-none border border-foreground p-2 leading-normal wrap-anywhere whitespace-pre-wrap text-foreground shadow-none ring-0 data-[side=bottom]:border-t-0 data-[side=top]:border-b-0', className)}
      onOpenAutoFocus={event => event.preventDefault()}
      onCloseAutoFocus={event => event.preventDefault()}
      onInteractOutside={event => { if (event.target instanceof Node && anchor.current?.contains(event.target)) event.preventDefault() }}
      onMouseDown={event => event.preventDefault()}>
      {value}
    </PopoverContent>
  </Popover>
}

export function DatasetGrid({ dataset, editable, reloadDataset, readDataset, onAccessLost, initialFilters, viewOnlyId }: {
  dataset: Dataset
  editable: boolean
  viewOnlyId?: string
  reloadDataset: () => void
  readDataset: (id: string, signal: AbortSignal) => Promise<Dataset>
  onAccessLost: () => void
  initialFilters?: DatasetFilters
}) {
  const { t } = useTranslation()
  const editId = useId()
  const addButton = useRef<HTMLButtonElement>(null)
  const gridViewport = useRef<HTMLDivElement>(null)
  const gridFooter = useRef<HTMLDivElement>(null)
  const draftRow = useRef<HTMLTableRowElement>(null)
  const inlineEditor = useRef<HTMLFormElement>(null)
  const previewAnchor = useRef<HTMLTableCellElement>(null)
  const relationAnchor = useRef<HTMLTableCellElement>(null)
  const previewContent = useRef<HTMLDivElement>(null)
  const [selectingCells, setSelectingCells] = useState(false)
  const saving = useRef(false)
  const restoreEditorFocus = useRef(false)
  const restoreCellFocus = useRef<string | null>(null)
  const unlinkFocus = useRef<string | null>(null)
  const confirm = useConfirmDelete(undefined, () => {
    const target = unlinkFocus.current
    unlinkFocus.current = null
    if (target) requestAnimationFrame(() => document.getElementById(target)?.focus())
  })
  const [autoOffset, setAutoOffset] = useState<number | null>(null)
  const [autoPage, setAutoPage] = useState<DatasetRowPage | null>(null)
  const [page, setPage] = useState<DatasetRowPage | null>(null)
  const [loadError, setLoadError] = useState('')
  const [batchBusy, setBatchBusy] = useState(false)
  const batchLock = useRef(false)
  const [batchError, setBatchError] = useState('')
  const [undo, setUndo] = useState<{ revision: number; rows: DatasetBatchRow[]; remove: Record<string, number> } | null>(null)
  const [pastePreview, setPastePreview] = useState<{ updates: DatasetBatchRow[]; append: Record<string, CellValue>[] } | null>(null)
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [searchText, setSearchText] = useState('')
  const [filters, setFilters] = useState<DatasetFilters>(initialFilters ?? emptyDatasetFilters())
  const [sorting, setSorting] = useState<SortingState>([])
  const [offsets, setOffsets] = useState([0])
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 50 })
  const [refresh, setRefresh] = useState(0)
  const [snapshotError, setSnapshotError] = useState(false)
  const [snapshotRunning, setSnapshotRunning] = useState(false)
  const completedSnapshot = useRef('')
  const completedQuery = useRef('')
  const [selection, setSelection] = useState<RowSelectionState>({})
  const layoutKey = `studio-dataset-layout:${dataset.id}`
  const [storedLayout] = useState(() => readLayout(layoutKey))
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibilityState>(storedLayout.visibility ?? {})
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>(storedLayout.order ?? [])
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>(storedLayout.sizes ?? {})
  const [pinning, setPinning] = useState<ColumnPinningState>({
    start: Array.isArray(storedLayout.pinned) ? storedLayout.pinned.slice(0, 3) : [],
    end: [],
  })
  const [rowHeight, setRowHeight] = useState<GridRowHeight>(
    storedLayout.rowHeight && Object.hasOwn(HEIGHTS, storedLayout.rowHeight) ? storedLayout.rowHeight : 'medium',
  )
  const [summaryOperations, setSummaryOperations] = useState<DatasetColumnSummaries>(storedLayout.summaries ?? {})
  const [showSummaries, setShowSummaries] = useState(storedLayout.showSummaries ?? false)
  const [grouping, setGrouping] = useState<GroupingState>(storedLayout.groupBy ? [storedLayout.groupBy] : [])
  const groupColumn = dataset.columns.find(column => column.key === grouping[0] && datasetGroupable(column.kind))
  const [expanded, setExpanded] = useState<ExpandedState>({})
  const selectedGroup = expanded === true ? undefined : Object.keys(expanded).find(key => expanded[key])
  const [groupOffset, setGroupOffset] = useState(0)
  const [groupResult, setGroupResult] = useState<{ request: string; data: DatasetGroupsPage } | null>(null)
  const [groupsError, setGroupsError] = useState<{ request: string; message: string } | null>(null)
  const [summary, setSummary] = useState<{ key: string; data: DatasetSummaryResult } | null>(null)
  const [summaryError, setSummaryError] = useState<{ key: string; message: string } | null>(null)
  useEffect(() => {
    try {
      localStorage.setItem(layoutKey, JSON.stringify({ order: columnOrder, sizes: columnSizing, visibility: columnVisibility, summaries: summaryOperations, showSummaries, groupBy: grouping[0], pinned: pinning.start, rowHeight }))
    } catch {
      // The grid remains usable when browser storage is unavailable.
    }
  }, [columnOrder, columnSizing, columnVisibility, grouping, layoutKey, pinning, rowHeight, showSummaries, summaryOperations])
  const [viewportWidth, setViewportWidth] = useState(0)
  const [headerHeight, setHeaderHeight] = useState(0)
  const [active, setActive] = useState<Cell | null>(null)
  const [draft, setDraft] = useState<Record<string, CellValue> | null>(null)
  const [draftError, setDraftError] = useState('')
  const [draftBusy, setDraftBusy] = useState(false)
  const [edit, setEdit] = useState<Edit | null>(null)
  const [rowDetails, setRowDetails] = useState<DatasetRow | null>(null)
  const [saveError, setSaveError] = useState<{ message: string; field?: boolean; notice?: boolean } | null>(null)
  const [stale, setStale] = useState(false)
  const [busy, setBusy] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const editing = !!edit || !!draft || !!rowDetails || !!pastePreview || batchBusy
  const live = useDatasetLive(dataset.id, onAccessLost)
  const [snapshotRevision, setSnapshotRevision] = useState(live.revision)
  // Keep only the latest pending marker while reading pages or preserving an editor draft.
  useEffect(() => {
    if (!editing && !snapshotRunning && autoOffset === null && live.revision) setSnapshotRevision(live.revision)
  }, [autoOffset, editing, live.revision, snapshotRunning])
  const canRead = snapshotRevision !== null || live.delayed
  useShortcuts({ cheatsheet: () => {
    if (editing) return false
    setShortcutsOpen(true)
  } }, SHORTCUT_HELP)
  const addingRow = !!draft
  const pageIndex = pagination.pageIndex
  const offset = offsets[pageIndex] ?? 0
  const url = `${datasetUrl(dataset.id)}/rows`
  const layout = useMemo(() => {
    const remainingFields = new Map(dataset.columns.map(column => [column.key, column]))
    const orderedFields: DatasetColumn[] = []
    for (const key of columnOrder) {
      const field = remainingFields.get(key)
      if (field) orderedFields.push(field)
      remainingFields.delete(key)
    }
    orderedFields.push(...remainingFields.values())
    const selectedFields = orderedFields.filter(column => columnVisibility[column.key] !== false)
    const showAll = addingRow || !selectedFields.length
    const fields = showAll ? orderedFields : selectedFields
    const showRowId = !dataset.columns.some(column => column.unique)
    const fixedWidth = ROW_NUMBER_WIDTH + (showRowId ? ROW_ID_WIDTH : 0) + ROW_ACTIONS_WIDTH
    const defaultWidth = (column: DatasetColumn) => Math.max(column.unique ? 160 : 0, DEFAULT_WIDTH[column.kind])
    const fieldWidth = (column: DatasetColumn) => Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, columnSizing[column.key] ?? defaultWidth(column)))
    const minimumWidth = fields.reduce((width, column) => width + fieldWidth(column), fixedWidth)
    const remaining = Math.max(0, viewportWidth - minimumWidth)
    const last = fields.at(-1)
    const fill = last && !Object.hasOwn(columnSizing, last.key) ? last : undefined
    const fillWidth = fill ? Math.min(remaining, MAX_COLUMN_WIDTH - defaultWidth(fill)) : 0
    return {
      fields, orderedFields, showRowId, width: Math.max(viewportWidth, minimumWidth),
      visibility: showAll ? {} : columnVisibility,
      columns: dataset.columns.map(column => ({
        id: column.key, accessorFn: (row: DatasetRow) => row.values[column.key],
        footer: column.key,
        size: defaultWidth(column) + (fill?.key === column.key ? fillWidth : 0),
      })),
    }
  }, [addingRow, columnOrder, columnSizing, columnVisibility, dataset.columns, viewportWidth])

  const summaryColumns = useMemo(() => Object.fromEntries(layout.fields.flatMap(column => {
    const operation = summaryOperations[column.key]
    return operation && datasetSummaryFunctions(column.kind).includes(operation) ? [[column.key, operation]] : []
  })), [layout.fields, summaryOperations])
  const summaryRequest = useMemo(() => {
    const tree = keepDatasetFilterFields(filters, new Set(dataset.columns.map(column => column.key)))
    return {
      search: search || null, ...(tree.children.length ? { filter_tree: tree } : {}),
      summaries: summaryColumns,
    }
  }, [dataset.columns, filters, search, summaryColumns])

  const summaryQuery = showSummaries && Object.keys(summaryColumns).length ? JSON.stringify(summaryRequest) : null
  const summaryKey = JSON.stringify([dataset.revision, summaryQuery])
  const currentSummaryError = summaryError?.key === summaryKey ? summaryError.message : null
  const currentSummary = summary?.key === summaryKey ? summary.data : null
  const groupsRequest = groupColumn ? JSON.stringify({
    ...summaryRequest, summaries: showSummaries ? summaryColumns : {},
    group_by: groupColumn.key, offset: groupOffset, limit: GROUP_PAGE_SIZE,
  }) : null
  const groupsRequestKey = JSON.stringify([dataset.revision, groupsRequest])
  const groups = groupResult?.request === groupsRequestKey ? groupResult.data : null
  const groupError = groupsError?.request === groupsRequestKey ? groupsError.message : null

  const rowsQuery = !groupColumn || selectedGroup !== undefined ? JSON.stringify({
    search: summaryRequest.search,
    ...(summaryRequest.filter_tree ? { filter_tree: summaryRequest.filter_tree } : {}),
    sorts: sorting.filter(rule => dataset.columns.some(field => field.key === rule.id))
      .map(rule => ({ field: rule.id, descending: rule.desc })),
    ...(groupColumn && selectedGroup !== undefined ? { group_by: groupColumn.key, group: JSON.parse(selectedGroup) as CellValue } : {}),
    limit: pagination.pageSize,
  }) : null
  const rowQueryUrl = `${url}/${groupColumn ? 'groups/query' : 'query'}`
  const loadedRows = useEffectEvent(() => autoPage?.items.length ?? 0)
  const canCommitSnapshot = useEffectEvent(() => !editing)
  const rememberFocusedCell = useEffectEvent(() => {
    const focused = document.activeElement
    if (active && focused?.id === cellId(active.row, active.column)) restoreCellFocus.current = focused.id
  })
  const [retry, setRetry] = useState(0)
  const queryKey = JSON.stringify([dataset.revision, refresh, rowsQuery, offset, summaryKey, groupsRequestKey])
  const snapshotKey = JSON.stringify([queryKey, snapshotRevision, retry])
  useEffect(() => {
    if (!canRead || editing || completedSnapshot.current === snapshotKey) {
      setSnapshotRunning(false)
      return
    }
    const controller = new AbortController()
    const { signal } = controller
    let retryTimer: number | undefined
    const keepRowCount = loadedRows()
    setSnapshotRunning(true)
    const fetchRows = async (request: string) => {
      const first = await queryRows(rowQueryUrl, request, offset, signal)
      let joined = first
      while (joined.next_offset !== null && joined.items.length < keepRowCount && joined.schema_revision === dataset.revision) {
        const next = await queryRows(rowQueryUrl, request, joined.next_offset, signal)
        if (next.schema_revision !== dataset.revision) return { first: next, joined: next }
        joined = { ...next, items: [...joined.items, ...next.items] }
      }
      return { first, joined }
    }
    const retrySnapshot = () => {
      setSnapshotError(true)
      retryTimer = window.setTimeout(() => setRetry(count => count + 1), SNAPSHOT_RETRY)
    }
    const checkAccess = <T,>(request: Promise<T>) => request.catch(error => {
      if (!signal.aborted && isDatasetAccessError(error)) {
        controller.abort()
        onAccessLost()
      }
      throw error
    })
    async function readSnapshot() {
      if (snapshotRevision && snapshotRevision.schema_revision !== dataset.revision) {
        const definition = await readDataset(dataset.id, signal)
        if (signal.aborted || definition.revision !== dataset.revision) return
      }
      const [rowsResult, groupsResult, summaryResult] = await Promise.allSettled([
        rowsQuery ? checkAccess(fetchRows(rowsQuery)) : null,
        groupsRequest ? checkAccess(api<DatasetGroupsPage>(`${url}/groups`, {
          method: 'POST', json: JSON.parse(groupsRequest), signal,
        })) : null,
        summaryQuery ? checkAccess(api<DatasetSummaryResult>(`${url}/summary`, {
          method: 'POST', json: JSON.parse(summaryQuery), signal,
        })) : null,
      ])
      if (signal.aborted || !canCommitSnapshot()) return
      const nextRows = rowsResult.status === 'fulfilled' ? rowsResult.value : null
      const nextGroups = groupsResult.status === 'fulfilled' ? groupsResult.value : null
      const nextSummary = summaryResult.status === 'fulfilled' ? summaryResult.value : null
      if ([nextRows?.first, nextGroups, nextSummary].some(result => result && result.schema_revision !== dataset.revision)) {
        const definition = await readDataset(dataset.id, signal)
        if (!signal.aborted && definition.revision === dataset.revision) retrySnapshot()
        return
      }
      const failed = rowsResult.status === 'rejected' || groupsResult.status === 'rejected' || summaryResult.status === 'rejected'
      if (failed && completedQuery.current === queryKey && snapshotRevision) {
        retrySnapshot()
        return
      }
      if (nextRows) {
        rememberFocusedCell()
        if (!nextRows.first.items.length && pageIndex > 0) {
          setPagination(current => ({ ...current, pageIndex: Math.min(current.pageIndex - 1,
            Math.floor(Math.max(0, nextRows.first.total - 1) / current.pageSize)) }))
        }
        setPage(nextRows.first)
        setAutoPage(nextRows.joined === nextRows.first ? null : nextRows.joined)
        setLoadError('')
      } else if (rowsResult.status === 'rejected') setLoadError(rowsResult.reason.message)
      if (nextGroups) {
        if (!nextGroups.groups.length && groupOffset > 0) {
          setGroupOffset(0)
          setExpanded({})
          setPage(null)
        } else if (selectedGroup !== undefined && !nextGroups.groups.some(group => groupKey(group.group) === selectedGroup)) {
          setExpanded({})
          setPage(null)
        }
        setGroupResult({ request: groupsRequestKey, data: nextGroups })
        setGroupsError(null)
      } else if (groupsResult.status === 'rejected') setGroupsError({ request: groupsRequestKey, message: groupsResult.reason.message })
      if (nextSummary) {
        setSummary({ key: summaryKey, data: nextSummary })
        setSummaryError(null)
      } else if (summaryResult.status === 'rejected') setSummaryError({ key: summaryKey, message: summaryResult.reason.message })
      if (!failed) {
        completedSnapshot.current = snapshotKey
        completedQuery.current = queryKey
        setSnapshotError(false)
      }
    }
    void readSnapshot().catch(error => {
      if (signal.aborted) return
      if (isDatasetAccessError(error)) onAccessLost()
      else retrySnapshot()
    }).finally(() => { if (!signal.aborted) setSnapshotRunning(false) })
    return () => { controller.abort(); clearTimeout(retryTimer) }
  }, [canRead, dataset.id, dataset.revision, editing, groupOffset, groupsRequest, groupsRequestKey,
    offset, onAccessLost, pageIndex, queryKey, readDataset, rowQueryUrl, rowsQuery, selectedGroup, snapshotKey, snapshotRevision, summaryKey, summaryQuery, url])

  useLayoutEffect(() => {
    const id = restoreCellFocus.current
    restoreCellFocus.current = null
    if (id && document.activeElement === document.body) document.getElementById(id)?.focus({ preventScroll: true })
  }, [autoPage, page])

  useLayoutEffect(() => {
    if (busy || !restoreEditorFocus.current) return
    restoreEditorFocus.current = false
    if (edit) document.getElementById(editId)?.focus()
  }, [busy, edit, editId])

  useEffect(() => {
    const viewport = gridViewport.current
    const footer = gridFooter.current
    const header = viewport?.querySelector('thead')
    if (!viewport || !footer || !header) return
    let frame = 0
    const scheduleMeasure = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const gridTop = viewport.getBoundingClientRect().top + window.scrollY + viewport.clientTop
        viewport.style.setProperty('--dataset-scroll-height', `${window.innerHeight - gridTop - footer.offsetHeight}px`)
        setViewportWidth(viewport.clientWidth)
        setHeaderHeight(header.offsetHeight)
      })
    }
    const observer = new ResizeObserver(scheduleMeasure)
    observer.observe(viewport)
    observer.observe(header)
    observer.observe(footer)
    observer.observe(document.body)
    window.addEventListener('resize', scheduleMeasure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', scheduleMeasure)
      cancelAnimationFrame(frame)
    }
  }, [])

  // oxlint-disable-next-line react/incompatible-library -- The table instance stays within this component.
  const displayPage = autoPage ?? page
  const table = useTable({
    features,
    autoResetCellSelection: false,
    data: displayPage?.items ?? NO_ROWS, columns: layout.columns, getRowId: row => row.id,
    manualSorting: true, manualPagination: true, manualGrouping: true, manualExpanding: true, groupedColumnMode: false, rowCount: page?.total, maxMultiSortColCount: DATASET_QUERY_LIMIT,
    defaultColumn: { minSize: MIN_COLUMN_WIDTH, maxSize: MAX_COLUMN_WIDTH },
    state: { pagination, sorting, grouping, expanded, rowSelection: selection, columnOrder, columnVisibility: layout.visibility, columnSizing, columnPinning: pinning },
    onPaginationChange: setPagination, onGroupingChange: setGrouping, onExpandedChange: setExpanded,
    onRowSelectionChange: setSelection, onSortingChange: changeSorting,
    onColumnVisibilityChange: updater => setColumnVisibility(typeof updater === 'function' ? updater(layout.visibility) : updater),
    onColumnSizingChange: setColumnSizing, onColumnPinningChange: setPinning,
  })
  useEffect(() => {
    function keepInvalidEditorFocused(event: MouseEvent) {
      const form = inlineEditor.current
      const target = event.target
      if (!form || !(target instanceof Node) || form.contains(target) || inEditorPopup(target)) return false
      const invalid = !form.checkValidity() || (saveError && !saveError.notice)
      if (!invalid) return false
      event.preventDefault()
      event.stopPropagation()
      document.getElementById(editId)?.focus({ preventScroll: true })
      return true
    }

    function clearOutsideCell(event: PointerEvent) {
      if (keepInvalidEditorFocused(event)) return
      const target = event.target
      if (target instanceof Element && (inEditorPopup(target) || inCellPreview(target)
        || target.closest('[data-dataset-clipboard]')
        || (gridViewport.current?.contains(target) && inDatasetCell(target)))) return
      setActive(null)
      if (table.getFocusedCell()) table.resetCellSelection(true)
    }
    const endCellSelection = () => setSelectingCells(false)
    document.addEventListener('pointerdown', clearOutsideCell, true)
    document.addEventListener('click', keepInvalidEditorFocused, true)
    document.addEventListener('mouseup', endCellSelection)
    window.addEventListener('blur', endCellSelection)
    return () => {
      document.removeEventListener('pointerdown', clearOutsideCell, true)
      document.removeEventListener('click', keepInvalidEditorFocused, true)
      document.removeEventListener('mouseup', endCellSelection)
      window.removeEventListener('blur', endCellSelection)
    }
  }, [table, editId, saveError])
  const rows = table.getRowModel().rows
  const scrollViewport = () => gridViewport.current?.querySelector<HTMLDivElement>('[data-slot="table-container"]') ?? null
  const useVirtualRows = !groupColumn && rows.length > 25
  const virtualizer = useVirtualizer({
    count: useVirtualRows ? rows.length : 0,
    getScrollElement: scrollViewport,
    estimateSize: () => HEIGHTS[rowHeight],
    scrollMargin: headerHeight,
    overscan: 8,
    getItemKey: index => rows[index]?.id ?? index,
    rangeExtractor: range => {
      const indices = defaultRangeExtractor(range)
      const current = rows.findIndex(row => row.id === (edit?.row.id ?? active?.row))
      return current < 0 || indices.includes(current) ? indices : [...indices, current].sort((a, b) => a - b)
    },
  })
  const virtualRows = virtualizer.getVirtualItems()
  const relationRows = useVirtualRows ? virtualRows.flatMap(item => rows[item.index] ? [rows[item.index].original] : [])
    : displayPage?.items ?? NO_ROWS
  const relationLabels = useDatasetRelationLabels(dataset, layout.fields, relationRows, `${snapshotKey}:${refresh}`)
  useEffect(() => {
    if (autoOffset === null || groupColumn || !rowsQuery) return
    const controller = new AbortController()
    void queryRows(rowQueryUrl, rowsQuery, autoOffset, controller.signal).then(result => {
      if (controller.signal.aborted) return
      if (result.schema_revision !== dataset.revision) { reloadDataset(); return }
      setAutoPage(current => {
        const previous = current ?? page
        return previous ? { ...result, items: [...previous.items, ...result.items] } : result
      })
    }).catch(error => {
      if (controller.signal.aborted) return
      if (isDatasetAccessError(error)) onAccessLost()
      else setLoadError(error.message)
    }).finally(() => {
      if (!controller.signal.aborted) setAutoOffset(null)
    })
    return () => controller.abort()
  }, [autoOffset, dataset.revision, groupColumn, onAccessLost, page, reloadDataset, rowQueryUrl, rowsQuery])

  function clearAutoPages() {
    setAutoOffset(null)
    setAutoPage(null)
    const viewport = scrollViewport()
    if (viewport) viewport.scrollTop = 0
  }

  function loadMoreOnScroll() {
    if (!useVirtualRows || editing || loadError || snapshotRunning || autoOffset !== null || displayPage?.next_offset == null) return
    const viewport = scrollViewport()
    if (viewport && viewport.scrollTop > 0 && viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < HEIGHTS[rowHeight] * 4) {
      setAutoOffset(displayPage.next_offset)
    }
  }
  const pinnedStyle = (column: (ReturnType<typeof table.getVisibleLeafColumns>)[number]): CSSProperties | undefined =>
    column.getIsPinned() === 'start' ? { insetInlineStart: ROW_NUMBER_WIDTH + column.getStart('start') } : undefined
  const orderedVisible = [
    ...table.getStartVisibleLeafColumns(), ...table.getCenterVisibleLeafColumns(), ...table.getEndVisibleLeafColumns(),
  ]
  const selectedCount = rows.filter(row => row.getIsSelected()).length
  const selectedCell = active && rows.some(row => row.id === active.row) && layout.fields.some(column => column.key === active.column)
    ? active : null
  const showCellPreview = !editing && !selectingCells && selectedCell && table.getSelectedCellCount() <= 1
  const tabStop = selectedCell ?? { row: rows[virtualRows[0]?.index ?? 0]?.id, column: orderedVisible[0]?.id }

  function changeSorting(updater: Updater<SortingState>) {
    if (edit || draft) return
    const next = typeof updater === 'function' ? updater(sorting) : updater
    if (next.length === sorting.length && next.every((rule, index) => rule.id === sorting[index].id && rule.desc === sorting[index].desc)) return
    setSorting(next)
    setSelection({})
    resetPaging()
    setPage(null)
  }

  useEffect(() => {
    const next = searchText.trim()
    if (editing || next === search) return
    const timer = window.setTimeout(() => {
      setSearch(next)
      if (groupColumn) { setExpanded({}); setGroupOffset(0); setPage(null) }
      resetPaging()
      setSelection({})
    }, 250)
    return () => window.clearTimeout(timer)
  }, [editing, groupColumn, search, searchText])

  function reload() {
    setAutoOffset(null)
    setLoadError('')
    setRefresh(current => current + 1)
  }

  function applyFilters(next: DatasetFilters) {
    if (edit || draft) return
    resetPaging()
    setSelection({})
    setFilters(next)
    if (groupColumn) { setExpanded({}); setGroupOffset(0); setPage(null) }
    reload()
  }

  const cellId = (row: string, column: string) => `${editId}-cell-${row}-${column}`
  const rowActionId = (row: string) => `${editId}-actions-${row}`

  function closeEditor(restoreFocus = true) {
    setEdit(null)
    setSaveError(null)
    setStale(false)
    if (restoreFocus && edit) window.requestAnimationFrame(() => document.getElementById(cellId(edit.row.id, edit.column.key))?.focus())
  }

  function canEditCell(column: DatasetColumn, value: CellValue) {
    return editable && (column.kind === 'relation' ? !!dataset.relation_config_enabled || value !== null : !datasetReadOnly(column))
  }

  function beginEdit(row: DatasetRow, column: DatasetColumn) {
    const value = row.values[column.key] ?? null
    if (editing || saving.current || !canEditCell(column, value)) return
    setActive({ row: row.id, column: column.key })
    setSaveError(null)
    setStale(false)
    setEdit({ row, column, value, schemaRevision: dataset.revision })
  }

  async function applyBatch(updates: DatasetBatchRow[], previous = false, append: Record<string, CellValue>[] = []) {
    if (!editable || edit || draft || rowDetails || batchLock.current || (!updates.length && !append.length && !previous)) return
    if (updates.length + append.length > 100 || [...updates.map(row => row.values), ...append].reduce((count, values) => count + Object.keys(values).length, 0) > 500) {
      setBatchError(t('dataset.clipboardLimit'))
      return
    }
    batchLock.current = true
    setBatchBusy(true)
    setBatchError('')
    try {
      const result = await api<DatasetBatchResult>(`${url}/batch`, {
        method: 'PATCH', json: {
          schema_revision: previous ? undo?.revision : dataset.revision, rows: updates, append,
          ...(previous ? { remove: undo?.remove } : {}),
        },
      })
      if (result.rows.length || result.added?.length || previous) {
        setUndo(previous ? null : {
          revision: result.schema_revision,
          rows: result.rows.map(row => ({ id: row.id, revision: row.revision, values: row.previous })),
          remove: Object.fromEntries((result.added ?? []).map(row => [row.id, row.revision])),
        })
      }
      setNotice(t(previous ? 'dataset.clipboardUndone' : 'dataset.clipboardSaved'))
      reload()
    } catch (error) {
      if (error instanceof ApiError) {
        const issues = error.details?.issues as { id?: string; index?: number; field: string; error: ApiErrorBody }[] | undefined
        const issue = issues?.[0]
        const number = issue?.index ? rows.length + issue.index - 1 : issue ? rows.findIndex(row => row.id === issue.id) : -1
        setBatchError(issue && number >= 0 ? t('dataset.clipboardCellError', {
          row: offset + number + 1, column: heading(issue.field)?.label ?? issue.field, error: errorText(issue.error),
        }) : error.message)
      } else setBatchError(t('errors.INTERNAL_ERROR'))
    } finally {
      batchLock.current = false
      setBatchBusy(false)
    }
  }

  function copyRanges(event?: ClipboardEvent) {
    const selected = table.getSelectedCellRangesData()
    if (!selected.length) return
    const text = datasetClipboardText(selected)
    if (event) {
      event.preventDefault()
      event.clipboardData.setData('text/plain', text)
    } else void navigator.clipboard.writeText(text).catch(() => setBatchError(t('dataset.clipboardPermission')))
  }

  function pasteText(text: string) {
    if (!editable || editing || !text) return
    const anchor = table.getFocusedCell()
    if (!anchor) return
    const rowAt = rows.findIndex(row => row.id === anchor.row.id)
    const columnAt = orderedVisible.findIndex(column => column.id === anchor.column.id)
    if (rowAt < 0 || columnAt < 0) return
    try {
      const matrix = datasetClipboardRows(text)
      const updates: DatasetBatchRow[] = []
      const append: Record<string, CellValue>[] = []
      matrix.forEach((cells, index) => {
        const row = rows[rowAt + index]?.original
        const values = Object.fromEntries(cells.map((value, position) => {
          const column = heading(orderedVisible[columnAt + position]?.id ?? '')
          if (!column || datasetReadOnly(column)) throw new Error('dataset.clipboardReadOnly')
          return [column.key, datasetClipboardValue(value, column)]
        }))
        if (row) updates.push({ id: row.id, revision: row.revision, values })
        else append.push(values)
      })
      if (append.length) {
        if (displayPage?.next_offset != null) throw new Error('dataset.clipboardNeedsRows')
        if (search || filters.children.length || groupColumn || sorting.length) throw new Error('dataset.clipboardClearQuery')
        setPastePreview({ updates, append })
      } else void applyBatch(updates)
    } catch (error) {
      setBatchError(t(error instanceof Error ? error.message : 'dataset.clipboardParse'))
    }
  }

  function fill(direction: 'down' | 'right') {
    if (!editable || editing) return
    const bounds = table.getCellSelectionBounds()
    const updates = new Map<string, DatasetBatchRow>()
    for (const range of bounds) {
      for (let i = range.minRowIndex; i <= range.maxRowIndex; i++) {
        const row = rows[i]
        if (!row) continue
        const update = updates.get(row.id) ?? { id: row.id, revision: row.original.revision, values: {} }
        for (let j = range.minColumnIndex; j <= range.maxColumnIndex; j++) {
          const column = orderedVisible[j]
          const field = column && heading(column.id)
          if (!field || datasetReadOnly(field) || (direction === 'down' ? i === range.minRowIndex : j === range.minColumnIndex)) continue
          const source = direction === 'down' ? rows[range.minRowIndex] : row
          const sourceField = direction === 'right' ? orderedVisible[range.minColumnIndex] : column
          if (source && sourceField) update.values[field.key] = source.original.values[sourceField.id] ?? null
        }
        if (Object.keys(update.values).length) updates.set(row.id, update)
      }
    }
    void applyBatch([...updates.values()])
  }

  function handleCellKey(event: KeyboardEvent<HTMLButtonElement>, row: DatasetRow, column: DatasetColumn) {
    const primary = event.ctrlKey || event.metaKey
    if (!primary && !event.shiftKey && !event.altKey && (event.key === 'PageDown' || event.key === 'PageUp')) {
      const preview = previewContent.current
      if (preview && preview.scrollHeight > preview.clientHeight) {
        event.preventDefault()
        preview.scrollBy({ top: event.key === 'PageDown' ? preview.clientHeight : -preview.clientHeight })
        return
      }
    }
    if (primary && !event.shiftKey && ['d', 'r', 'z'].includes(event.key.toLowerCase())) {
      if (!editable) return
      event.preventDefault()
      const key = event.key.toLowerCase()
      if (key === 'z') { if (undo) void applyBatch(undo.rows, true) }
      else fill(key === 'd' ? 'down' : 'right')
      return
    }
    if (event.key === 'Enter' || event.key === 'F2') {
      if (editable) { event.preventDefault(); beginEdit(row, column) }
      return
    }
    const movement = MOVEMENT[event.key]
    if (!movement || edit || draft) return
    event.preventDefault()
    const keyDirection = DIRECTIONS[event.key]
    if (event.shiftKey) {
      if (!table.getFocusedCell()) table.selectCellRange({ anchorRowId: row.id, anchorColumnId: column.key, focusRowId: row.id, focusColumnId: column.key })
      table.extendCellSelection(keyDirection)
      return
    }
    const rowIndex = rows.findIndex(item => item.id === row.id)
    const columnIndex = orderedVisible.findIndex(item => item.id === column.key)
    const nextRow = rows[rowIndex + movement[0]]
    const nextColumn = orderedVisible[columnIndex + movement[1]]
    if (!nextRow || !nextColumn) return
    table.selectCellRange({ anchorRowId: nextRow.id, anchorColumnId: nextColumn.id, focusRowId: nextRow.id, focusColumnId: nextColumn.id })
    const target = cellId(nextRow.id, nextColumn.id)
    if (document.getElementById(target)) document.getElementById(target)?.focus()
    else if (useVirtualRows) {
      virtualizer.scrollToIndex(rowIndex + movement[0])
      requestAnimationFrame(() => requestAnimationFrame(() => document.getElementById(target)?.focus()))
    }
  }

  function cancelDraft() {
    setDraft(null)
    setDraftError('')
    window.requestAnimationFrame(() => addButton.current?.focus())
  }

  async function saveDraft() {
    if (!draft || draftBusy) return
    const invalid = Array.from(draftRow.current?.querySelectorAll('input') ?? []).find(input => !input.checkValidity())
    if (invalid) {
      invalid.focus()
      return
    }
    setDraftBusy(true)
    setDraftError('')
    try {
      const values = Object.fromEntries(dataset.columns.filter(column => !datasetReadOnly(column)).map(column => [
        column.key, Object.hasOwn(draft, column.key) ? draft[column.key] : column.default,
      ]))
      await api<DatasetRowResult>(url, { method: 'POST', json: { values, schema_revision: dataset.revision } })
      cancelDraft()
      setNotice(t('dataset.rowAdded'))
      reload()
    } catch (error) {
      setDraftError(error instanceof Error ? error.message : t('errors.INTERNAL_ERROR'))
      if (error instanceof ApiError && error.code === 'DATASET_SCHEMA_CONFLICT') reloadDataset()
      const first = dataset.columns[0]
      if (first) window.requestAnimationFrame(() => document.getElementById(`${editId}-new-${first.key}`)?.focus())
    } finally {
      setDraftBusy(false)
    }
  }

  async function updateRow(source: DatasetRow, values: Record<string, CellValue>, schemaRevision: number) {
    const { row } = await api<DatasetRowResult>(`${url}/${source.id}`, {
      method: 'PATCH', json: { revision: source.revision, schema_revision: schemaRevision, values },
    })
    setPage(current => current && { ...current, items: current.items.map(item => item.id === row.id ? row : item) })
    reload()
  }

  async function save(value: CellValue, restoreFocus = true) {
    if (!edit || busy || stale || saving.current) return
    if (Object.is(value, edit.row.values[edit.column.key] ?? null)) {
      closeEditor(restoreFocus)
      return
    }
    saving.current = true
    setBusy(true)
    setSaveError(null)
    try {
      await updateRow(edit.row, { [edit.column.key]: value }, dataset.revision)
      closeEditor(restoreFocus)
      setNotice(t('dataset.cellSaved'))
    } catch (error) {
      setActive({ row: edit.row.id, column: edit.column.key })
      setEdit({ ...edit, value })
      setSaveError({
        message: error instanceof Error ? error.message : t('errors.INTERNAL_ERROR'),
        field: error instanceof ApiError && ['DATASET_UNIQUE_CONFLICT', 'DATASET_VALUE_INVALID'].includes(error.code ?? ''),
      })
      setStale(error instanceof ApiError && ['DATASET_ROW_CONFLICT', 'DATASET_SCHEMA_CONFLICT'].includes(error.code ?? ''))
      restoreEditorFocus.current = true
    } finally {
      saving.current = false
      setBusy(false)
    }
  }

  async function writeRelation(source: Edit, target: string | null) {
    const path = `${url}/${source.row.id}/relations/${encodeURIComponent(source.column.key)}`
    const revisions = { revision: source.row.revision, schema_revision: source.schemaRevision }
    const result = target === null
      ? await api<{ id: string; revision: number }>(`${path}?revision=${revisions.revision}&schema_revision=${revisions.schema_revision}`, { method: 'DELETE' })
      : await api<{ id: string; revision: number }>(path, { method: 'PUT', json: { ...revisions, target_row_id: target } })
    const update = (current: DatasetRowPage | null) => current && { ...current, items: current.items.map(row =>
      row.id === result.id ? { ...row, revision: result.revision, values: { ...row.values, [source.column.key]: target } } : row) }
    setPage(update)
    setAutoPage(update)
    setNotice(t('dataset.cellSaved'))
    reload()
  }

  async function pickRelation(target: string) {
    if (!edit || busy || stale || saving.current || !editable || !dataset.relation_config_enabled) return
    if (edit.value === target) { closeEditor(); return }
    saving.current = true
    setBusy(true)
    setSaveError(null)
    try {
      await writeRelation(edit, target)
      closeEditor()
    } catch (error) {
      setSaveError({ message: error instanceof Error ? error.message : t('errors.INTERNAL_ERROR') })
      setStale(error instanceof ApiError && ['DATASET_ROW_CONFLICT', 'DATASET_SCHEMA_CONFLICT'].includes(error.code ?? ''))
    } finally {
      saving.current = false
      setBusy(false)
    }
  }

  function askUnlink() {
    if (!edit || !editable || busy || typeof edit.value !== 'string') return
    const source = edit
    const label = relationLabels[edit.column.key]?.[edit.value]
    unlinkFocus.current = cellId(edit.row.id, edit.column.key)
    closeEditor(false)
    confirm.ask({ name: label ?? source.column.label, title: t('dataset.relation.unlink'),
      description: t('dataset.relation.unlinkHelp'), confirmLabel: t('dataset.relation.unlink'),
      onConfirm: () => writeRelation(source, null),
    })
  }

  async function refreshEdit() {
    if (!edit || busy) return
    setBusy(true)
    try {
      const row = await api<DatasetRow>(`${url}/${edit.row.id}`)
      const schema = await api<Dataset>(datasetUrl(dataset.id))
      if (!schema.columns.some(column => column.key === edit.column.key)) {
        reloadDataset()
        setSaveError({ message: t('errors.DATASET_COLUMN_NOT_FOUND') })
        return
      }
      if (schema.revision !== dataset.revision) reloadDataset()
      setEdit({ ...edit, row })
      setStale(false)
      setSaveError({ message: t('dataset.editRefreshed', { value: format(row.values[edit.column.key] ?? null, edit.column.kind) }), notice: true })
      reload()
      restoreEditorFocus.current = true
    } catch (error) {
      setSaveError({ message: error instanceof Error ? error.message : t('errors.INTERNAL_ERROR') })
    } finally {
      setBusy(false)
    }
  }

  const format = (value: CellValue, kind: DatasetKind) => displayValue(value, t('dataset.valueTrue'), t('dataset.valueFalse'), kind)
  const heading = (key: string) => dataset.columns.find(column => column.key === key)

  function askDelete(row: DatasetRow) {
    const named = deleteRowName(dataset, row)
    confirm.ask({ name: named?.value ?? row.id, requireTyping: false, title: t('dataset.deleteRow'),
      description: named ? t('dataset.deleteRowNamed', { field: named.label, value: named.value }) : t('dataset.deleteRowById', { id: row.id }),
      onConfirm: async () => {
        await api(`${url}/${row.id}?revision=${row.revision}`, { method: 'DELETE' })
        setSelection(current => { const next = { ...current }; delete next[row.id]; return next })
        if (page?.items.length === 1 && offset) changePage(-1)
        reload()
      },
    })
  }

  function resetPaging() {
    clearAutoPages()
    setOffsets([0])
    setPagination(current => ({ ...current, pageIndex: 0 }))
  }

  function changePage(direction: -1 | 1) {
    const nextOffset = displayPage?.next_offset
    if (direction === 1 && nextOffset == null) return
    clearAutoPages()
    setSelection({})
    if (direction === 1) setOffsets([...offsets.slice(0, pagination.pageIndex + 1), nextOffset!])
    table.setPageIndex(pagination.pageIndex + direction)
    setPage(null)
  }

  function moveColumn(from: string, to: string) {
    if (from === to) return
    const next = layout.orderedFields.map(column => column.key)
    const index = next.indexOf(to)
    next.splice(next.indexOf(from), 1)
    next.splice(index, 0, from)
    setColumnOrder(next)
  }

  const span = 1 + layout.fields.length + Number(layout.showRowId) + 1

  function renderRow(row: (typeof rows)[number], index: number) {
    // ui-class-ok: The selected row height controls spacing on data cells.
    return <TableRow key={row.id} data-testid="dataset-row" data-state={row.getIsSelected() ? 'selected' : undefined}
      className="group/row [&>td]:py-0" data-index={index} ref={useVirtualRows ? virtualizer.measureElement : undefined}
      style={{ height: HEIGHTS[rowHeight] }}>
      <TableCell className={cn(ROW_INDEX, 'p-0 group-hover/row:bg-muted group-data-[state=selected]/row:bg-muted')}><label className="grid absolute inset-0 cursor-pointer place-items-center">
        <Checkbox aria-label={t('dataset.selectRow', { row: offset + index + 1 })} checked={row.getIsSelected()}
          className="col-start-1 row-start-1 opacity-0 group-hover/row:opacity-100 group-has-[:focus-visible]/row:opacity-100 data-[state=checked]:opacity-100"
          onCheckedChange={checked => row.toggleSelected(checked === true)} />
        <span aria-hidden="true" data-testid="dataset-row-number" className={cn(
          'pointer-events-none col-start-1 row-start-1 text-xs tabular-nums text-muted-foreground group-hover/row:opacity-0 group-has-[:focus-visible]/row:opacity-0',
          row.getIsSelected() && 'opacity-0',
        )}>{offset + index + 1}</span>
      </label></TableCell>
      {layout.showRowId && <TableCell className={cn(DIVIDER, 'truncate font-mono text-xs text-muted-foreground')} title={row.id}>{row.id}</TableCell>}
      {row.getVisibleCells().map(cell => {
        const column = heading(cell.column.id)!
        const value = (cell.getValue() as CellValue | undefined) ?? null
        const isEditing = edit?.row.id === row.id && edit.column.key === column.key
        const isSelected = selectedCell?.row === row.id && selectedCell.column === column.key
        const rangeSelected = !editing && cell.getIsSelected()
        const isFocused = !editing && isSelected
        const isTabStop = !editing && tabStop.row === row.id && tabStop.column === column.key
        const buttonId = cellId(row.id, column.key)
        const relation = column.kind === 'relation'
        const cellEditable = canEditCell(column, value)
        const usesPicker = column.kind === 'boolean' || column.kind === 'select'
        const multiSelect = column.kind === 'multi_select'
        const linkedLabel = relation && typeof value === 'string' ? relationLabels[column.key]?.[value] : undefined
        const display = relation && value !== null
          ? linkedLabel ?? t(linkedLabel === null ? 'dataset.relation.unavailable' : 'common.loading')
          : displayColumnValue(value, column, t('dataset.valueTrue'), t('dataset.valueFalse'))
        const reason = row.original.formula_errors?.[column.key]
        const diagnostic = reason ? datasetFormulaError(reason) : undefined
        const showPreview = isFocused && showCellPreview && value !== null && !!display
        return <TableCell key={cell.id} ref={relation && isEditing ? relationAnchor : isFocused ? previewAnchor : undefined} data-dataset-cell="" style={pinnedStyle(cell.column)} className={cn(DIVIDER, 'relative p-0 whitespace-normal',
          (isEditing && isSelected) || isFocused ? 'bg-muted outline-1 -outline-offset-1 outline-foreground has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2' : !rangeSelected && 'hover:bg-muted',
          rangeSelected && CELL_RANGE_BACKGROUND,
          cell.column.getIsPinned() && '!sticky z-10',
          cell.column.getIsPinned() && !isEditing && !isFocused && !rangeSelected && 'bg-background',
        )}>
          {isEditing && !relation ? <form ref={inlineEditor} onFocus={event => {
            if (!isSelected && event.currentTarget.contains(event.target)) setActive({ row: row.id, column: column.key })
          }} onSubmit={event => {
            event.preventDefault()
            void save(edit.value)
          }} onKeyDown={event => {
            if (inEditorPopup(event.target)) return
            if (event.key === 'Tab' && (!event.currentTarget.checkValidity() || (saveError && !saveError.notice))) {
              const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('input, textarea, button'))
                .filter(control => control.tabIndex >= 0 && !control.matches(':disabled') && control.getClientRects().length)
              const first = controls[0]
              const last = controls.at(-1)
              if (event.target === (event.shiftKey ? first : last)) {
                event.preventDefault()
                const next = event.shiftKey ? last : first
                next?.focus()
              }
            }
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && event.target instanceof HTMLTextAreaElement
              && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void save(edit.value)
            }
            if (event.key === 'Escape' && !busy && !event.nativeEvent.isComposing) { event.stopPropagation(); closeEditor() }
          }} onBlur={event => {
            const form = event.currentTarget
            if (form.contains(event.relatedTarget) || inEditorPopup(event.target) || inEditorPopup(event.relatedTarget)) return
            if (!form.checkValidity() || (saveError && !saveError.notice)) {
              requestAnimationFrame(() => {
                if (inlineEditor.current !== form || form.contains(document.activeElement)
                  || inEditorPopup(document.activeElement)) return
                document.getElementById(editId)?.focus({ preventScroll: true })
              })
            } else if (!usesPicker && !multiSelect && !saveError) {
              void save(edit.value, false)
            }
          }}>
            <DatasetValueField id={editId} label={column.label} column={column} value={edit.value} focus inline openPicker disabled={busy}
              error={saveError?.notice ? undefined : saveError?.message}
              onPickerClose={usesPicker || multiSelect ? reason => {
                // A single-value picker can start saving before the menu closes.
                if (saving.current) return
                if (reason === 'escape') closeEditor()
                else if (!saveError) void save(edit.value, reason !== 'outside')
              } : undefined}
              onCalendarPick={column.kind === 'date' && !stale ? value => { void save(value) } : undefined}
              onChange={value => {
                if (saveError?.field) setSaveError(null)
                if (usesPicker && !stale) void save(value)
                else setEdit({ ...edit, value })
              }} />
            {saveError && !saveError.field && <div className="space-y-1 px-2 pb-2">
              {saveError.notice && <div role="status" className="text-xs wrap-anywhere text-muted-foreground">{saveError.message}</div>}
              {stale ? <Button type="button" variant="outline" size="sm" onClick={refreshEdit} disabled={busy}>{t('dataset.refreshEdit')}</Button>
                : <Button type="submit" variant="outline" size="sm" disabled={busy}>{t('common.save')}</Button>}
            </div>}
          </form> :
            <Button id={buttonId} variant="ghost" tabIndex={isTabStop ? 0 : -1}
              className={cn(CELL_BUTTON, 'absolute inset-0 h-full touch-manipulation px-2 font-normal focus-visible:border-transparent focus-visible:ring-0',
                column.kind === 'url' && value && 'pr-9', relation && cellEditable && isFocused && 'pe-9')}
              aria-label={t(cellEditable ? 'dataset.editCell' : 'dataset.readCell', { field: column.label, value: diagnostic ?? display })}
              title={diagnostic}
              aria-pressed={isFocused || rangeSelected}
              onMouseDown={event => {
                if (!editing && event.button === 0) {
                  setSelectingCells(true)
                  cell.getSelectionStartHandler()(event)
                }
              }}
              onMouseEnter={event => { if (!editing) cell.getSelectionExtendHandler()(event) }}
              onFocus={() => { if (!draft && (!saveError || saveError.notice)) setActive({ row: row.id, column: column.key }) }}
              onBlur={event => {
                if (!inDatasetCell(event.relatedTarget) && !inCellPreview(event.relatedTarget) && !inEditorPopup(event.relatedTarget)) setActive(null)
              }}
              onClick={() => { if (!draft) setActive({ row: row.id, column: column.key }) }}
              onDoubleClick={() => beginEdit(row.original, column)}
              onKeyDown={event => handleCellKey(event, row.original, column)}>
              {diagnostic && <CircleAlert aria-hidden="true" className="text-destructive" />}
              <span data-dataset-cell-label="" className={cn('min-w-0 truncate', diagnostic && 'text-destructive', column.kind === 'select' && value !== null && 'rounded bg-muted px-1.5')}>{diagnostic || display || '—'}</span>
              {isFocused && cellEditable && (usesPicker || multiSelect) && <ChevronDown aria-hidden="true" className="ms-auto text-muted-foreground" />}
            </Button>
          }
          {relation && isFocused && cellEditable && <Button type="button" variant="ghost" size="icon-sm" tabIndex={-1}
            className="absolute inset-y-0 end-0 my-auto" aria-haspopup="dialog" aria-label={t('dataset.relation.chooseRow')}
            onClick={() => beginEdit(row.original, column)}><ChevronDown /></Button>}
          {relation && isEditing && <Popover open onOpenChange={open => { if (!open && !saving.current) closeEditor(false) }}>
            <PopoverAnchor virtualRef={relationAnchor} />
            <PopoverContent data-dataset-editor-popup="" align="start" aria-label={t('dataset.relation.chooseRow')}
              className="max-h-(--radix-popover-content-available-height) max-w-[calc(100vw-1.5rem)] overflow-hidden"
              onCloseAutoFocus={event => event.preventDefault()}
              onEscapeKeyDown={event => {
                event.preventDefault()
                if (!saving.current) closeEditor()
              }}
              onInteractOutside={event => { if (saving.current) event.preventDefault() }}>
              {saveError && <Alert variant="destructive"><AlertDescription>{saveError.message}</AlertDescription></Alert>}
              {stale ? <Button type="button" variant="outline" onClick={() => {
                closeEditor()
                reloadDataset()
                reload()
              }}>{t('dataset.refreshEdit')}</Button>
                : dataset.relation_config_enabled ? <DatasetRelationPicker dataset={{ id: dataset.id, revision: edit.schemaRevision }}
                  field={column.key} value={typeof value === 'string' ? value : null} busy={busy} onPick={choice => { void pickRelation(choice.id) }}>
                  {value !== null && <Button type="button" variant="ghost" className="text-destructive" size="sm" disabled={busy}
                    onClick={askUnlink}>{t('dataset.relation.unlink')}</Button>}
                </DatasetRelationPicker> : <Button type="button" variant="ghost" className="text-destructive" size="sm"
                  onClick={askUnlink}>{t('dataset.relation.unlink')}</Button>}
            </PopoverContent>
          </Popover>}
          {showPreview && <DatasetCellPreview anchor={previewAnchor} content={previewContent} value={display}
            className={rangeSelected ? CELL_RANGE_BACKGROUND : 'bg-muted'} onClose={() => setActive(null)} />}
          {!isEditing && column.kind === 'url' && typeof value === 'string' && /^https?:\/\//i.test(value) &&
            <Button asChild variant="ghost" size="icon-sm" className="absolute inset-y-0 right-0 my-auto">
              <a href={value} target="_blank" rel="noopener noreferrer" aria-label={t('dataset.openUrl', { column: column.label })}><ExternalLink /></a>
            </Button>}
        </TableCell>
      })}
      <TableCell className={cn(ROW_ACTIONS, 'group-hover/row:bg-muted group-data-[state=selected]/row:bg-muted')}>
        <DatasetActionsMenu label={t('dataset.rowActions', { row: offset + index + 1 })} triggerId={rowActionId(row.id)}
          disabled={!!edit || !!draft}
          view={{ label: t(editable ? 'dataset.viewEditRow' : 'dataset.viewRow'), onSelect: () => setRowDetails(row.original) }}
          remove={{ label: t('dataset.deleteRow'), onSelect: () => askDelete(row.original), disabled: !editable }} />
      </TableCell>
    </TableRow>
  }

  function renderGroupHeader(group: DatasetRowGroup, columnKind: DatasetKind) {
    const key = groupKey(group.group)
    const open = selectedGroup === key
    return <TableRow className="bg-muted/50">
      <TableCell colSpan={span}>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" aria-expanded={open} disabled={editing} onClick={() => {
            table.setExpanded(open ? {} : { [key]: true })
            resetPaging()
            setSelection({})
            setPage(null)
          }}>
            {open ? <ChevronDown /> : <ChevronRight />}
            <span className="inline-flex items-baseline gap-1 leading-normal">
              <span>{group.group === null ? t('dataset.groupEmpty') : format(group.group, columnKind)}</span>
              <span className="tabular-nums text-muted-foreground">{t('dataset.groupRows', { count: group.total })}</span>
            </span>
          </Button>
          {showSummaries && layout.fields.map(column => {
            const operation = summaryColumns[column.key]
            const value = group.values[column.key]
            return operation && value != null && <span key={column.key} className="text-xs text-muted-foreground">
              {t('dataset.groupSummary', { column: column.label, metric: t(`dataset.summaryFunctions.${operation}`), value: displayColumnValue(value, column, t('dataset.valueTrue'), t('dataset.valueFalse')) })}
            </span>
          })}
        </div>
      </TableCell>
    </TableRow>
  }

  return <div>
    <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="toolbar" size="icon" aria-label={t('dataset.clipboardMenu')} data-dataset-clipboard="" disabled={editing}><Clipboard /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" data-dataset-clipboard="">
            <DropdownMenuItem disabled={!table.getSelectedCellCount()} onSelect={() => copyRanges()}>{t('dataset.clipboardCopy')}</DropdownMenuItem>
            <DropdownMenuItem disabled={!editable || !table.getFocusedCell()} onSelect={() => {
              void navigator.clipboard.readText().then(pasteText).catch(() => setBatchError(t('dataset.clipboardPermission')))
            }}>{t('dataset.clipboardPaste')}</DropdownMenuItem>
            <DropdownMenuItem disabled={!editable || table.getSelectedCellCount() < 2} onSelect={() => fill('down')}>{t('dataset.clipboardFillDown')}</DropdownMenuItem>
            <DropdownMenuItem disabled={!editable || table.getSelectedCellCount() < 2} onSelect={() => fill('right')}>{t('dataset.clipboardFillRight')}</DropdownMenuItem>
            <DropdownMenuItem disabled={!editable || !undo} onSelect={() => { if (undo) void applyBatch(undo.rows, true) }}>{t('dataset.clipboardUndo')}</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <span className="sr-only" role="status">{t('dataset.clipboardSelection', { count: table.getSelectedCellCount() })}</span>
        <ShortcutCheatsheet open={shortcutsOpen} onOpenChange={setShortcutsOpen}
          list={editable ? DATASET_EDIT_SHORTCUTS : DATASET_VIEW_SHORTCUTS} intro={t('dataset.shortcutIntro')}
          trigger={<Button variant="toolbar" size="icon" disabled={editing} aria-label={t('shortcuts.title')}><Keyboard /></Button>} />
        <Popover>
          <PopoverTrigger asChild><Button variant="toolbar" size="icon" data-active={rowHeight !== 'medium' || !!pinning.start?.length} disabled={editing} aria-label={t('dataset.gridLayout')}><Settings2 /></Button></PopoverTrigger>
          <PopoverContent align="start" className="grid gap-2">
            <div className="grid gap-1.5">
              <Label htmlFor={`${editId}-row-height`}>{t('dataset.rowHeight')}</Label>
              <Select value={rowHeight} disabled={editing} onValueChange={value => {
                setRowHeight(value as GridRowHeight)
                virtualizer.measure()
              }}>
                <SelectTrigger id={`${editId}-row-height`} className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{(Object.keys(HEIGHTS) as GridRowHeight[]).map(size => {
                  const Icon = ROW_HEIGHT_ICONS[size]
                  return <SelectItem value={size} key={size}><Icon aria-hidden="true" />{t(`dataset.rowHeights.${size}`)}</SelectItem>
                })}</SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor={`${editId}-freeze-columns`}>{t('dataset.freezeColumns')}</Label>
              <Select value={String(pinning.start?.length ?? 0)} disabled={editing} onValueChange={value => {
                table.setColumnPinning({ start: orderedVisible.slice(0, Number(value)).map(column => column.id), end: [] })
              }}>
                <SelectTrigger id={`${editId}-freeze-columns`} className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{[0, 1, 2, 3].map(count =>
                  <SelectItem value={String(count)} key={count} disabled={count > orderedVisible.length}>
                    {count ? <Pin aria-hidden="true" /> : <PinOff aria-hidden="true" />}{t('dataset.frozenCount', { count })}
                  </SelectItem>)}</SelectContent>
              </Select>
            </div>
          </PopoverContent>
        </Popover>
        <Select value={groupColumn?.key ?? '$none'} disabled={editing} onValueChange={field => {
          table.setGrouping(field === '$none' ? [] : [field])
          table.setExpanded({})
          setGroupOffset(0)
          setSelection({})
          resetPaging()
          setPage(null)
        }}>
          <SelectTrigger variant="toolbar" data-active={!!groupColumn} aria-label={t('dataset.groupBy')}><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="$none"><Ungroup aria-hidden="true" />{t('dataset.noGrouping')}</SelectItem>
            {dataset.columns.filter(column => datasetGroupable(column.kind)).map(column =>
              <SelectItem value={column.key} key={column.key}><DatasetFieldIcon kind={column.formula ? 'formula' : column.kind} /><span className="truncate">{column.label}</span></SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="toolbar" aria-pressed={showSummaries} disabled={editing}
          onClick={() => setShowSummaries(value => !value)}><Sigma />{t('dataset.summary')}</Button>
        <DatasetQueryControls dataset={dataset} disabled={editing} filters={filters} sorting={sorting}
          onFilters={applyFilters} onSorting={changeSorting} />
        <DatasetColumnControls columns={layout.orderedFields} visibleKeys={new Set(layout.fields.map(column => column.key))}
          disabled={editing} onMove={moveColumn} onVisibility={(key, visible) => table.getColumn(key)?.toggleVisibility(visible)} />
      </div>
      <div className="contents sm:ml-auto sm:flex sm:items-center sm:gap-2">
        <InputGroup className="order-last sm:order-none sm:w-44">
          <InputGroupAddon><Search aria-hidden="true" /></InputGroupAddon>
          <InputGroupInput type="search" aria-label={t('dataset.searchRows')} placeholder={t('dataset.searchRows')}
            value={searchText} maxLength={120} disabled={editing || !dataset.columns.some(column => datasetTextKind(column.kind))}
            onChange={event => setSearchText(event.target.value)} />
        </InputGroup>
        <Button ref={addButton} className="ml-auto sm:ml-0" disabled={editing || !editable} aria-describedby={editable ? undefined : viewOnlyId}
          onClick={() => {
            setActive(null)
            setDraft(Object.fromEntries(dataset.columns.map(column => [column.key, column.default])))
            setNotice('')
          }}><Plus />{t('dataset.addRow')}</Button>
      </div>
    </div>
    {loadError && <Alert variant="destructive"><AlertDescription>{loadError}<Button variant="outline" onClick={reload}>{t('common.retry')}</Button></AlertDescription></Alert>}
    {batchError && <Alert variant="destructive"><AlertDescription>{batchError}</AlertDescription></Alert>}
    <div ref={gridViewport} onCopy={event => { if (!editing) copyRanges(event) }} onPaste={event => {
      if (editable && !editing && table.getFocusedCell()) {
        event.preventDefault()
        pasteText(event.clipboardData.getData('text/plain'))
      }
    }} onScrollCapture={loadMoreOnScroll} className="border-t [&>[data-slot=table-container]]:max-h-[max(12rem,var(--dataset-scroll-height,100dvh))] [&>[data-slot=table-container]]:overflow-auto">
      <Table aria-label={t('dataset.gridView')} aria-busy={groupColumn ? !groups && !groupError : !page && !loadError}
        className="table-fixed border-separate border-spacing-0 [&_tr:not([aria-hidden=true])>:is(td,th)]:border-b [&_tbody>tr:last-child>:is(td,th)]:border-b-0" style={{ width: layout.width }}>
        <colgroup>
          <col style={{ width: ROW_NUMBER_WIDTH }} />
          {layout.showRowId && <col style={{ width: ROW_ID_WIDTH }} />}
          {orderedVisible.map(column => <col key={column.id} style={{ width: column.getSize() }} />)}
          <col />
        </colgroup>
        <TableHeader className="bg-muted/50"><TableRow className="hover:bg-transparent">
          <TableHead scope="col" className={cn(ROW_INDEX, 'bg-muted p-0')}><div className="grid place-items-center"><Checkbox aria-label={t('dataset.selectVisibleRows')}
            disabled={!rows.length} checked={table.getIsAllRowsSelected() || (table.getIsSomeRowsSelected() ? 'indeterminate' : false)}
            onCheckedChange={checked => table.toggleAllRowsSelected(checked === true)} /></div></TableHead>
          {layout.showRowId && <TableHead scope="col" className={DIVIDER}>{t('dataset.rowId')}</TableHead>}
          {[...table.getStartFlatHeaders(), ...table.getCenterFlatHeaders(), ...table.getEndFlatHeaders()].map(header => {
            const direction = header.column.getIsSorted()
            const priority = header.column.getSortIndex()
            const column = heading(header.column.id)!
            const Icon = direction === 'asc' ? ArrowUp : direction === 'desc' ? ArrowDown : ArrowUpDown
            return <TableHead key={header.id} scope="col" style={pinnedStyle(header.column)}
              className={cn(DIVIDER, 'relative p-0 hover:bg-muted', header.column.getIsPinned() && '!sticky z-10 bg-muted')}
              aria-sort={priority === 0 && direction ? (direction === 'asc' ? 'ascending' : 'descending') : undefined}>
              <Button variant="ghost" size="sm" className={cn(CELL_BUTTON, 'absolute inset-y-0 left-0 right-2 h-full gap-1 px-2')}
                onClick={header.column.getToggleSortingHandler()} disabled={!!edit || !!draft}>
                <DatasetFieldIcon kind={column.formula ? 'formula' : column.kind} />
                <span className="relative top-px min-w-0 truncate leading-none" title={column.label}>{column.label}</span>
                {column.unique && <DatasetUniqueBadge />}
                <Icon aria-hidden="true" className="ml-auto" />
                {priority >= 0 && sorting.length > 1 && <span aria-label={t('dataset.sortPriority', { number: priority + 1 })}
                  className="text-xs tabular-nums text-muted-foreground">{priority + 1}</span>}
              </Button>
              {!editing && <div role="separator" aria-orientation="vertical" tabIndex={0} aria-label={t('dataset.resizeColumn', { name: column.label })}
                aria-valuemin={MIN_COLUMN_WIDTH} aria-valuemax={MAX_COLUMN_WIDTH} aria-valuenow={Math.round(header.getSize())}
                className="absolute inset-y-0 right-0 z-10 w-2 cursor-col-resize touch-none select-none after:absolute after:inset-y-0 after:right-0 after:w-px hover:after:bg-foreground focus-visible:after:bg-foreground"
                onMouseDown={header.getResizeHandler()} onTouchStart={header.getResizeHandler()}
                onDoubleClick={() => header.column.resetSize()} onKeyDown={event => {
                  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
                  event.preventDefault()
                  const width = Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, header.getSize() + (event.key === 'ArrowRight' ? 16 : -16)))
                  table.setColumnSizing(current => ({ ...current, [column.key]: width }))
                }}>
                {header.column.getIsResizing() && <span className="pointer-events-none absolute inset-y-0 right-0 w-px bg-foreground"
                  style={{ transform: `translateX(${table.state.columnResizing.deltaOffset ?? 0}px)` }} />}
              </div>}
            </TableHead>
          })}
          <TableHead scope="col" className={cn(ROW_ACTIONS, 'bg-muted')}><span className="sr-only">{t('dataset.actions')}</span></TableHead>
        </TableRow>
          {showSummaries && <TableRow className="bg-muted/50 hover:bg-muted/50">
            <TableCell aria-label={t('dataset.summary')} className={cn(ROW_INDEX, 'bg-muted')} />
            {layout.showRowId && <TableCell className={DIVIDER} />}
            {orderedVisible.map(visible => {
              const column = layout.fields.find(field => field.key === visible.id)
              return <TableCell key={visible.id} style={pinnedStyle(visible)}
                className={cn(DIVIDER, visible.getIsPinned() === 'start' && '!sticky z-10 bg-muted')}>
                {column && <DatasetColumnSummary column={column}
                  operation={summaryColumns[column.key]} value={currentSummary?.values[column.key]} disabled={editing}
                  loading={!currentSummary} failed={!!currentSummaryError}
                  onChange={operation => setSummaryOperations(current => ({ ...current, [column.key]: operation }))} />}
              </TableCell>
            })}
            <TableCell className={cn(ROW_ACTIONS, 'bg-muted')} />
          </TableRow>}
          {showSummaries && currentSummaryError && <TableRow><TableCell colSpan={span}>
            <Alert variant="warning"><AlertDescription>{currentSummaryError}</AlertDescription></Alert>
          </TableCell></TableRow>}
        </TableHeader>
        <TableBody>
          {draft && <TableRow ref={draftRow} data-testid="dataset-row-draft" className="bg-muted/40" onKeyDown={event => {
            if (inDatasetCalendar(event.target)) return
            if (event.key === 'Escape' && !event.defaultPrevented && !draftBusy) cancelDraft()
            if (event.key === 'Enter' && event.target instanceof HTMLInputElement && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void saveDraft()
            }
          }}>
            <TableCell className={cn(ROW_INDEX, 'bg-muted p-0')}><div className="grid min-h-10 place-items-center">
              <Plus aria-hidden="true" className="size-4 text-muted-foreground" />
            </div></TableCell>
            {layout.showRowId && <TableCell className={DIVIDER}>—</TableCell>}
            {layout.fields.map((column, index) => <TableCell key={column.key} data-dataset-cell="" className={cn(DIVIDER, 'p-0 whitespace-normal focus-within:bg-muted focus-within:outline-1 focus-within:-outline-offset-1 focus-within:outline-foreground')}>
              <DatasetValueField id={`${editId}-new-${column.key}`} label={column.label} column={column} inline
                value={Object.hasOwn(draft, column.key) ? draft[column.key] : column.default} focus={index === 0} disabled={draftBusy} onChange={value => setDraft(current => current && ({ ...current, [column.key]: value }))} />
            </TableCell>)}
            <TableCell className={cn(ROW_ACTIONS, 'px-1')}>
              <div className="flex items-center">
                <Button variant="ghost" size="icon" aria-label={t('common.save')} disabled={draftBusy} onClick={() => void saveDraft()}><Check /></Button>
                <Button variant="ghost" size="icon" aria-label={t('common.cancel')} disabled={draftBusy} onClick={cancelDraft}><X /></Button>
              </div>
            </TableCell>
          </TableRow>}
          {draftError && <TableRow><TableCell colSpan={span}><Alert variant="destructive"><AlertDescription>{draftError}</AlertDescription></Alert></TableCell></TableRow>}
          {groupColumn && (!groups || !groups.groups.length) && <TableRow><TableCell colSpan={span} className="text-muted-foreground">
            {groupError ? <Alert variant="destructive"><AlertDescription>{groupError}
              <Button variant="outline" onClick={reload}>{t('common.retry')}</Button>
            </AlertDescription></Alert> : groups ? t('dataset.noRows') : t('common.loading')}
          </TableCell></TableRow>}
          {!groupColumn && !draft && !page?.items.length && <TableRow><TableCell colSpan={span} className="text-muted-foreground">
            {loadError ? t('dataset.rowsUnavailable') : page ? t('dataset.noRows') : t('common.loading')}
          </TableCell></TableRow>}
          {groupColumn ? groups?.groups.map(group => <Fragment key={groupKey(group.group)}>
            {renderGroupHeader(group, groupColumn.kind)}
            {selectedGroup === groupKey(group.group) && rows.map(renderRow)}
          </Fragment>) : useVirtualRows ? <>
            {virtualRows.map((item, index) => {
              const gap = item.start - (virtualRows[index - 1]?.end ?? headerHeight)
              return <Fragment key={item.key}>
                {gap > 0 && <TableRow aria-hidden="true"><TableCell colSpan={span} style={{ height: gap }} className="border-0 p-0" /></TableRow>}
                {renderRow(rows[item.index], item.index)}
              </Fragment>
            })}
            <TableRow aria-hidden="true"><TableCell colSpan={span}
              style={{ height: Math.max(0, virtualizer.getTotalSize() - ((virtualRows.at(-1)?.end ?? headerHeight) - headerHeight)) }} className="border-0 p-0" /></TableRow>
          </> : rows.map(renderRow)}
        </TableBody>
      </Table>
    </div>
    <div ref={gridFooter} data-testid="dataset-grid-footer" className="sticky bottom-0 z-30 flex flex-wrap items-center justify-between gap-2 border-t bg-background px-3 py-1 text-sm">
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground" aria-live="polite">
        {page && <span>{t(page.total_capped ? 'dataset.visibleRangeCapped' : 'dataset.visibleRange', {
          start: rows.length ? offset + 1 : 0, end: rows.length ? offset + rows.length : 0, total: page.total,
        })}</span>}
        {!!selectedCount && <span>{t('dataset.rowsSelected', { count: selectedCount })}</span>}
        {edit ? <span>{t('dataset.discardEditKeys')}</span>
          : editable && <span className="hidden lg:inline">{t('dataset.gridKeys')}</span>}
      </div>
      {groupColumn && <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={groupOffset === 0 || editing} onClick={() => {
          setGroupOffset(current => Math.max(0, current - GROUP_PAGE_SIZE)); table.setExpanded({}); setPage(null); setSelection({}); resetPaging()
        }}>{t('dataset.previousGroups')}</Button>
        <Button variant="outline" size="sm" disabled={groups?.next_offset == null || editing} onClick={() => {
          if (groups?.next_offset == null) return
          setGroupOffset(groups.next_offset); table.setExpanded({}); setPage(null); setSelection({}); resetPaging()
        }}>{t('dataset.nextGroups')}</Button>
      </div>}
      <div className="flex items-center gap-2">
        <span role="status" className="flex items-center gap-1 text-xs text-muted-foreground">
          {(live.delayed || snapshotError) && <><WifiOff aria-hidden="true" className="size-4 text-warning" />{t('dataset.liveDelayed')}</>}
          {!live.delayed && !snapshotError && notice && <><Check aria-hidden="true" className="size-3" />{notice}</>}
        </span>
        <Select value={String(pagination.pageSize)} disabled={editing} onValueChange={value => {
          clearAutoPages()
          setOffsets([0])
          setSelection({})
          setPage(null)
          table.setPagination({ pageIndex: 0, pageSize: Number(value) })
        }}>
          <SelectTrigger size="sm" aria-label={t('dataset.pageSize')}><SelectValue /></SelectTrigger>
          <SelectContent>{PAGE_SIZES.map(size => <SelectItem key={size} value={String(size)}>{size}</SelectItem>)}</SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">{t('dataset.page', { page: pagination.pageIndex + 1 })}</span>
        <Button variant="outline" size="icon-sm" aria-label={t('dataset.previousPage')} disabled={pagination.pageIndex === 0 || editing}
          onClick={() => changePage(-1)}><ChevronLeft /></Button>
        <Button variant="outline" size="icon-sm" aria-label={t('dataset.nextPage')} disabled={displayPage?.next_offset == null || editing}
          onClick={() => changePage(1)}><ChevronRight /></Button>
      </div>
    </div>
    {rowDetails && <DatasetRowDialog dataset={dataset} row={rowDetails} editable={editable} triggerId={rowActionId(rowDetails.id)}
      onClose={() => setRowDetails(null)} onReload={() => { reloadDataset(); reload() }}
      onSave={async (row, values, schemaRevision) => {
        await updateRow(row, values, schemaRevision)
        setRowDetails(null)
        setNotice(t('dataset.rowSaved'))
      }} />}
    {pastePreview && <Dialog open onOpenChange={open => { if (!open) setPastePreview(null) }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('dataset.clipboardPreview')}</DialogTitle>
          <DialogDescription>{t('dataset.clipboardAppend', { count: pastePreview.append.length })}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setPastePreview(null)}>{t('common.cancel')}</Button>
          <Button onClick={() => {
            void applyBatch(pastePreview.updates, false, pastePreview.append)
            setPastePreview(null)
          }}>{t('dataset.clipboardPaste')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>}
    {confirm.dialog}
  </div>
}
