import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { datasetUrl, type Dataset, type DatasetGrantPermission } from '@/lib/datasets'

export type BindingLookup = {
  id: string
  workflowId?: string
  dataset?: Dataset
  permission?: DatasetGrantPermission | null
  error?: string
  grantError?: string
}
export function useDatasetNodeBinding(datasetId?: string, workflowId?: string) {
  const [lookup, setLookup] = useState<BindingLookup | null>(null)
  useEffect(() => {
    if (!datasetId) return
    const id = datasetId
    let sequence = 0
    let active = true
    async function load() {
      const ticket = ++sequence
      const base = { id, workflowId }
      try {
        const dataset = await api<Dataset>(datasetUrl(id))
        let access: Pick<BindingLookup, 'permission' | 'grantError'> = {}
        if (workflowId) {
          try {
            access = await api<{ permission: DatasetGrantPermission | null }>(
              `${datasetUrl(id)}/access/grants/${encodeURIComponent(workflowId)}`,
            )
          } catch (error) {
            access = { grantError: (error as Error).message }
          }
        }
        if (active && sequence === ticket) setLookup({ ...base, dataset, ...access })
      } catch (error) {
        if (active && sequence === ticket) setLookup({ ...base, error: (error as Error).message })
      }
    }
    void load()
    window.addEventListener('focus', load)
    return () => { active = false; window.removeEventListener('focus', load) }
  }, [datasetId, workflowId])
  return lookup?.id === datasetId && lookup?.workflowId === workflowId ? lookup : null
}
