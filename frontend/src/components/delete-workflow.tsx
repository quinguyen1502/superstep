/** Delete a workflow through the shared type-the-name dialog, listing subgraph dependents first (then `force`).
 *  Used by the workflow list and the editor's ⋯ menu. */
import { useTranslation } from 'react-i18next'
import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'

type Dep = { id: string | null; name: string | null }

export function useDeleteWorkflow(onDeleted: () => void) {
  const { t } = useTranslation(); const confirmDel = useConfirmDelete()
  const ask = async (w: { id: string; name: string }) => {
    const deps = await api<{ dependents: Dep[] }>(`/api/workflows/${w.id}/dependents`).then(r => r.dependents).catch(() => [] as Dep[])
    confirmDel.ask({ title: t('list.deleteTitle'), name: w.name, description: t('list.deleteBody', { name: w.name }),
      confirmLabel: deps.length ? t('list.deleteAnyway') : undefined,
      children: deps.length ? <Alert variant="destructive" id="delete-dependents"><AlertCircle /><AlertDescription><div>{t('list.inUse', { count: deps.length })}</div>
        <ul className="mt-1 list-disc pl-4">{deps.map((d, i) => <li key={d.id ?? i}>{d.name ?? t('list.hiddenWorkflow')}{d.id && <span className="ml-1 font-mono text-xs">{d.id}</span>}</li>)}</ul></AlertDescription></Alert> : null,
      onConfirm: async () => { await api(`/api/workflows/${w.id}${deps.length ? '?force=true' : ''}`, { method: 'DELETE' }); onDeleted() } })
  }
  return { ask, dialog: confirmDel.dialog }
}
