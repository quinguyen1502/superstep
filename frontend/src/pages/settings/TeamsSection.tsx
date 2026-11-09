/** Settings → Teams: create teams, add or remove members by e-mail. Workflows are shared with a team from the editor. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Loader2, Plus, Trash2, UserPlus, Users } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { type ConfirmDeleteOptions } from '@/components/confirm-delete-dialog'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { can, useMe, type Team, type TeamMember, type Teams } from '@/lib/rbac'

function TeamCard({ team, onChange, onDelete, ask }: { team: Team; onChange: (t: Team) => void; onDelete: () => void; ask: (o: ConfirmDeleteOptions) => void }) {
  const { t } = useTranslation(); const [email, setEmail] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const run = async (f: () => Promise<{ members: TeamMember[] }>) => {
    setBusy(true); setErr('')
    try { const r = await f(); onChange({ ...team, member_list: r.members, members: r.members.length }); setEmail('') } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const removeMember = (m: TeamMember) => ask({ title: t('teams.removeTitle', { email: m.email, team: team.name }), name: m.email, description: t('teams.removeBody'),
    confirmLabel: t('confirmDelete.remove'), onConfirm: async () => {
      const r = await api<{ members: TeamMember[] }>(`/api/teams/${team.id}/members/${m.user_id}`, { method: 'DELETE' })
      onChange({ ...team, member_list: r.members, members: r.members.length }) } })
  return <Card data-testid={`team-card-${team.id}`} className="gap-4">
    <CardHeader><CardTitle className="flex items-center gap-2"><Users className="size-4 text-muted-foreground" />{team.name}<Badge variant="secondary">{t('teams.members', { count: team.members })}</Badge></CardTitle>
      {team.description && <CardDescription>{team.description}</CardDescription>}
      <CardAction><Button variant="ghost" size="icon" aria-label={t('teams.delete', { name: team.name })} onClick={onDelete}><Trash2 /></Button></CardAction></CardHeader>
    <CardContent className="space-y-3">
      <ul className="divide-y rounded-md border">
        {(team.member_list || []).map(m => <li key={m.user_id} className="flex items-center gap-2 px-3 py-2 text-sm team-member">
          <span className="flex-1 truncate">{m.email}</span><Badge variant="outline">{t(`users.roles.${m.role}`)}</Badge>
          {!m.active && <Badge variant="secondary">{t('users.statusDisabled')}</Badge>}
          <Button variant="ghost" size="icon" aria-label={t('teams.removeMember', { email: m.email })} disabled={busy}
            onClick={() => removeMember(m)}><Trash2 /></Button></li>)}
        {!team.member_list?.length && <li className="px-3 py-3 text-sm text-muted-foreground">{t('teams.noMembers')}</li>}
      </ul>
      <div className="flex gap-2"><Input type="email" placeholder="name@example.com" aria-label={t('teams.memberEmail')} value={email} onChange={e => setEmail(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && email.trim() && run(() => api(`/api/teams/${team.id}/members`, { method: 'POST', json: { email: email.trim() } }))} />
        <Button variant="outline" disabled={!email.trim() || busy} onClick={() => run(() => api(`/api/teams/${team.id}/members`, { method: 'POST', json: { email: email.trim() } }))}>
          {busy ? <Loader2 className="animate-spin" /> : <UserPlus />}{t('teams.addMember')}</Button></div>
      {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
    </CardContent></Card>
}

export function TeamsSection() {
  const { t } = useTranslation(); const me = useMe()
  const [data, setData] = useState<Teams | null>(null); const [name, setName] = useState(''); const [err, setErr] = useState('')
  const confirmDel = useConfirmDelete()
  useEffect(() => { api<Teams>('/api/teams').then(setData).catch(e => setErr(e.message)) }, [])
  if (me && !can(me, 'users.manage')) return <Alert variant="warning"><AlertCircle /><AlertDescription>{t('users.adminOnly')}</AlertDescription></Alert>
  const create = async () => {
    setErr('')
    try { const tm = await api<Team>('/api/teams', { method: 'POST', json: { name } }); setData(d => d && { ...d, teams: [...d.teams, tm].sort((a, b) => a.name.localeCompare(b.name)) }); setName('') }
    catch (e: any) { setErr(e.message) }
  }
  const del = (tm: Team) => confirmDel.ask({ title: t('teams.deleteTitle', { name: tm.name }), name: tm.name, description: t('teams.deleteBody'),
    onConfirm: async () => {
      await api(`/api/teams/${tm.id}`, { method: 'DELETE' })
      setData(d => d && { ...d, teams: d.teams.filter(x => x.id !== tm.id) }) } })
  return <div className="space-y-4">
    <div className="flex gap-2"><Input id="team-new-name" placeholder={t('teams.namePlaceholder')} aria-label={t('teams.name')} value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && name.trim() && create()} className="max-w-sm" />
      <Button id="team-create" onClick={create} disabled={!name.trim()}><Plus />{t('teams.create')}</Button></div>
    {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
    {!data ? <div className="grid gap-4 lg:grid-cols-2" aria-busy="true"><span className="sr-only">{t('common.loading')}</span>{Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-36 w-full" />)}</div>
      : !data.teams.length ? <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground" id="teams-empty">{t('teams.empty')}</div>
      : <div className="grid gap-4 lg:grid-cols-2">{data.teams.map(tm => <TeamCard key={tm.id} team={tm} onDelete={() => del(tm)} ask={confirmDel.ask}
          onChange={n => setData(d => d && { ...d, teams: d.teams.map(x => x.id === n.id ? n : x) })} />)}</div>}
    {confirmDel.dialog}
  </div>
}
