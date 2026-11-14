import { Fragment, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type ClipboardEvent, type CSSProperties, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import {
  cellSelectionFeature, columnGroupingFeature, columnOrderingFeature, columnPinningFeature, columnResizingFeature, columnSizingFeature,
  columnVisibilityFeature, rowExpandingFeature, rowPaginationFeature, rowSelectionFeature, rowSortingFeature,
  tableFeatures, useTable, type CellSelectionDirection, type ColumnPinningState, type ColumnVisibilityState, type ExpandedState, type GroupingState,
  type ColumnOrderState, type ColumnSizingState, type PaginationState, type RowSelectionState, type SortingState, type Updater,
} from '@tanstack/react-table'
import { defaultRangeExtractor, useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, ArrowUpDown, Check, ChevronDown, ChevronLeft, ChevronRight, ExternalLink, Clipboard, Plus, Search, Settings2, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Checkbox } from '@/components/ui/checkbox'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api, ApiError } from '@/lib/api'
import { DATASET_QUERY_LIMIT, datasetGroupable, datasetSummaryFunctions, datasetReadOnly, datasetTextKind, datasetUrl, deleteRowName, displayColumnValue, displayValue, emptyDatasetFilters, keepDatasetFilterFields, type DatasetFilters, type DatasetGroupsPage, type DatasetRowGroup, type CellValue, type Dataset, type DatasetColumn, type DatasetColumnSummaries, type DatasetSummaryResult, type DatasetKind, type DatasetRow, type DatasetRowPage, type DatasetRowResult } from '@/lib/datasets'
import { errorText, type ApiErrorBody } from '@/lib/i18n'
import { datasetClipboardRows, datasetClipboardText, datasetClipboardValue, type DatasetBatchResult, type DatasetBatchRow } from '@/lib/dataset-clipboard'
import { cn } from '@/lib/utils'
import { DatasetColumnSummary } from './dataset-column-summary'
import { DatasetActionsMenu } from './dataset-actions-menu'
import { DatasetRowDialog } from './dataset-dialogs'
import { DatasetColumnControls, DatasetUniqueBadge } from './dataset-column-controls'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetValueField } from './dataset-fields'
import { DatasetQueryControls } from './dataset-query-controls'

const NO_ROWS: DatasetRow[] = []
const features = tableFeatures({
  cellSelectionFeature, columnGroupingFeature, columnOrderingFeature, columnPinningFeature, columnSizingFeature, columnResizingFeature,
  columnVisibilityFeature, rowExpandingFeature, rowPaginationFeature, rowSelectionFeature, rowSortingFeature,
})
type Edit = { row: DatasetRow; column: DatasetColumn; value: CellValue }
type Cell = { row: string; column: string }
const DIRECTIONS: Record<string, CellSelectionDirection> = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' }
const MOVEMENT: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }
const DIVIDER = 'border-r border-border'
const CELL_BUTTON = 'w-full justify-start rounded-none hover:bg-transparent dark:hover:bg-transparent'
const MIN_COLUMN_WIDTH = 100
const MAX_COLUMN_WIDTH = 4096
const ROW_NUMBER_WIDTH = 56
const ROW_ID_WIDTH = 112
const ROW_ACTIONS_WIDTH = 80
const HEIGHTS = { short: 32, medium: 40, tall: 56 }
type GridRowHeight = keyof typeof HEIGHTS
const DEFAULT_WIDTH: Record<DatasetKind, number> = { text: 200, number: 120, boolean: 104, date: 152, datetime: 216, email: 232, select: 160, long_text: 320, url: 250, created_time: 216, updated_time: 216, multi_select: 240, auto_number: 140 }
const PAGE_SIZES = [25, 50, 100]

function readLayout(key: string): { order?: ColumnOrderState; sizes?: ColumnSizingState; visibility?: ColumnVisibilityState; summaries?: DatasetColumnSummaries; showSummaries?: boolean; groupBy?: string; pinned?: string[]; rowHeight?: GridRowHeight } {
  try {
    return JSON.parse(localStorage.getItem(key) ?? '{}') ?? {}
  } catch {
    return {}
  }
}

const GROUP_PAGE_SIZE = 50
const groupKey = (value: CellValue) => JSON.stringify(value)

const ROW_ACTIONS = 'sticky right-0 z-20 border-l bg-background'

function inDatasetCell(target: EventTarget | null) {
  return target instanceof Element && !!target.closest('[data-dataset-cell]')
}

function inDatasetCalendar(target: EventTarget | null) {
  return target instanceof Element && !!target.closest('[data-dataset-calendar]')
}


export function DatasetGrid({ dataset, editable, reloadDataset, initialFilters, viewOnlyId }: {
  dataset: Dataset
  editable: boolean
  viewOnlyId?: string
  reloadDataset: () => void
  initialFilters?: DatasetFilters
}) {
  const { t } = useTranslation()
  const editId = useId()
  const addButton = useRef<HTMLButtonElement>(null)
  const gridViewport = useRef<HTMLDivElement>(null)
  const draftRow = useRef<HTMLTableRowElement>(null)
  const saving = useRef(false)
  const restoreEditorFocus = useRef(false)
  const confirm = useConfirmDelete()
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
  const [active, setActive] = useState<Cell | null>(null)
  const [draft, setDraft] = useState<Record<string, CellValue> | null>(null)
  const [draftError, setDraftError] = useState('')
  const [draftBusy, setDraftBusy] = useState(false)
  const [edit, setEdit] = useState<Edit | null>(null)
  const [rowDetails, setRowDetails] = useState<DatasetRow | null>(null)
  const [saveError, setSaveError] = useState<{ message: string; field?: boolean; notice?: boolean } | null>(null)
  const [stale, setStale] = useState(false)
  const [busy, setBusy] = useState(false)
  const editing = !!edit || !!draft || !!rowDetails || batchBusy
  const addingRow = !!draft
  const offset = offsets[pagination.pageIndex] ?? 0
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

  const summaryKey = JSON.stringify([dataset.revision, refresh, summaryRequest])
  const currentSummaryError = summaryError?.key === summaryKey ? summaryError.message : null
  const currentSummary = summary?.key === summaryKey ? summary.data : null
  useEffect(() => {
    if (!showSummaries || !Object.keys(summaryRequest.summaries).length) return
    const controller = new AbortController()
    void api<DatasetSummaryResult>(`${url}/summary`, {
      method: 'POST', json: summaryRequest, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.schema_revision !== dataset.revision) {
        reloadDataset()
        return
      }
      setSummary({ key: summaryKey, data: result })
      setSummaryError(null)
    }).catch(error => {
      if (!controller.signal.aborted) setSummaryError({ key: summaryKey, message: error.message })
    })
    return () => controller.abort()
  }, [dataset.revision, refresh, reloadDataset, showSummaries, summaryKey, summaryRequest, url])

  const groupsRequest = groupColumn ? JSON.stringify({
    ...summaryRequest, summaries: showSummaries ? summaryRequest.summaries : {},
    group_by: groupColumn.key, offset: groupOffset, limit: GROUP_PAGE_SIZE,
  }) : null
  const groupsRequestKey = JSON.stringify([groupsRequest, dataset.revision, refresh])
  const groups = groupResult?.request === groupsRequestKey ? groupResult.data : null
  const groupError = groupsError?.request === groupsRequestKey ? groupsError.message : null

  useEffect(() => {
    if (!groupsRequest) return
    const controller = new AbortController()
    void api<DatasetGroupsPage>(`${url}/groups`, {
      method: 'POST', body: groupsRequest, headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.schema_revision !== dataset.revision) reloadDataset()
      setGroupResult({ request: groupsRequestKey, data: result })
      setGroupsError(null)
    }).catch(error => {
      if (!controller.signal.aborted) setGroupsError({ request: groupsRequestKey, message: error.message })
    })
    return () => controller.abort()
  }, [dataset.revision, groupsRequest, groupsRequestKey, reloadDataset, url])

  useLayoutEffect(() => {
    if (busy || !restoreEditorFocus.current) return
    restoreEditorFocus.current = false
    if (edit) document.getElementById(editId)?.focus()
  }, [busy, edit, editId])

  useEffect(() => {
    const viewport = gridViewport.current
    if (!viewport) return
    const observer = new ResizeObserver(() => setViewportWidth(viewport.clientWidth))
    observer.observe(viewport)
    return () => observer.disconnect()
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
    function clearOutsideCell(event: PointerEvent) {
      const target = event.target
      if (target instanceof Element && (inDatasetCalendar(target)
        || target.closest('[data-dataset-clipboard]')
        || (gridViewport.current?.contains(target) && inDatasetCell(target)))) return
      setActive(null)
      if (table.getFocusedCell()) table.resetCellSelection(true)
    }
    document.addEventListener('pointerdown', clearOutsideCell, true)
    return () => document.removeEventListener('pointerdown', clearOutsideCell, true)
  }, [table])
  const rows = table.getRowModel().rows
  const scrollViewport = () => gridViewport.current?.querySelector<HTMLDivElement>('[data-slot="table-container"]') ?? null
  const useVirtualRows = !groupColumn && rows.length > 25
  const virtualizer = useVirtualizer({
    count: useVirtualRows ? rows.length : 0,
    getScrollElement: scrollViewport,
    estimateSize: () => HEIGHTS[rowHeight],
    overscan: 8,
    getItemKey: index => rows[index]?.id ?? index,
    rangeExtractor: range => {
      const indices = defaultRangeExtractor(range)
      const current = edit ? rows.findIndex(row => row.id === edit.row.id) : -1
      return current < 0 || indices.includes(current) ? indices : [...indices, current].sort((a, b) => a - b)
    },
  })
  const virtualRows = virtualizer.getVirtualItems()
  useEffect(() => {
    if (autoOffset === null || groupColumn) return
    const controller = new AbortController()
    const fields = new Set(dataset.columns.map(column => column.key))
    const filterTree = keepDatasetFilterFields(filters, fields)
    void api<DatasetRowPage>(`${url}/query`, {
      method: 'POST', signal: controller.signal, json: {
        search: search || null, ...(filterTree.children.length ? { filter_tree: filterTree } : {}),
        sorts: sorting.filter(rule => fields.has(rule.id)).map(rule => ({ field: rule.id, descending: rule.desc })),
        offset: autoOffset, limit: pagination.pageSize,
      },
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.schema_revision !== dataset.revision) { reloadDataset(); return }
      setAutoPage(current => {
        const previous = current ?? page
        return previous ? { ...result, items: [...previous.items, ...result.items] } : result
      })
    }).catch(error => {
      if (!controller.signal.aborted) setLoadError(error.message)
    }).finally(() => {
      if (!controller.signal.aborted) setAutoOffset(null)
    })
    return () => controller.abort()
  }, [autoOffset, dataset.columns, dataset.revision, filters, groupColumn, page, pagination.pageSize, reloadDataset, search, sorting, url])

  function clearAutoPages() {
    setAutoOffset(null)
    setAutoPage(null)
    const viewport = scrollViewport()
    if (viewport) viewport.scrollTop = 0
  }

  function loadMoreOnScroll() {
    if (!useVirtualRows || editing || loadError || autoOffset !== null || displayPage?.next_offset == null) return
    const viewport = scrollViewport()
    if (viewport && viewport.scrollTop > 0 && viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < HEIGHTS[rowHeight] * 4) {
      setAutoOffset(displayPage.next_offset)
    }
  }
  const pinnedStyle = (column: (ReturnType<typeof table.getVisibleLeafColumns>)[number]): CSSProperties | undefined =>
    column.getIsPinned() === 'start' ? { insetInlineStart: column.getStart('start') } : undefined
  const orderedVisible = [
    ...table.getStartVisibleLeafColumns(), ...table.getCenterVisibleLeafColumns(), ...table.getEndVisibleLeafColumns(),
  ]
  const pinnedClass = '!sticky z-10 bg-background'
  const selectedCount = rows.filter(row => row.getIsSelected()).length
  const selectedCell = active && rows.some(row => row.id === active.row) && layout.fields.some(column => column.key === active.column)
    ? active : null
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
    if (groupColumn && selectedGroup === undefined) return
    let active = true
    const fields = new Set(dataset.columns.map(column => column.key))
    const filterTree = keepDatasetFilterFields(filters, fields)
    api<DatasetRowPage>(`${url}/${groupColumn ? "groups/query" : "query"}`, {
      method: 'POST', json: {
        search: search || null, ...(filterTree.children.length ? { filter_tree: filterTree } : {}),
        sorts: sorting.filter(rule => fields.has(rule.id)).map(rule => ({ field: rule.id, descending: rule.desc })),
        ...(groupColumn && selectedGroup !== undefined ? { group_by: groupColumn.key, group: JSON.parse(selectedGroup) as CellValue } : {}),
        offset, limit: pagination.pageSize,
      },
    }).then(result => {
      if (!active) return
      if (result.schema_revision !== dataset.revision) reloadDataset()
      setPage(result)
      setLoadError('')
    }).catch(error => {
      if (active) setLoadError(error.message)
    })
    return () => { active = false }
  }, [filters, dataset.columns, dataset.revision, groupColumn, offset, pagination.pageSize, refresh, reloadDataset, search, selectedGroup, sorting, url])

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
    clearAutoPages()
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

  function keepInvalidEditorFocused() {
    if (!edit) return false
    const control = document.getElementById(editId)
    const invalidInput = control instanceof HTMLInputElement && !control.checkValidity()
    if (!invalidInput && (!saveError || saveError.notice)) return false
    control?.focus()
    return true
  }

  function beginEdit(row: DatasetRow, column: DatasetColumn) {
    if (!editable || editing || saving.current || datasetReadOnly(column.kind)) return
    setActive({ row: row.id, column: column.key })
    setSaveError(null)
    setStale(false)
    setEdit({ row, column, value: row.values[column.key] ?? null })
  }

  async function applyBatch(updates: DatasetBatchRow[], previous = false, append: Record<string, CellValue>[] = []) {
    if (!editable || editing || batchLock.current || (!updates.length && !append.length && !previous)) return
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
          if (!column || datasetReadOnly(column.kind)) throw new Error('dataset.clipboardReadOnly')
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
          if (!field || datasetReadOnly(field.kind) || (direction === 'down' ? i === range.minRowIndex : j === range.minColumnIndex)) continue
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
      const values = Object.fromEntries(dataset.columns.filter(column => !datasetReadOnly(column.kind)).map(column => [
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
    return <TableRow key={row.id} data-testid="dataset-row" data-state={row.getIsSelected() ? 'selected' : undefined}
      className="group/row" data-index={index} ref={useVirtualRows ? virtualizer.measureElement : undefined}
      style={{ height: HEIGHTS[rowHeight] }}>
      <TableCell className={cn(DIVIDER, 'p-0')}><label className="grid min-h-10 cursor-pointer place-items-center">
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
        const cellEditable = editable && !datasetReadOnly(column.kind)
      const usesPicker = column.kind === 'boolean' || column.kind === 'select'
      const multiSelect = column.kind === 'multi_select'
        return <TableCell key={cell.id} data-dataset-cell="" style={pinnedStyle(cell.column)} className={cn(DIVIDER, 'relative p-0 whitespace-normal',
          (isEditing && isSelected) || isFocused ? 'bg-muted outline-1 -outline-offset-1 outline-foreground has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2' : 'hover:bg-muted',
          rangeSelected && 'bg-accent',
          cell.column.getIsPinned() && pinnedClass,
        )}>
          {isEditing ? <form onFocus={event => {
            if (!isSelected && event.currentTarget.contains(event.target)) setActive({ row: row.id, column: column.key })
          }} onSubmit={event => {
            event.preventDefault()
            void save(edit.value)
          }} onKeyDown={event => {
            if (inDatasetCalendar(event.target)) return
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && event.target instanceof HTMLTextAreaElement
              && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void save(edit.value)
            }
            if (event.key === 'Escape' && !busy && !event.nativeEvent.isComposing) { event.stopPropagation(); closeEditor() }
          }} onBlur={event => {
            if (!usesPicker && !multiSelect && !saveError && !inDatasetCalendar(event.target) && !inDatasetCalendar(event.relatedTarget)
              && !event.currentTarget.contains(event.relatedTarget) && event.currentTarget.checkValidity()) {
              void save(edit.value, false)
            }
          }}>
            <DatasetValueField id={editId} label={column.label} column={column} value={edit.value} focus inline openPicker disabled={busy}
              error={saveError?.notice ? undefined : saveError?.message}
              onCalendarPick={column.kind === 'date' && !stale ? value => { void save(value) } : undefined}
              onChange={value => {
                if (saveError?.field) setSaveError(null)
                if (usesPicker && !stale) void save(value)
                else setEdit({ ...edit, value })
              }} />
            {multiSelect && !saveError && <div className="flex gap-1 p-1">
              <Button type="submit" variant="outline" size="sm" disabled={busy}>{t('common.save')}</Button>
              <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => closeEditor()}>{t('common.cancel')}</Button>
            </div>}
            {saveError && !saveError.field && <div className="space-y-1 px-2 pb-2">
              {saveError.notice && <div role="status" className="text-xs wrap-anywhere text-muted-foreground">{saveError.message}</div>}
              {stale ? <Button type="button" variant="outline" size="sm" onClick={refreshEdit} disabled={busy}>{t('dataset.refreshEdit')}</Button>
                : <Button type="submit" variant="outline" size="sm" disabled={busy}>{t('common.save')}</Button>}
            </div>}
          </form> :
            <Button id={buttonId} variant="ghost" tabIndex={isTabStop ? 0 : -1}
              className={cn(CELL_BUTTON, 'absolute inset-0 h-full touch-manipulation px-2 font-normal focus-visible:border-transparent focus-visible:ring-0', column.kind === 'url' && value && 'pr-9')}
              aria-label={t(cellEditable ? 'dataset.editCell' : 'dataset.readCell', { field: column.label, value: displayColumnValue(value, column, t('dataset.valueTrue'), t('dataset.valueFalse')) })}
              aria-pressed={isFocused || rangeSelected}
              onMouseDown={event => { if (!editing && event.button === 0) cell.getSelectionStartHandler()(event) }}
              onMouseEnter={event => { if (!editing) cell.getSelectionExtendHandler()(event) }}
              onPointerDown={event => { if (keepInvalidEditorFocused()) event.preventDefault() }}
              onFocus={() => { if (!draft && !keepInvalidEditorFocused()) setActive({ row: row.id, column: column.key }) }}
              onBlur={event => { if (!inDatasetCell(event.relatedTarget)) setActive(null) }}
              onClick={() => { if (!draft && !keepInvalidEditorFocused()) setActive({ row: row.id, column: column.key }) }}
              onDoubleClick={() => beginEdit(row.original, column)}
              onKeyDown={event => handleCellKey(event, row.original, column)}>
              <span className={cn('min-w-0 truncate', column.kind === 'select' && value !== null && 'rounded bg-muted px-1.5')}>{displayColumnValue(value, column, t('dataset.valueTrue'), t('dataset.valueFalse')) || '—'}</span>
            </Button>
          }
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
            {group.group === null ? t('dataset.groupEmpty') : format(group.group, columnKind)}
            <span className="tabular-nums text-muted-foreground">{t('dataset.groupRows', { count: group.total })}</span>
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
            <Button variant="outline" size="icon" aria-label={t('dataset.clipboardMenu')} data-dataset-clipboard="" disabled={editing}><Clipboard /></Button>
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
        <Popover>
          <PopoverTrigger asChild><Button variant="outline" size="icon" disabled={editing} aria-label={t('dataset.gridLayout')}><Settings2 /></Button></PopoverTrigger>
          <PopoverContent align="start" className="grid gap-2">
            <Select value={rowHeight} disabled={editing} onValueChange={value => {
              setRowHeight(value as GridRowHeight)
              virtualizer.measure()
            }}>
              <SelectTrigger aria-label={t('dataset.rowHeight')}><SelectValue /></SelectTrigger>
              <SelectContent>{(Object.keys(HEIGHTS) as GridRowHeight[]).map(size =>
                <SelectItem value={size} key={size}>{t(`dataset.rowHeights.${size}`)}</SelectItem>)}</SelectContent>
            </Select>
            <Select value={String(pinning.start?.length ?? 0)} disabled={editing} onValueChange={value => {
              table.setColumnPinning({ start: orderedVisible.slice(0, Number(value)).map(column => column.id), end: [] })
            }}>
              <SelectTrigger aria-label={t('dataset.freezeColumns')}><SelectValue /></SelectTrigger>
              <SelectContent>{[0, 1, 2, 3].map(count =>
                <SelectItem value={String(count)} key={count} disabled={count > orderedVisible.length}>
                  {t('dataset.frozenCount', { count })}
                </SelectItem>)}</SelectContent>
            </Select>
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
          <SelectTrigger aria-label={t('dataset.groupBy')}><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="$none">{t('dataset.noGrouping')}</SelectItem>
            {dataset.columns.filter(column => datasetGroupable(column.kind)).map(column =>
              <SelectItem value={column.key} key={column.key}>{column.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant={showSummaries ? 'secondary' : 'outline'} aria-pressed={showSummaries} disabled={editing}
          onClick={() => { setSummary(null); setSummaryError(null); setShowSummaries(value => !value) }}>{t('dataset.summary')}</Button>
        <DatasetQueryControls columns={dataset.columns} disabled={editing} filters={filters} sorting={sorting}
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
    }} onScrollCapture={loadMoreOnScroll} className="border-y [&>[data-slot=table-container]]:max-h-[70dvh] [&>[data-slot=table-container]]:overflow-auto">
      <Table aria-label={t('dataset.gridView')} aria-busy={groupColumn ? !groups && !groupError : !page && !loadError}
        className="table-fixed" style={{ width: layout.width }}>
        <colgroup>
          <col style={{ width: ROW_NUMBER_WIDTH }} />
          {layout.showRowId && <col style={{ width: ROW_ID_WIDTH }} />}
          {orderedVisible.map(column => <col key={column.id} style={{ width: column.getSize() }} />)}
          <col />
        </colgroup>
        <TableHeader className="bg-muted/50"><TableRow className="hover:bg-transparent">
          <TableHead scope="col" className={cn(DIVIDER, 'p-0')}><div className="grid place-items-center"><Checkbox aria-label={t('dataset.selectVisibleRows')}
            disabled={!rows.length} checked={table.getIsAllRowsSelected() || (table.getIsSomeRowsSelected() ? 'indeterminate' : false)}
            onCheckedChange={checked => table.toggleAllRowsSelected(checked === true)} /></div></TableHead>
          {layout.showRowId && <TableHead scope="col" className={DIVIDER}>{t('dataset.rowId')}</TableHead>}
          {[...table.getStartFlatHeaders(), ...table.getCenterFlatHeaders(), ...table.getEndFlatHeaders()].map(header => {
            const direction = header.column.getIsSorted()
            const priority = header.column.getSortIndex()
            const column = heading(header.column.id)!
            const Icon = direction === 'asc' ? ArrowUp : direction === 'desc' ? ArrowDown : ArrowUpDown
            return <TableHead key={header.id} scope="col" style={pinnedStyle(header.column)}
              className={cn(DIVIDER, 'relative p-0 hover:bg-muted', header.column.getIsPinned() && pinnedClass)}
              aria-sort={priority === 0 && direction ? (direction === 'asc' ? 'ascending' : 'descending') : undefined}>
              <Button variant="ghost" size="sm" className={cn(CELL_BUTTON, 'absolute inset-y-0 left-0 right-2 h-full gap-1 px-2')}
                onClick={header.column.getToggleSortingHandler()} disabled={!!edit || !!draft}>
                <DatasetFieldIcon kind={column.kind} />
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
        </TableRow></TableHeader>
        <TableBody>
          {draft && <TableRow ref={draftRow} data-testid="dataset-row-draft" className="bg-muted/40" onKeyDown={event => {
            if (inDatasetCalendar(event.target)) return
            if (event.key === 'Escape' && !event.defaultPrevented && !draftBusy) cancelDraft()
            if (event.key === 'Enter' && event.target instanceof HTMLInputElement && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void saveDraft()
            }
          }}>
            <TableCell className={cn(DIVIDER, 'p-0')}><div className="grid min-h-10 place-items-center">
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
              const gap = item.start - (virtualRows[index - 1]?.end ?? 0)
              return <Fragment key={item.key}>
                {gap > 0 && <TableRow aria-hidden="true"><TableCell colSpan={span} style={{ height: gap }} className="border-0 p-0" /></TableRow>}
                {renderRow(rows[item.index], item.index)}
              </Fragment>
            })}
            <TableRow aria-hidden="true"><TableCell colSpan={span}
              style={{ height: Math.max(0, virtualizer.getTotalSize() - (virtualRows.at(-1)?.end ?? 0)) }} className="border-0 p-0" /></TableRow>
          </> : rows.map(renderRow)}
        </TableBody>
        {showSummaries && <TableFooter>
          {table.getFooterGroups().map(group => <TableRow key={group.id}>
            <TableCell aria-label={t('dataset.summary')} colSpan={layout.showRowId ? 2 : 1} />
            {group.headers.map(header => {
              const column = layout.fields.find(field => field.key === header.column.id)
              return <TableCell key={header.id} className={DIVIDER}>
                {!header.isPlaceholder && column && <DatasetColumnSummary column={column}
                  operation={summaryColumns[column.key]} value={currentSummary?.values[column.key]} disabled={editing}
                  loading={!currentSummary} failed={!!currentSummaryError}
                  onChange={operation => setSummaryOperations(current => ({ ...current, [column.key]: operation }))} />}
              </TableCell>
            })}
            <TableCell className={ROW_ACTIONS} />
          </TableRow>)}
          {currentSummaryError && <TableRow><TableCell colSpan={span}>
            <Alert variant="warning"><AlertDescription>{currentSummaryError}</AlertDescription></Alert>
          </TableCell></TableRow>}
        </TableFooter>}
      </Table>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1 text-sm">
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
          {notice && <><Check aria-hidden="true" className="size-3" />{notice}</>}
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
