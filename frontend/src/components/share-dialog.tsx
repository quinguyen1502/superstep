/** Share a workflow (TASK-0014): owner or admin adds users by email as viewer (open, run) or editor (also edit). */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Share2, Trash2, UserPlus, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { useOpenState } from '@/lib/use-open-state'
import { api } from '@/lib/api'
import type { Issue, Shares, Teams } from '@/lib/rbac'
import { TransferDialog } from '@/components/transfer-dialog'
import { useLoadWhen } from '@/lib/use-when'

export function ShareDialog(props: { workflowId: string; disabled?: boolean; onTransferred?: (owner: string, flagged: Issue[]) => void; open?: boolean; onOpenChange?: (v: boolean) => void }) {
  const { workflowId, disabled, onTransferred } = props
  const { t } = useTranslation()
  const [open, setOpen, controlled] = useOpenState(props.open, props.onOpenChange); const [data, setData] = useState<Shares | null>(null)
  const [email, setEmail] = useState(''); const [role, setRole] = useState<'viewer' | 'editor'>('viewer')
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const [kind, setKind] = useState<'user' | 'team'>('user'); const [teams, setTeams] = useState<Teams['teams']>([]); const [team, setTeam] = useState('')
  const load = () => api<Shares>(`/api/workflows/${workflowId}/shares`).then(setData).catch(e => setErr(e.message))
  useLoadWhen(open, () => { setErr(''); load(); api<Teams>('/api/teams').then(d => setTeams(d.teams)).catch(() => {}) }, workflowId)
  const run = async (f: () => Promise<any>) => { setBusy(true); setErr(''); try { await f() } catch (e: any) { setErr(e.message) } finally { setBusy(false) } }
  const add = () => run(async () => { setData(await api(`/api/workflows/${workflowId}/shares`, { method: 'PUT', json: { email: email.trim(), role } })); setEmail('') })
  const change = (em: string, r: string) => run(async () => setData(await api(`/api/workflows/${workflowId}/shares`, { method: 'PUT', json: { email: em, role: r } })))
  const addTeam = () => run(async () => { setData(await api(`/api/workflows/${workflowId}/team-shares`, { method: 'PUT', json: { team_id: team, role } })); setTeam('') })
  const changeTeam = (tid: string, r: string) => run(async () => setData(await api(`/api/workflows/${workflowId}/team-shares`, { method: 'PUT', json: { team_id: tid, role: r } })))
  const confirmDel = useConfirmDelete()
  const removeTeam = (tid: string, name: string) => confirmDel.ask({ title: t('share.removeTeamTitle', { name }), name, description: t('share.removeBody'), confirmLabel: t('confirmDelete.remove'),
    onConfirm: async () => { await api(`/api/workflows/${workflowId}/team-shares/${tid}`, { method: 'DELETE' }); await load() } })
  const remove = (uid: string, email: string) => confirmDel.ask({ title: t('share.removeTitle', { name: email }), name: email, description: t('share.removeBody'), confirmLabel: t('confirmDelete.remove'),
    onConfirm: async () => { await api(`/api/workflows/${workflowId}/shares/${uid}`, { method: 'DELETE' }); await load() } })
  return <Dialog open={open} onOpenChange={setOpen}>
    {!controlled && <DialogTrigger asChild><Button variant="outline" size="sm" id="share-btn" disabled={disabled}><Share2 />{t('share.button')}</Button></DialogTrigger>}
    <DialogContent className="sm:max-w-lg">
      <DialogHeader><DialogTitle>{t('share.title')}</DialogTitle><DialogDescription>{t('share.intro')}</DialogDescription></DialogHeader>
      {data?.can_share && <div className="grid grid-cols-2 items-end gap-3 sm:grid-cols-[7rem_minmax(0,1fr)_7rem_auto]">
        <div className="space-y-1.5"><Label htmlFor="share-kind">{t('share.with')}</Label>
        <Select value={kind} onValueChange={v => setKind(v as 'user' | 'team')}><SelectTrigger className="w-full" id="share-kind"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="user">{t('share.kindUser')}</SelectItem><SelectItem value="team">{t('share.kindTeam')}</SelectItem></SelectContent></Select></div>
        {kind === 'user' ? <div className="min-w-0 space-y-1.5"><Label htmlFor="share-email">{t('share.email')}</Label>
          <Input id="share-email" type="email" placeholder="name@example.com" value={email} onChange={e => setEmail(e.target.value)} onKeyDown={e => e.key === 'Enter' && email.trim() && add()} /></div>
          : <div className="min-w-0 space-y-1.5"><Label htmlFor="share-team">{t('share.team')}</Label>
            <Select value={team} onValueChange={setTeam}><SelectTrigger id="share-team" className="w-full"><SelectValue placeholder={teams.length ? t('share.pickTeam') : t('share.noTeams')} /></SelectTrigger>
              <SelectContent>{teams.map(tm => <SelectItem key={tm.id} value={tm.id}>{tm.name} ({tm.members})</SelectItem>)}</SelectContent></Select></div>}
        <div className="space-y-1.5"><Label htmlFor="share-role">{t('share.role')}</Label>
        <Select value={role} onValueChange={v => setRole(v as 'viewer' | 'editor')}><SelectTrigger className="w-full" id="share-role"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="viewer">{t('share.roles.viewer')}</SelectItem><SelectItem value="editor">{t('share.roles.editor')}</SelectItem></SelectContent></Select></div>
        <Button id="share-add" onClick={kind === 'user' ? add : addTeam} disabled={(kind === 'user' ? !email.trim() : !team) || busy}>{busy ? <Loader2 className="animate-spin" /> : <UserPlus />}{t('share.add')}</Button>
      </div>}
      {err && <p role="alert" className="text-sm text-destructive" id="share-error">{err}</p>}
      <ul className="divide-y rounded-md border" id="share-list">
        {data && <li className="flex items-center gap-2 px-3 py-2 text-sm"><span className="flex-1 truncate">{data.owner.email}</span><Badge variant="secondary">{t('share.owner')}</Badge></li>}
        {data?.shares.map(s => <li key={s.user_id} className="flex items-center gap-2 px-3 py-2 text-sm share-row">
          <span className="flex-1 truncate">{s.email}</span>
          {data.can_share ? <>
            <Select value={s.role} onValueChange={v => change(s.email, v)}><SelectTrigger size="sm" className="w-28" aria-label={t('share.roleFor', { email: s.email })}><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="viewer">{t('share.roles.viewer')}</SelectItem><SelectItem value="editor">{t('share.roles.editor')}</SelectItem></SelectContent></Select>
            <Button variant="ghost" size="icon" aria-label={t('share.remove', { email: s.email })} onClick={() => remove(s.user_id, s.email)} disabled={busy}><Trash2 /></Button>
          </> : <Badge variant="outline">{t(`share.roles.${s.role}`)}</Badge>}
        </li>)}
        {data?.teams.map(s => <li key={s.team_id} className="flex items-center gap-2 px-3 py-2 text-sm share-team-row">
          <Users className="size-4 text-muted-foreground" /><span className="flex-1 truncate">{s.name}</span><Badge variant="secondary">{t('share.kindTeam')}</Badge>
          {data.can_share ? <>
            <Select value={s.role} onValueChange={v => changeTeam(s.team_id, v)}><SelectTrigger size="sm" className="w-28" aria-label={t('share.roleFor', { email: s.name })}><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="viewer">{t('share.roles.viewer')}</SelectItem><SelectItem value="editor">{t('share.roles.editor')}</SelectItem></SelectContent></Select>
            <Button variant="ghost" size="icon" aria-label={t('share.remove', { email: s.name })} onClick={() => removeTeam(s.team_id, s.name)} disabled={busy}><Trash2 /></Button>
          </> : <Badge variant="outline">{t(`share.roles.${s.role}`)}</Badge>}
        </li>)}
        {data && !data.shares.length && !data.teams.length && <li className="px-3 py-3 text-sm text-muted-foreground" id="share-empty">{t('share.empty')}</li>}
      </ul>
      {data?.can_transfer && <div className="flex items-center justify-between gap-2 border-t pt-3"><p className="text-xs text-muted-foreground">{t('transfer.hint')}</p>
        <TransferDialog workflowId={workflowId} onDone={(o, f) => { setOpen(false); onTransferred?.(o, f) }} /></div>}
    </DialogContent>
    {confirmDel.dialog}
  </Dialog>
}
