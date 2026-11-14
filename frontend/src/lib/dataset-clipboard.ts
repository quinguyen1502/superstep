import Papa from 'papaparse'
import { datasetSystemTime, type CellValue, type DatasetColumn } from './datasets'

export type DatasetBatchRow = { id: string; revision: number; values: Record<string, CellValue> }
export type DatasetBatchResult = { schema_revision: number; added?: { id: string; revision: number }[]; rows: { id: string; revision: number; previous: Record<string, CellValue> }[] }

export function datasetClipboardText(ranges: unknown[][][]): string {
  return ranges.map(range => Papa.unparse(range.map(row => row.map(value => Array.isArray(value) ? value.join(';') : value)),
    { delimiter: '\t', newline: '\n', escapeFormulae: true })).join('\n\n')
}

export function datasetClipboardRows(text: string): string[][] {
  const result = Papa.parse<string[]>(text.replace(/\r?\n$/, ''), { delimiter: text.includes('\t') ? '\t' : '' })
  if (result.errors.some(error => error.code !== 'UndetectableDelimiter')) throw new Error('dataset.clipboardParse')
  return result.data
}

export function datasetClipboardValue(value: string, column: DatasetColumn): CellValue {
  if (value === '') return null
  const text = /^'[=+\-@\t\r]/.test(value) ? value.slice(1) : value
  if (column.kind === 'multi_select') return text.split(';')
  if (column.kind === 'number') {
    const number = Number(text)
    return Number.isFinite(number) && text.trim() ? number : text
  }
  if (column.kind === 'boolean') {
    if (/^(true|1)$/i.test(text)) return true
    if (/^(false|0)$/i.test(text)) return false
  }
  if ((column.kind === 'datetime' || datasetSystemTime(column.kind)) && /^\d{4}-\d\d-\d\dT/.test(text)) {
    const date = new Date(text)
    if (!Number.isNaN(date.getTime())) return date.toISOString()
  }
  return text
}
