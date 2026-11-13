import { describe, expect, it } from 'vitest'
import { csvIssueSummary, deleteRowName, shortCsvValue, type Dataset } from '@/lib/datasets'

describe('csvIssueSummary', () => {
  it('sorts by line and counts issues per code', () => {
    const { sorted, counts } = csvIssueSummary([
      { row: 7, field: 'score', value: 'no', error: { code: 'DATASET_VALUE_INVALID' } },
      { row: 3, field: 'ticket', value: 'A', error: { code: 'DATASET_UNIQUE_CONFLICT' } },
      { row: 5, field: null, error: { code: 'DATASET_CSV_INVALID' } },
      { row: 4, field: 'score', value: 'x', error: { code: 'DATASET_VALUE_INVALID' } },
    ])
    expect(sorted.map(issue => issue.row)).toEqual([3, 4, 5, 7])
    expect(counts).toEqual([['DATASET_UNIQUE_CONFLICT', 1], ['DATASET_VALUE_INVALID', 2], ['DATASET_CSV_INVALID', 1]])
  })
})

describe('shortCsvValue', () => {
  it('keeps short values and cuts long ones with an ellipsis', () => {
    expect(shortCsvValue('abc')).toBe('abc')
    const cut = shortCsvValue('x'.repeat(100))
    expect(cut).toHaveLength(60)
    expect(cut.endsWith('…')).toBe(true)
  })
})

describe('deleteRowName', () => {
  const dataset = {
    id: 'd', name: 'Tickets', description: null, owner_id: 'u', team_id: null, revision: 1, created: 0, updated: 0,
    columns: [
      { key: 'subject', label: 'Subject', kind: 'text', required: false, unique: false, default: null, options: [] },
      { key: 'ticket', label: 'Ticket', kind: 'text', required: false, unique: true, default: null, options: [] },
    ],
  } as Dataset
  it('names a row by its first unique field with a value', () => {
    expect(deleteRowName(dataset, { id: 'r1', revision: 1, values: { subject: 'Hi', ticket: 'T-1' } })).toEqual({ label: 'Ticket', value: 'T-1' })
  })
  it('falls back to nothing when the unique field is empty', () => {
    expect(deleteRowName(dataset, { id: 'r1', revision: 1, values: { subject: 'Hi', ticket: null } })).toBeNull()
  })
})
