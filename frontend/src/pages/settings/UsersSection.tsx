/** Settings → Users (TASK-0014, admins): every account with its role and status, and the roles matrix. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Check, KeyRound, Minus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { CopyField } from '@/components/copy-field'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { can, useMe, type AdminUser, type Policy, type RoleMatrix } from '@/lib/rbac'
import { useOnChange } from '@/lib/use-when'
import { Tip } from '@/components/tip'
import { CodeRuntimeCard } from '@/components/code-runtime-card'

type Data = RoleMatrix & { users: AdminUser[] }

/** Delete or anonymise an account (TASK-0029): owned workflows must go to another editor/admin first. */
function DeleteUserDialog({ user, onClose, onDone }: { user: AdminUser | null; onClose: () => void; onDone: (msg: string) => void }) {
  const { t } = useTranslation(); const [mode, setMode] = useState('anonymize'); const [to, setTo] = useState('')
  useOnChange(user, () => { setMode('anonymize'); setTo('') })
  if (!user) return null
  const go = async () => {
    const r = await api<{ reassigned: string[]; flagged: any[] }>(`/api/admin/users/${user.id}`, { method: 'DELETE', json: { mode, reassign_to: to.trim() || null } })
    onDone(t('users.deleted', { email: user.email, count: r.reassigned.length, flagged: r.flagged.length }))
  }
  return <ConfirmDeleteDialog open onOpenChange={o => !o && onClose()} title={t('users.deleteTitle', { email: user.email })} name={user.email}
    description={t('users.deleteIntro')} confirmLabel={t(`users.modes.${mode}`)} disabled={!!user.workflows && !to.trim()} onConfirm={go}>
    <div className="space-y-3">
      <div className="space-y-1.5"><Label htmlFor="delete-mode">{t('users.deleteMode')}</Label>
        <Select value={mode} onValueChange={setMode}><SelectTrigger id="delete-mode" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="anonymize">{t('users.modes.anonymize')}</SelectItem><SelectItem value="delete">{t('users.modes.delete')}</SelectItem></SelectContent></Select>
        <p className="text-xs text-muted-foreground">{t(`users.modeHelp.${mode}`)}</p></div>
      {!!user.workflows && <div className="space-y-1.5"><Label htmlFor="delete-reassign">{t('users.reassign', { count: user.workflows })}</Label>
        <Input id="delete-reassign" type="email" placeholder="name@example.com" value={to} onChange={e => setTo(e.target.value)} />
        <p className="text-xs text-muted-foreground">{t('users.reassignHelp')}</p></div>}
    </div>
  </ConfirmDeleteDialog>
}

/** A one-time password reset link for another account (TASK-0045). The admin sends it to the user. */
function ResetLinkDialog({ user, onClose }: { user: AdminUser | null; onClose: () => void }) {
  const { t } = useTranslation(); const [link, setLink] = useState<{ path: string; url: string | null; expires_in: number } | null>(null); const [err, setErr] = useState('')
  useOnChange(user, u => { setLink(null); setErr(''); if (u) api<{ path: string; url: string | null; expires_in: number }>(`/api/admin/users/${u.id}/password-reset`, { method: 'POST' }).then(setLink).catch(e => setErr(e.message)) })
  return <Dialog open={!!user} onOpenChange={o => !o && onClose()}><DialogContent id="reset-link-dialog">
    <DialogHeader><DialogTitle>{t('users.resetTitle', { email: user?.email })}</DialogTitle>
      <DialogDescription>{t('users.resetIntro', { minutes: Math.round((link?.expires_in ?? 3600) / 60) })}</DialogDescription></DialogHeader>
    {err ? <p role="alert" className="text-sm text-destructive">{err}</p>
      : link ? <CopyField id="reset-link" label={t('users.resetLink')} value={link.url ?? location.origin + link.path} /> : <Skeleton className="h-9 w-full" />}
  </DialogContent></Dialog>
}

/** Which roles may use org-wide approval channels and MCP servers at run time (TASK-0029). */
function PolicyCard() {
  const { t } = useTranslation(); const [p, setP] = useState<Policy | null>(null); const [err, setErr] = useState('')
  useEffect(() => { api<Policy>('/api/admin/policy').then(setP).catch(e => setErr(e.message)) }, [])
  const toggle = async (role: string, on: boolean) => {
    if (!p) return; setErr('')
    const roles = on ? [...p.org_resources_roles, role] : p.org_resources_roles.filter(r => r !== role)
    try { setP(await api<Policy>('/api/admin/policy', { method: 'PUT', json: { org_resources_roles: roles } })) } catch (e: any) { setErr(e.message) }
  }
  return <Card id="org-policy"><CardHeader><CardTitle>{t('policy.title')}</CardTitle><CardDescription>{t('policy.intro')}</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      {(['admin', 'editor', 'viewer'] as const).map(r => <div key={r} className="flex items-center gap-3 text-sm">
        <Switch id={`policy-${r}`} checked={!!p?.org_resources_roles.includes(r)} disabled={!p || r === 'admin'} onCheckedChange={v => toggle(r, v)} />
        <Label htmlFor={`policy-${r}`} className="font-normal">{t(`users.roles.${r}`)}</Label>
        {r === 'admin' && <span className="text-xs text-muted-foreground">{t('policy.adminAlways')}</span>}</div>)}
      {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
    </CardContent></Card>
}

type LangSmith = { configured: boolean; tracing: boolean; evals: boolean; project: string; endpoint: string | null }

/** Send finished workflow test suites to LangSmith as experiments (needs LANGSMITH_API_KEY on the server). */
function LangSmithCard() {
  const { t } = useTranslation(); const [s, setS] = useState<LangSmith | null>(null); const [err, setErr] = useState('')
  useEffect(() => { api<LangSmith>('/api/admin/langsmith').then(setS).catch(e => setErr(e.message)) }, [])
  const toggle = async (on: boolean) => {
    setErr(''); try { setS(await api<LangSmith>('/api/admin/langsmith', { method: 'PUT', json: { evals: on } })) } catch (e: any) { setErr(e.message) }
  }
  return <Card id="langsmith-settings"><CardHeader><CardTitle>{t('langsmith.title')}</CardTitle><CardDescription>{t('langsmith.intro')}</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <div className="flex items-center gap-3 text-sm">
        <Switch id="langsmith-evals" checked={!!s?.evals} disabled={!s?.configured} onCheckedChange={toggle} />
        <Label htmlFor="langsmith-evals" className="font-normal">{t('langsmith.evals')}</Label></div>
      {s && !s.configured && <p className="text-xs text-muted-foreground" id="langsmith-not-configured">{t('langsmith.notConfigured')}</p>}
      {s?.configured && <p className="text-xs text-muted-foreground">{t(s.tracing ? 'langsmith.tracingOn' : 'langsmith.tracingOff', { project: s.project })}</p>}
      {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
    </CardContent></Card>
}

export function UsersSection() {
  const { t } = useTranslation(); const me = useMe()
  const [data, setData] = useState<Data | null>(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState<string | null>(null)
  const [del, setDel] = useState<AdminUser | null>(null); const [notice, setNotice] = useState(''); const [reset, setReset] = useState<AdminUser | null>(null)
  const load = () => api<Data>('/api/admin/users').then(d => { setData(d); setErr('') }).catch(e => setErr(e.message))
  useEffect(() => { if (can(me, 'users.manage')) load() }, [me])
  const patch = async (u: AdminUser, json: Partial<AdminUser>) => {
    setBusy(u.id); setErr('')
    try { const n = await api<AdminUser>(`/api/admin/users/${u.id}`, { method: 'PATCH', json }); setData(d => d && { ...d, users: d.users.map(x => x.id === n.id ? { ...x, ...n } : x) }) }
    catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }
  if (me && !can(me, 'users.manage')) return <Alert variant="warning" id="users-forbidden"><AlertCircle /><AlertDescription>{t('users.adminOnly')}</AlertDescription></Alert>
  if (!data) return err ? <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>
    : <div className="space-y-2" aria-busy="true"><span className="sr-only">{t('common.loading')}</span>{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
  return <div className="space-y-4">
    {notice && <Alert id="users-notice"><Check /><AlertDescription>{notice}</AlertDescription></Alert>}
    {err && <Alert variant="destructive" id="users-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
    <Card className="overflow-hidden p-0"><Table id="users-table">
      <TableHeader><TableRow><TableHead className="pl-4">{t('users.email')}</TableHead><TableHead>{t('users.role')}</TableHead><TableHead>{t('users.workflows')}</TableHead>
        <TableHead>{t('users.created')}</TableHead><TableHead>{t('users.active')}</TableHead><TableHead className="w-24 pr-4" /></TableRow></TableHeader>
      <TableBody>{data.users.map(u => { const self = u.id === me?.id
        return <TableRow key={u.id} className="user-row" data-email={u.email}>
          <TableCell className="pl-4 font-medium"><div className="flex items-center gap-2">{u.email}{self && <Badge variant="secondary">{t('users.you')}</Badge>}</div></TableCell>
          <TableCell><Select value={u.role} disabled={self || busy === u.id} onValueChange={v => patch(u, { role: v as AdminUser['role'] })}>
            <SelectTrigger size="sm" className="w-32" aria-label={t('users.roleFor', { email: u.email })}><SelectValue /></SelectTrigger>
            <SelectContent>{data.roles.map(r => <SelectItem key={r.role} value={r.role}>{t(`users.roles.${r.role}`)}</SelectItem>)}</SelectContent></Select></TableCell>
          <TableCell><Badge variant="secondary">{u.workflows}</Badge></TableCell>
          <TableCell className="text-muted-foreground">{u.created ? fmtDate(u.created) : '—'}</TableCell>
          <TableCell><div className="flex items-center gap-2"><Switch checked={u.active} disabled={self || busy === u.id} aria-label={t('users.activeFor', { email: u.email })} onCheckedChange={v => patch(u, { active: v })} />
            <span className={u.active ? 'text-sm' : 'text-sm text-muted-foreground'}>{t(u.active ? 'users.statusActive' : 'users.statusDisabled')}</span></div></TableCell>
          <TableCell className="pr-4"><div className="flex gap-1">
            <Tip tip={t('users.resetFor', { email: u.email })}><Button variant="ghost" size="icon" disabled={!u.active} aria-label={t('users.resetFor', { email: u.email })} className="user-reset" onClick={() => setReset(u)}><KeyRound /></Button></Tip>
            <Button variant="ghost" size="icon" disabled={self} aria-label={t('users.deleteFor', { email: u.email })} className="user-delete" onClick={() => setDel(u)}><Trash2 /></Button></div></TableCell>
        </TableRow> })}</TableBody></Table></Card>
    <Card id="roles-matrix"><CardHeader><CardTitle>{t('users.matrixTitle')}</CardTitle><CardDescription>{t('users.matrixIntro')}</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <Table><TableHeader><TableRow><TableHead>{t('users.permission')}</TableHead>{data.roles.map(r => <TableHead key={r.role} className="text-center">{t(`users.roles.${r.role}`)}</TableHead>)}</TableRow></TableHeader>
          <TableBody>{data.permissions.map(p => <TableRow key={p}><TableCell><div className="font-medium">{t(`users.perms.${p.replace('.', '_')}`)}</div><div className="font-mono text-xs text-muted-foreground">{p}</div></TableCell>
            {data.roles.map(r => <TableCell key={r.role} className="text-center">{r.permissions.includes(p) ? <Check className="inline size-4 text-primary" aria-label={t('users.yes')} /> : <Minus className="inline size-4 text-muted-foreground" aria-label={t('users.no')} />}</TableCell>)}</TableRow>)}</TableBody></Table>
        <div className="space-y-1"><div className="text-sm font-medium">{t('users.accessTitle')}</div>
          {data.workflow_access.map(a => <div key={a.access} className="flex flex-wrap items-center gap-1.5 text-sm"><span className="w-28 text-muted-foreground">{t(`share.access.${a.access}`)}</span>
            {a.actions.map(x => <Badge key={x} variant="outline">{t(`share.actions.${x}`)}</Badge>)}</div>)}
          <p className="text-xs text-muted-foreground">{t('users.accessNote')}</p></div>
      </CardContent></Card>
    <PolicyCard />
    <LangSmithCard />
    <CodeRuntimeCard />
    <ResetLinkDialog user={reset} onClose={() => setReset(null)} />
    <DeleteUserDialog user={del} onClose={() => setDel(null)} onDone={m => { setDel(null); setNotice(m); load() }} />
  </div>
}
