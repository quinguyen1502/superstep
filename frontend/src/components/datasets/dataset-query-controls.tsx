import { useRef, useState } from 'react'
import type { SortingState } from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ArrowUpDown, ListFilter, Plus, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription } from '@/components/ui/empty'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { DATASET_QUERY_LIMIT, datasetFilterRules, emptyDatasetFilters, keepDatasetFilterFields, type DatasetColumn, type DatasetFilters } from '@/lib/datasets'
import { DatasetFieldIcon } from './dataset-field-icon'
import { DatasetFilterBuilder, validDatasetFilters } from './dataset-filter-builder'

type SortDraft = SortingState[number] & { key: number }

export function DatasetQueryControls({ columns, disabled, filters, sorting, onFilters, onSorting }: {
  columns: DatasetColumn[]
  disabled: boolean
  filters: DatasetFilters
  sorting: SortingState
  onFilters: (filters: DatasetFilters) => void
  onSorting: (sorting: SortingState) => void
}) {
  const { t } = useTranslation()
  const nextKey = useRef(0)
  const [panel, setPanel] = useState<'filter' | 'sort' | null>(null)
  const [filterDraft, setFilterDraft] = useState(emptyDatasetFilters)
  const activeCount = datasetFilterRules(filters).length
  const [sortDraft, setSortDraft] = useState<SortDraft[]>([])
  const hasColumn = (key: string) => columns.some(column => column.key === key)

  function addSort() {
    const key = nextKey.current++
    setSortDraft(current => [...current, { key, id: '', desc: false }])
  }

  function changePanel(name: 'filter' | 'sort', open: boolean) {
    if (open && name === 'filter') {
      const tree = keepDatasetFilterFields(filters, new Set(columns.map(column => column.key)))
      setFilterDraft(tree.children.length ? tree : { ...tree, children: [{ type: 'rule', field: '', op: 'eq', value: null }] })
    }
    if (open && name === 'sort') {
      const rules = sorting.filter(rule => hasColumn(rule.id)).map(rule => ({ ...rule, key: nextKey.current++ }))
      setSortDraft(rules.length ? rules : [{ key: nextKey.current++, id: '', desc: false }])
    }
    setPanel(current => open ? name : current === name ? null : current)
  }

  function updateSort(key: number, change: Partial<SortingState[number]>) {
    setSortDraft(current => current.map(rule => rule.key === key ? { ...rule, ...change } : rule))
  }

  function moveSort(from: number, to: number) {
    setSortDraft(current => {
      const next = [...current]
      const rule = next[from]
      next[from] = next[to]
      next[to] = rule
      return next
    })
  }

  function applyFilters(next: DatasetFilters) {
    onFilters(next)
    setPanel(null)
  }

  function applySort(next: SortingState) {
    onSorting(next)
    setPanel(null)
  }

  return <>
    <Popover open={panel === 'filter'} onOpenChange={open => changePanel('filter', open)}>
      <PopoverTrigger asChild>
        <Button variant={panel === 'filter' || activeCount ? 'secondary' : 'outline'} disabled={disabled} aria-label={t('dataset.filter')} aria-description={activeCount ? t('dataset.activeFilterCount', { count: activeCount }) : undefined}>
          <ListFilter />{t('dataset.filter')}
          {activeCount > 0 && <Badge variant="secondary" size="sm" aria-hidden="true">{activeCount}</Badge>}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" aria-label={t('dataset.filter')} className="max-w-[calc(100vw-1.5rem)] sm:w-152">
        <form className="grid gap-3" onSubmit={event => {
          event.preventDefault()
          if (validDatasetFilters(filterDraft, columns)) applyFilters(filterDraft)
        }}>
          <div className="grid max-h-[45dvh] gap-2 overflow-y-auto p-1">
            <DatasetFilterBuilder tree={filterDraft} columns={columns} onChange={setFilterDraft} />
          </div>
          <p className="text-xs text-muted-foreground">{t('dataset.filterHelp')}</p>
          <Separator />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="ml-auto flex gap-2">
              <Button type="button" variant="ghost" onClick={() => applyFilters(emptyDatasetFilters())}>{t('dataset.resetQuery')}</Button>
              <Button type="submit" disabled={!validDatasetFilters(filterDraft, columns)}>{t('dataset.applyFilters')}</Button>
            </div>
          </div>
        </form>
      </PopoverContent>
    </Popover>
    <Popover open={panel === 'sort'} onOpenChange={open => changePanel('sort', open)}>
      <PopoverTrigger asChild>
        <Button variant={panel === 'sort' || sorting.length ? 'secondary' : 'outline'} disabled={disabled}>
          <ArrowUpDown />{t('dataset.sort')}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" aria-label={t('dataset.sort')} className="max-w-[calc(100vw-1.5rem)] sm:w-132">
        <form className="grid gap-3" onSubmit={event => {
          event.preventDefault()
          applySort(sortDraft.map(({ id: field, desc }) => ({ id: field, desc })))
        }}>
          <div className="grid max-h-[45dvh] gap-2 overflow-y-auto p-1">
            {!sortDraft.length && <Empty className="p-3"><EmptyDescription>{t('dataset.noSortColumns')}</EmptyDescription></Empty>}
            {sortDraft.map((rule, index) => <div key={rule.key} role="group" aria-label={t('dataset.sortPriority', { number: index + 1 })}
              className="flex flex-wrap items-center gap-2">
              <span aria-hidden="true" className="w-4 text-center text-xs tabular-nums text-muted-foreground">{index + 1}</span>
              <div className="grid min-w-44 flex-1 grid-cols-2 gap-2">
                <Select value={rule.id} onValueChange={field => updateSort(rule.key, { id: field })}>
                  <SelectTrigger aria-label={t('dataset.sortColumn')} className="w-full min-w-0"><SelectValue placeholder={t('dataset.sortColumn')} /></SelectTrigger>
                  <SelectContent>{columns.map(column => <SelectItem key={column.key} value={column.key}
                    disabled={sortDraft.some(other => other.key !== rule.key && other.id === column.key)}><DatasetFieldIcon kind={column.kind} /><span className="truncate">{column.label}</span></SelectItem>)}</SelectContent>
                </Select>
                <Select value={rule.desc ? 'desc' : 'asc'} disabled={!rule.id} onValueChange={direction => updateSort(rule.key, { desc: direction === 'desc' })}>
                  <SelectTrigger aria-label={t('dataset.sortDirection')} className="w-full min-w-0"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asc">{t('dataset.ascending')}</SelectItem>
                    <SelectItem value="desc">{t('dataset.descending')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="ml-auto flex items-center">
                <Button type="button" variant="ghost" size="icon" aria-label={t('dataset.moveSortUp')} disabled={index === 0}
                  onClick={() => moveSort(index, index - 1)}><ArrowUp /></Button>
                <Button type="button" variant="ghost" size="icon" aria-label={t('dataset.moveSortDown')} disabled={index === sortDraft.length - 1}
                  onClick={() => moveSort(index, index + 1)}><ArrowDown /></Button>
                <Button type="button" variant="ghost" size="icon" aria-label={t('dataset.removeSortColumn')}
                  onClick={() => setSortDraft(current => current.filter(item => item.key !== rule.key))}><X /></Button>
              </div>
            </div>)}
          </div>
          <Separator />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button type="button" variant="ghost" onClick={addSort} disabled={sortDraft.length >= Math.min(columns.length, DATASET_QUERY_LIMIT)}>
              <Plus />{t('dataset.addSortColumn')}
            </Button>
            <div className="ml-auto flex gap-2">
              <Button type="button" variant="ghost" onClick={() => applySort([])}>{t('dataset.resetQuery')}</Button>
              <Button type="submit" disabled={sortDraft.some(rule => !hasColumn(rule.id))}>{t('dataset.applySort')}</Button>
            </div>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  </>
}
