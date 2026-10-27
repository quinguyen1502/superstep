/** MCP servers (TASK-0013): register stdio / Streamable HTTP servers, secrets (write-only), discover their tools.
 *  Org servers are managed by admins and usable by everyone; stdio needs STUDIO_MCP_STDIO=1 and an admin. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Building2, ChevronDown, KeyRound, Plug, Plus, RefreshCw, ShieldAlert, Trash2, User, Wrench, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { ErrorAlert } from '@/components/approvals/channel-parts'
import { useAction } from '@/components/approvals/use-action'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { can, useMe } from '@/lib/rbac'
import i18n from '@/lib/i18n'
import type { McpList, McpServer } from '@/lib/mcp'
import { cn } from '@/lib/utils'
import { useOnChange } from '@/lib/use-when'

type Secret = { name: string; value: string; stored: boolean }
type Form = { name: string; transport: 'stdio' | 'http'; scope: 'user' | 'org'; command: string; args: string; url: string; secrets: Secret[] }
const toForm = (s?: McpServer): Form => ({ name: s?.name || '', transport: s?.transport || 'http', scope: s?.scope || 'user', command: s?.command || '',
  args: (s?.args || []).join('\n'), url: s?.url || '', secrets: Object.keys(s?.secrets || {}).map(name => ({ name, value: '', stored: true })) })
/** Request body: an empty value of a stored secret means "keep it" (null). */
const toBody = (f: Form) => ({ name: f.name, transport: f.transport, scope: f.scope, command: f.command || null, url: f.url || null,
  args: f.args.split('\n').map(a => a.trim()).filter(Boolean),
  secrets: Object.fromEntries(f.secrets.filter(s => s.name.trim()).map(s => [s.name.trim(), s.stored && !s.value ? null : s.value])) })

function ServerFields({ form, set, idp, fixed, data }: { form: Form; set: (f: Form) => void; idp: string; fixed: boolean; data: McpList }) {
  const { t } = useTranslation()
  const sec = (i: number, p: Partial<Secret>) => set({ ...form, secrets: form.secrets.map((s, j) => j === i ? { ...s, ...p } : s) })
  return <div className="space-y-3">
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-1.5"><Label htmlFor={`${idp}-name`}>{t('mcp.name')}</Label><Input id={`${idp}-name`} value={form.name} onChange={e => set({ ...form, name: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor={`${idp}-transport`}>{t('mcp.transport')}</Label>
        <Select value={form.transport} disabled={fixed} onValueChange={v => set({ ...form, transport: v as Form['transport'] })}>
          <SelectTrigger className="w-full" id={`${idp}-transport`}><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="http">{t('mcp.http')}</SelectItem>
            <SelectItem value="stdio" disabled={!data.stdio_enabled || !data.is_admin}>{t('mcp.stdio')}</SelectItem></SelectContent></Select></div>
      <div className="space-y-1.5"><Label htmlFor={`${idp}-scope`}>{t('mcp.scope')}</Label>
        <Select value={form.scope} disabled={fixed || !data.is_admin} onValueChange={v => set({ ...form, scope: v as Form['scope'] })}>
          <SelectTrigger className="w-full" id={`${idp}-scope`}><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="user">{t('approvals.scope.user')}</SelectItem><SelectItem value="org">{t('approvals.scope.org')}</SelectItem></SelectContent></Select></div>
    </div>
    {form.transport === 'http'
      ? <div className="space-y-1.5"><Label htmlFor={`${idp}-url`}>{t('mcp.url')}</Label><Input id={`${idp}-url`} className="font-mono text-xs" placeholder="https://mcp.example.com/mcp" value={form.url} onChange={e => set({ ...form, url: e.target.value })} /></div>
      : <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5"><Label htmlFor={`${idp}-command`}>{t('mcp.command')}</Label><Input id={`${idp}-command`} className="font-mono text-xs" placeholder="npx" value={form.command} onChange={e => set({ ...form, command: e.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor={`${idp}-args`}>{t('mcp.args')}</Label>
          <Textarea id={`${idp}-args`} rows={2} className="min-h-9 font-mono text-xs" placeholder={t('mcp.argsHint')} value={form.args} onChange={e => set({ ...form, args: e.target.value })} /></div>
      </div>}
    <div className="space-y-2">
      <Label>{t(form.transport === 'http' ? 'mcp.headers' : 'mcp.env')}</Label>
      {form.secrets.map((s, i) => <div key={i} className="flex gap-2" data-testid="mcp-secret">
        <Input aria-label={t('mcp.secretName')} className="w-48 font-mono text-xs" value={s.name} disabled={s.stored} onChange={e => sec(i, { name: e.target.value })} placeholder={form.transport === 'http' ? 'Authorization' : 'API_TOKEN'} />
        <Input aria-label={t('mcp.secretValue')} type="password" autoComplete="new-password" className="font-mono text-xs" value={s.value} onChange={e => sec(i, { value: e.target.value })}
          placeholder={s.stored ? t('mcp.keepSecret') : t('mcp.secretValue')} />
        <Button variant="ghost" size="icon" aria-label={t('mcp.removeSecret')} onClick={() => set({ ...form, secrets: form.secrets.filter((_, j) => j !== i) })}><X /></Button>
      </div>)}
      <Button variant="outline" size="sm" onClick={() => set({ ...form, secrets: [...form.secrets, { name: '', value: '', stored: false }] })} id={`${idp}-add-secret`}><KeyRound />{t('mcp.addSecret')}</Button>
      <p className="text-xs text-muted-foreground">{t('mcp.secretHelp')}</p>
    </div>
  </div>
}

function ServerCard({ s, data, reload, defaultOpen }: { s: McpServer; data: McpList; reload: () => void; defaultOpen: boolean }) {
  const { t } = useTranslation(); const [open, setOpen] = useState(defaultOpen); const [edit, setEdit] = useState(false); const [form, setForm] = useState(toForm(s))
  const act = useAction(reload); const confirmDel = useConfirmDelete()
  useOnChange(s, v => setForm(toForm(v)))
  return <Collapsible open={open} onOpenChange={setOpen} asChild>
    <Card data-testid={`mcp-card-${s.id}`} className="gap-4">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2"><Plug className="size-4 text-node-mcp" />{s.name}
          <Badge variant="outline" className="font-mono">{s.transport}</Badge>
          <Badge variant="secondary">{s.scope === 'org' ? <Building2 /> : <User />}{t(`approvals.scope.${s.scope}`)}</Badge>
          <Badge variant={s.tools.length ? 'default' : 'outline'} data-testid="mcp-tool-count"><Wrench />{t('mcp.tools', { count: s.tools.length })}</Badge>
        </CardTitle>
        <CardDescription className="font-mono text-xs break-all">{s.transport === 'http' ? s.url : [s.command, ...s.args].join(' ')}</CardDescription>
        <CardAction><CollapsibleTrigger asChild><Button variant="ghost" size="icon" aria-label={t('settings.toggle')} id={`mcp-${s.id}-toggle`}>
          <ChevronDown className={cn('transition-transform', open && 'rotate-180')} /></Button></CollapsibleTrigger></CardAction>
      </CardHeader>
      <CollapsibleContent>
        <CardContent className="space-y-4">
          {act.alerts}
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" disabled={act.busy} id={`mcp-${s.id}-discover`} onClick={() => act.run(() => api<McpServer>(`/api/mcp/servers/${s.id}/discover`, { method: 'POST' }), r => t('mcp.discovered', { count: r.tools.length }))}><RefreshCw />{t('mcp.discover')}</Button>
            <span className="text-xs text-muted-foreground">{s.tools_at ? t('mcp.discoveredAt', { at: new Date(s.tools_at * 1000).toLocaleString(i18n.resolvedLanguage) }) : t('mcp.notDiscovered')}</span>
            {Object.keys(s.secrets).length > 0 && <span className="flex flex-wrap gap-1">{Object.entries(s.secrets).map(([k, v]) => <Badge key={k} variant="outline" className="font-mono"><KeyRound />{k} {v}</Badge>)}</span>}
            {s.can_edit && <Button size="sm" variant="ghost" className={cn('ml-auto', edit && 'bg-accent text-accent-foreground')} aria-expanded={edit} onClick={() => setEdit(!edit)} id={`mcp-${s.id}-edit`}>{t('mcp.edit')}</Button>}
          </div>
          {s.tools.length > 0 && <ul className="divide-y rounded-md border" data-testid="mcp-tools">{s.tools.map(x => <li key={x.name} className="flex flex-col gap-0.5 px-3 py-2">
            <span className="font-mono text-sm">{x.name}<span className="ml-2 text-xs text-muted-foreground">{Object.keys(x.input_schema?.properties || {}).join(', ')}</span></span>
            {x.description && <span className="text-xs text-muted-foreground">{x.description}</span>}</li>)}</ul>}
          {edit && <><Separator /><div className="space-y-3" data-testid="mcp-edit">
            <ServerFields form={form} set={setForm} idp={`mcp-${s.id}`} fixed data={data} />
            <div className="flex flex-wrap gap-2">
              <Button size="sm" disabled={act.busy} onClick={() => act.run(() => api(`/api/mcp/servers/${s.id}`, { method: 'PUT', json: toBody(form) }), t('mcp.saved'))}>{t('common.save')}</Button>
              <Button size="sm" variant="destructive" className="ml-auto" disabled={act.busy} id={`mcp-${s.id}-delete`}
                onClick={() => confirmDel.ask({ title: t('mcp.deleteTitle', { name: s.name }), name: s.name, description: t('mcp.deleteBody'), onConfirm: () => act.run(() => api(`/api/mcp/servers/${s.id}`, { method: 'DELETE' }), '') })}><Trash2 />{t('mcp.delete')}</Button>
            </div></div></>}
        </CardContent>
      </CollapsibleContent>
      {confirmDel.dialog}
    </Card>
  </Collapsible>
}

export function McpSection() {
  const { t } = useTranslation()
  const [data, setData] = useState<McpList | null>(null); const [err, setErr] = useState(''); const manages = can(useMe(), 'resources.manage')
  const [adding, setAdding] = useState(false); const [form, setForm] = useState(toForm())
  const load = () => api<McpList>('/api/mcp/servers').then(d => { setData(d); setErr('') }).catch(e => setErr(e.message))
  const create = useAction(() => { setAdding(false); setForm(toForm()); load() })
  useEffect(() => { load() }, [])
  return <div className="space-y-4">
    {err && <ErrorAlert>{err}</ErrorAlert>}
    {data?.org_usable === false && <Alert variant="warning" id="mcp-org-blocked"><ShieldAlert /><AlertDescription>{t('policy.blockedMcp')}</AlertDescription></Alert>}
    {data && <Alert variant="warning" id="mcp-sandbox-note"><ShieldAlert /><AlertDescription>{t(data.stdio_enabled ? 'mcp.stdioOn' : 'mcp.stdioOff')}</AlertDescription></Alert>}
    {data && manages && (adding ? <Card className="gap-4" id="mcp-new"><CardHeader><CardTitle>{t('mcp.new')}</CardTitle><CardDescription>{t('mcp.newHelp')}</CardDescription></CardHeader>
      <CardContent className="space-y-3">{create.alerts}
        <ServerFields form={form} set={setForm} idp="mcp-new" fixed={false} data={data} />
        <div className="flex gap-2"><Button size="sm" disabled={create.busy} id="mcp-create" onClick={() => create.run(() => api('/api/mcp/servers', { method: 'POST', json: toBody(form) }), '')}>{t('mcp.create')}</Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>{t('common.cancel')}</Button></div></CardContent></Card>
      : <Button size="sm" onClick={() => setAdding(true)} id="mcp-add"><Plus />{t('mcp.new')}</Button>)}
    {!data && !err && <div className="space-y-3" aria-busy="true"><span className="sr-only">{t('common.loading')}</span>{Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>}
    {data && !data.servers.length && !adding && <p className="text-sm text-muted-foreground" id="mcp-none">{t('mcp.none')}</p>}
    {data?.servers.map((s, i) => <ServerCard key={s.id} s={s} data={data} reload={load} defaultOpen={i < 2} />)}
  </div>
}
