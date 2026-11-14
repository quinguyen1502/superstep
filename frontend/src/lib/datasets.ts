import { fmtDate, fmtCalendarDate } from "@/lib/i18n"
import { can, type Me } from '@/lib/rbac'

export const datasetKinds = ['text', 'number', 'boolean', 'date', 'datetime', 'email', 'select', 'long_text', 'url', 'created_time', 'updated_time', 'multi_select', 'auto_number'] as const
export type DatasetKind = (typeof datasetKinds)[number]
export const datasetSystemTime = (kind: DatasetKind) => kind === 'created_time' || kind === 'updated_time'
export const datasetReadOnly = (kind: DatasetKind) => datasetSystemTime(kind) || kind === 'auto_number'
export const datasetTextKind = (kind: DatasetKind) => ['text', 'long_text', 'email', 'select', 'url'].includes(kind)
export type ScalarCellValue = string | number | boolean | null
export type CellValue = ScalarCellValue | string[]
export type DatasetColumn = {
  key: string
  label: string
  kind: DatasetKind
  required: boolean
  unique: boolean
  default: CellValue
  options: string[]
}
export type DatasetSummary = {
  id: string
  name: string
  description: string | null
  owner_id: string | null
  team_id: string | null
  team_owner_id?: string | null
  revision: number
}
export type Dataset = DatasetSummary & { columns: DatasetColumn[] }
export type DatasetRow = { id: string; revision: number; values: Record<string, CellValue> }
export type DatasetPage<T> = { items: T[]; next_offset: number | null }
export type DatasetRowPage = DatasetPage<DatasetRow> & { schema_revision: number; total: number; total_capped: boolean }
export type DatasetRowResult = { row: DatasetRow; inserted: boolean }
export const DATASET_QUERY_LIMIT = 12
export const DATASET_FILTER_DEPTH = 3
export const DATASET_FILTER_RULES = 20
export const DATASET_FILTER_VALUES = 50

export type DatasetFilterValue = ScalarCellValue | ScalarCellValue[]
export type DatasetFilterRule = { type: 'rule'; field: string; op: string; value: DatasetFilterValue }
export type DatasetFilters = {
  type: 'group'
  conjunction: 'and' | 'or'
  children: (DatasetFilters | DatasetFilterRule)[]
}

export const emptyDatasetFilters = (): DatasetFilters => ({ type: 'group', conjunction: 'and', children: [] })
export const datasetFilterRules = ({ children }: DatasetFilters): DatasetFilterRule[] =>
  children.flatMap(child => child.type === 'rule' ? [child] : datasetFilterRules(child))

export function keepDatasetFilterFields(tree: DatasetFilters, fields: ReadonlySet<string>): DatasetFilters {
  const children: DatasetFilters['children'] = []
  for (const child of tree.children) {
    if (child.type === 'rule') {
      if (fields.has(child.field)) children.push(child)
    } else {
      const group = keepDatasetFilterFields(child, fields)
      if (group.children.length) children.push(group)
    }
  }
  return { ...tree, children }
}

export const datasetListFilter = (op: string) => op === 'in' || op === 'not_in' || op === 'contains_any' || op === 'contains_all'
export const datasetSubstringFilter = (op: string) => op === 'contains' || op === 'not_contains'
export const datasetValueFreeFilter = (op: string) => op === 'is_null' || op === 'not_null'
const generalSummaryFunctions = ['count', 'empty_count', 'empty_percent', 'unique_count'] as const
export type DatasetSummaryFunction = (typeof generalSummaryFunctions)[number] | 'sum' | 'avg' | 'min' | 'max'
export type DatasetColumnSummaries = Partial<Record<string, DatasetSummaryFunction>>
export type DatasetSummaryResult = { total: number; values: Record<string, CellValue>; schema_revision: number }
export type DatasetRowGroup = { group: CellValue; total: number; values: Record<string, CellValue> }
export type DatasetGroupsPage = { groups: DatasetRowGroup[]; next_offset: number | null; schema_revision: number }
export const datasetGroupable = (kind: DatasetKind) => ['select', 'boolean', 'text', 'date'].includes(kind)


export function datasetSummaryFunctions(kind: DatasetKind): readonly DatasetSummaryFunction[] {
  if (kind === 'number' || kind === 'auto_number') return [...generalSummaryFunctions, 'sum', 'avg', 'min', 'max']
  if (kind === 'date' || kind === 'datetime' || datasetSystemTime(kind)) return [...generalSummaryFunctions, 'min', 'max']
  return generalSummaryFunctions
}

export type DatasetTeam = { id: string; name: string; mine: boolean }

/** Schema, access, tokens and deletion: the personal owner, a team dataset's owner, or an admin. Rows need only resources.manage. */
export function canManageDataset(me: Me | null, dataset: DatasetSummary) {
  if (!me || !can(me, 'resources.manage')) return false
  return dataset.team_id ? dataset.team_owner_id === me.id || can(me, 'org.manage') : dataset.owner_id === me.id
}

export const datasetUrl = (id?: string) => id ? `/api/datasets/${encodeURIComponent(id)}` : '/api/datasets'

export function newDatasetColumn(): DatasetColumn {
  return { key: '', label: '', kind: 'text', required: false, unique: false, default: null, options: [] }
}

export function displayValue(value: CellValue, yes: string, no: string, kind?: DatasetKind) {
  if (value === null) return '—'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'boolean') return value ? yes : no
  if (typeof value === 'string') {
    if (kind === 'date') return fmtCalendarDate(value)
    if (kind === 'datetime' || (kind && datasetSystemTime(kind))) return fmtDate(Date.parse(value) / 1000)
  }
  return String(value)
}

export type ColumnDraft = DatasetColumn & { optionsText: string }
export const toDraft = (column: DatasetColumn): ColumnDraft => ({ ...column, optionsText: column.options.join('\n') })

export function fromDraft({ optionsText, ...column }: ColumnDraft): DatasetColumn {
  return { ...column, key: column.key.trim(), label: column.label.trim(),
    options: column.kind === 'select' || column.kind === 'multi_select' ? optionsText.split('\n').map(option => option.trim()).filter(Boolean) : [] }
}

export const datasetOperations = ['find_rows', 'aggregate_rows', 'get_row', 'insert_row', 'upsert_row', 'delete_row'] as const
export type DatasetOperation = (typeof datasetOperations)[number]
export type DatasetGrantPermission = 'read' | 'write' | 'read_write'

export const DATASET_AGENT_MAX_ROWS = 20
/** What an Agent Dataset tool may do. Delete row is never offered to an Agent. */
export const datasetAgentOperations = ['find_rows', 'aggregate_rows', 'insert_row', 'upsert_row'] as const
export type DatasetAgentOperation = (typeof datasetAgentOperations)[number]

export function datasetFilterOperators(kind: DatasetColumn['kind']) {
  if (kind === 'multi_select') return ['contains_any', 'contains_all', 'is_null']
  if (kind === 'boolean') return ['eq', 'ne', 'is_null', 'not_null', 'in', 'not_in']
  const operators = ['eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'is_null', 'not_null']
  if (datasetTextKind(kind)) operators.push('contains', 'not_contains')
  return [...operators, 'in', 'not_in']
}

export const datasetWriteOperation = (operation?: DatasetOperation) => operation === 'insert_row' || operation === 'upsert_row'

export type DatasetNodePermission = 'read' | 'write' | 'delete'
export function datasetNodePermission(operation?: DatasetOperation): DatasetNodePermission {
  return operation === 'delete_row' ? 'delete' : datasetWriteOperation(operation) ? 'write' : 'read'
}

export type DatasetNodeConfig = {
  dataset_id?: string
  operation?: DatasetOperation
  fields?: string[]
  output_field?: string
  arguments?: {
    values?: Record<string, CellValue>
    key?: string
    value?: CellValue
    row_id?: string
    limit?: number
    offset?: number
    search?: string | null
    filter_mode?: 'and' | 'or'
    filters?: { field: string; op: string; value: ScalarCellValue }[]
    filter_tree?: DatasetFilters
    summaries?: DatasetColumnSummaries
    group_by?: string
    sorts?: { field: string; descending: boolean }[]
  }
}

/** The label and value that name a row in a delete confirmation: its first unique field with a value. */
export function deleteRowName(dataset: Dataset, row: DatasetRow): { label: string; value: string } | null {
  for (const column of dataset.columns) {
    const value = row.values[column.key]
    if (column.unique && value !== null && value !== undefined && value !== '') return { label: column.label, value: String(value) }
  }
  return null
}

export type CsvIssue = { row: number; field: string | null; value?: string | null; error: { code?: string; message?: string; details?: Record<string, unknown> } }

/** Issues ordered by CSV line, and the number of issues of each error code in first-seen order. */
export function csvIssueSummary(issues: CsvIssue[]): { sorted: CsvIssue[]; counts: [string, number][] } {
  const sorted = [...issues].sort((a, b) => a.row - b.row)
  const counts = new Map<string, number>()
  for (const issue of sorted) {
    const code = issue.error.code ?? 'INTERNAL_ERROR'
    counts.set(code, (counts.get(code) ?? 0) + 1)
  }
  return { sorted, counts: [...counts] }
}

/** A rejected cell for display: at most `max` characters, with an ellipsis when cut. */
export function shortCsvValue(value: string, max = 60): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}
