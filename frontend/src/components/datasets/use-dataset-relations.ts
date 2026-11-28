import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { datasetUrl, type Dataset, type DatasetColumn, type DatasetPage, type DatasetRow, type DatasetSummary } from '@/lib/datasets'
import { errorText } from '@/lib/i18n'

export const RELATION_PAGE_SIZE = 25

export type RelationChoice = { id: string; label: string | null }

export function readRelationChoices(dataset: Pick<Dataset, 'id' | 'revision'>, field: string, options: {
  search?: string; offset?: number; rowIds?: string[]
}, signal: AbortSignal) {
  const query = new URLSearchParams({ schema_revision: String(dataset.revision), limit: String(RELATION_PAGE_SIZE) })
  if (options.search) query.set('search', options.search)
  if (options.offset) query.set('offset', String(options.offset))
  if (options.rowIds) {
    query.set('limit', '50')
    for (const id of options.rowIds) query.append('row_ids', id)
  }
  return api<DatasetPage<RelationChoice>>(
    `${datasetUrl(dataset.id)}/columns/${encodeURIComponent(field)}/relation/rows?${query}`, { signal },
  )
}

type RelationLabels = Record<string, Record<string, string | null>>
const EMPTY_LABELS: RelationLabels = {}

export function useDatasetRelationLabels(dataset: Dataset, columns: DatasetColumn[], rows: DatasetRow[], refresh = '') {
  const { id, revision } = dataset
  const source = `${id}:${revision}`
  const request = JSON.stringify(columns.filter(column => column.kind === 'relation').map(column => {
    const ids = rows.map(row => row.values[column.key]).filter((value): value is string => typeof value === 'string')
    return [column.key, [...new Set(ids)].sort()]
  }))
  const [result, setResult] = useState<{ source: string; labels: RelationLabels } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const labels: RelationLabels = {}
    const entries: [string, string[]][] = JSON.parse(request)
    const batches = entries.flatMap(([field, ids]) => {
      labels[field] = Object.fromEntries(ids.map(id => [id, null]))
      return Array.from({ length: Math.ceil(ids.length / 50) }, (_, index) => ({ field, ids: ids.slice(index * 50, (index + 1) * 50) }))
    })
    if (!batches.length) return
    void Promise.all(batches.map(async batch => {
      try {
        const page = await readRelationChoices({ id, revision }, batch.field, { rowIds: batch.ids }, controller.signal)
        for (const choice of page.items) labels[batch.field][choice.id] = choice.label?.trim() ? choice.label : choice.id
      } catch {
        // Never substitute an ID when the authorized lookup fails.
      }
    })).then(() => {
      if (!controller.signal.aborted) setResult({ source, labels })
    })
    return () => controller.abort()
  }, [id, revision, source, request, refresh])

  return result?.source === source ? result.labels : EMPTY_LABELS
}

export function useDatasetRelationTargets(dataset: Dataset | null, enabled: boolean) {
  const id = dataset?.id
  const team = dataset?.team_id
  const owner = dataset?.owner_id
  const scope = JSON.stringify([id, team, owner])
  const [state, setState] = useState<{ scope: string; items: DatasetSummary[]; error: string }>()
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!id || !enabled) return
    const controller = new AbortController()
    async function load() {
      const items: DatasetSummary[] = []
      let offset: number | null = 0
      try {
        while (offset !== null && !controller.signal.aborted) {
          const page: DatasetPage<DatasetSummary> = await api(`${datasetUrl()}?limit=100&offset=${offset}`, { signal: controller.signal })
          items.push(...page.items.filter(item => item.id !== id && (team ? item.team_id === team : !item.team_id && item.owner_id === owner)))
          offset = page.next_offset
        }
        if (!controller.signal.aborted) setState({ scope, items, error: '' })
      } catch (error) {
        if (!controller.signal.aborted) setState({ scope, items: [], error: error instanceof Error ? error.message : errorText({ code: 'INTERNAL_ERROR' }) })
      }
    }
    void load()
    return () => controller.abort()
  }, [attempt, enabled, id, owner, scope, team])

  const current = state?.scope === scope ? state : undefined
  return {
    items: current?.items ?? [],
    loading: enabled && !current,
    error: current?.error ?? '',
    retry: () => { setState(undefined); setAttempt(value => value + 1) },
  }
}
