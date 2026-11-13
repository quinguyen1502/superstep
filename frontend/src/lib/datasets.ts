import { can, type Me } from '@/lib/rbac'

export const datasetKinds = ['text', 'number', 'boolean', 'date', 'datetime', 'email', 'select'] as const
export type DatasetKind = (typeof datasetKinds)[number]
export type CellValue = string | number | boolean | null
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
export type DatasetRowPage = DatasetPage<DatasetRow> & { schema_revision: number }
export type DatasetRowResult = { row: DatasetRow; inserted: boolean }
export const DATASET_QUERY_LIMIT = 12
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

export function displayValue(value: CellValue, yes: string, no: string) {
  return value === null ? '—' : typeof value === 'boolean' ? value ? yes : no : String(value)
}

export type ColumnDraft = DatasetColumn & { optionsText: string }
export const toDraft = (column: DatasetColumn): ColumnDraft => ({ ...column, optionsText: column.options.join('\n') })

export function fromDraft({ optionsText, ...column }: ColumnDraft): DatasetColumn {
  return { ...column, key: column.key.trim(), label: column.label.trim(),
    options: column.kind === 'select' ? optionsText.split('\n').map(option => option.trim()).filter(Boolean) : [] }
}

export const datasetOperations = ['find_rows', 'get_row', 'insert_row', 'upsert_row', 'delete_row'] as const
export type DatasetOperation = (typeof datasetOperations)[number]
export type DatasetGrantPermission = 'read' | 'write' | 'read_write'

export const DATASET_AGENT_MAX_ROWS = 20
/** What an Agent Dataset tool may do. Delete row is never offered to an Agent. */
export const datasetAgentOperations = ['find_rows', 'insert_row', 'upsert_row'] as const
export type DatasetAgentOperation = (typeof datasetAgentOperations)[number]

export function datasetFilterOperators(kind: DatasetColumn['kind']) {
  if (kind === 'boolean') return ['eq', 'ne', 'is_null', 'not_null']
  const operators = ['eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'is_null', 'not_null']
  if (kind === 'text' || kind === 'email' || kind === 'select') operators.push('contains')
  return operators
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
    filters?: { field: string; op: string; value: CellValue }[]
    sorts?: { field: string; descending: boolean }[]
  }
}
