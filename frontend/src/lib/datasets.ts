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
  revision: number
}
export type Dataset = DatasetSummary & { columns: DatasetColumn[] }
export type DatasetRow = { id: string; revision: number; values: Record<string, CellValue> }
export type DatasetPage<T> = { items: T[]; next_offset: number | null }
export type DatasetRowPage = DatasetPage<DatasetRow> & { schema_revision: number }
export type DatasetRowResult = { row: DatasetRow; inserted: boolean }
export const DATASET_QUERY_LIMIT = 12
export type DatasetTeam = { id: string; name: string; mine: boolean }

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
