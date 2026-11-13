import { useEffect, useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { datasetUrl, type Dataset } from '@/lib/datasets'
import type { TeamMember, Teams } from '@/lib/rbac'

/** Admins move a team dataset to another team member who can manage resources. */
export function DatasetOwnerDialog({ dataset, onClose, onSave }: { dataset: Dataset; onClose: () => void; onSave: (dataset: Dataset) => void }) {
  const { t } = useTranslation()
  const id = useId()
  const [members, setMembers] = useState<TeamMember[] | null>(null)
  const [userId, setUserId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api<Teams>('/api/teams').then(data => setMembers(data.teams.find(team => team.id === dataset.team_id)?.member_list ?? []))
      .catch(failure => setError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR')))
  }, [dataset.team_id, t])

  const owner = members?.find(member => member.user_id === dataset.team_owner_id)
  const candidates = (members ?? []).filter(member => member.active && member.role !== 'viewer' && member.user_id !== dataset.team_owner_id)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!userId || busy) return
    setBusy(true)
    setError('')
    try {
      onSave(await api<Dataset>(`${datasetUrl(dataset.id)}/owner`, { method: 'PUT', json: { user_id: userId, revision: dataset.revision } }))
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR'))
    } finally {
      setBusy(false)
    }
  }

  return <Dialog open onOpenChange={open => { if (!open) onClose() }}>
    <DialogContent>
      <form className="contents" onSubmit={submit}>
        <DialogHeader>
          <DialogTitle>{t('dataset.transferOwner')}</DialogTitle>
          <DialogDescription>{t('dataset.transferOwnerDescription')}</DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-3">
          <p className="text-sm">{dataset.team_owner_id
            ? t('dataset.currentOwner', { email: owner?.email ?? dataset.team_owner_id })
            : t('dataset.noOwner')}</p>
          {members && !candidates.length && <p className="text-sm text-muted-foreground">{t('dataset.noTransferCandidates')}</p>}
          {!!candidates.length && <div className="space-y-1.5">
            <Label htmlFor={`${id}-owner`}>{t('dataset.newOwner')}</Label>
            <Select value={userId} onValueChange={setUserId} disabled={busy}>
              <SelectTrigger id={`${id}-owner`} className="w-full"><SelectValue placeholder={t('dataset.newOwner')} /></SelectTrigger>
              <SelectContent>{candidates.map(member => <SelectItem key={member.user_id} value={member.user_id}>{member.email}</SelectItem>)}</SelectContent>
            </Select>
          </div>}
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        </DialogBody>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={onClose}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={!userId || busy}>{t('dataset.transfer')}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
