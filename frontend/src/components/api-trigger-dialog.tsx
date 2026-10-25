import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { AlertCircle, Check, Copy, Plus, RefreshCw, Trash2, Webhook } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { DeliveriesList } from '@/components/deliveries-list'
import { McpServerTab } from '@/components/mcp-server-tab'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { useOpenState } from '@/lib/use-open-state'
import { api } from '@/lib/api'
import i18n from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'

type Token = { id: string; name: string; prefix: string; created: number; last_used: number | null; revoked: number | null; token?: string; signing_secret?: string; signed?: boolean; grace_until?: number }
const when = (s: number | null) => s ? new Date(s * 1000).toLocaleString(i18n.resolvedLanguage) : '—'

const Tip = ({ tip, children }: { tip: string; children: React.ReactElement }) => <Tooltip><TooltipTrigger asChild>{children}</TooltipTrigger><TooltipContent>{tip}</TooltipContent></Tooltip>

/** Per-workflow API tokens + how to call the trigger endpoint (TASK-0007). */
export function ApiTriggerDialog(props: { wid?: string; open?: boolean; onOpenChange?: (v: boolean) => void }) {
  const { wid } = props
  const { t } = useTranslation(); const [open, setOpen, controlled] = useOpenState(props.open, props.onOpenChange)
  const [items, setItems] = useState<Token[]>([]); const [name, setName] = useState(''); const [created, setCreated] = useState<Token | null>(null)
  const [err, setErr] = useState(''); const [copied, setCopied] = useState(false); const [showRevoked, setShowRevoked] = useState(false)
  const load = () => wid && api<Token[]>(`/api/workflows/${wid}/tokens`).then(setItems).catch(e => setErr(e.message))
  useLoadWhen(open, () => { setCreated(null); setErr(''); load() })
  const add = async () => {
    setErr('')
    try { const tk = await api<Token>(`/api/workflows/${wid}/tokens`, { method: 'POST', json: { name: name || 'API token' } }); setCreated(tk); setName(''); load() }
    catch (e: any) { setErr(e.message) }
  }
  const rotate = async (id: string) => {
    setErr('')
    try { setCreated(await api<Token>(`/api/workflows/${wid}/tokens/${id}/rotate-secret`, { method: 'POST' })); load() } catch (e: any) { setErr(e.message) }
  }
  const confirmDel = useConfirmDelete()
  const revoke = (tk: Token) => confirmDel.ask({ title: t('api.revokeTitle', { name: tk.name }), name: tk.name, description: t('api.revokeBody'), confirmLabel: t('confirmDelete.revoke'),
    onConfirm: async () => { await api(`/api/workflows/${wid}/tokens/${tk.id}`, { method: 'DELETE' }); load() } })
  const revokedCount = items.filter(tk => tk.revoked).length
  const visible = showRevoked ? items : items.filter(tk => !tk.revoked)
  const url = `${location.origin}/api/hooks/workflows/${wid}/runs`
  const curl = `curl -X POST ${url} \\\n  -H "Authorization: Bearer ${created?.token ?? '<token>'}" -H "Content-Type: application/json" \\\n  -d '{"input": {"message": "hi"}, "mode": "sync"}'`
  const copy = async (s: string) => { try { await navigator.clipboard.writeText(s); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* clipboard blocked */ } }
  return <Dialog open={open} onOpenChange={setOpen}>
    {!controlled && <DialogTrigger asChild><Button size="sm" variant="outline" id="api-btn" disabled={!wid}><Webhook />{t('api.button')}</Button></DialogTrigger>}
    <DialogContent className="sm:max-w-2xl max-h-[90dvh] flex flex-col overflow-hidden" id="api-dialog">
      <DialogHeader className="shrink-0"><DialogTitle>{t('api.title')}</DialogTitle><DialogDescription>{t('api.desc')}</DialogDescription></DialogHeader>
      <Tabs defaultValue="tokens" className="flex min-h-0 flex-1 flex-col">
      <TabsList className="shrink-0"><TabsTrigger value="tokens">{t('api.tokensTab')}</TabsTrigger><TabsTrigger value="deliveries" id="api-deliveries-tab">{t('deliveries.tab')}</TabsTrigger><TabsTrigger value="mcp" id="api-mcp-tab">{t('mcpServer.tab')}</TabsTrigger></TabsList>
      <div className="-mx-1 min-h-0 flex-1 space-y-4 overflow-y-auto px-1" id="api-scroll">
      {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
      {(created?.token || created?.signing_secret) && <Alert id="api-new-token"><Check /><AlertDescription className="space-y-2">
        <span>{t('api.copyOnce')}</span>
        {created.token && <div className="flex gap-2"><Input readOnly id="api-token-value" className="font-mono text-xs" value={created.token} />
          <Button variant="outline" size="icon" aria-label={t('api.copy')} onClick={() => copy(created.token!)}>{copied ? <Check /> : <Copy />}</Button></div>}
        {created.grace_until && <p className="text-xs" id="api-rotated">{t('api.rotated', { when: when(created.grace_until) })}</p>}
        {created.signing_secret && <div className="space-y-1"><Label htmlFor="api-signing-secret" className="text-xs">{t('api.signingSecret')}</Label>
          <div className="flex gap-2"><Input readOnly id="api-signing-secret" className="font-mono text-xs" value={created.signing_secret} />
            <Button variant="outline" size="icon" aria-label={t('api.copy')} onClick={() => copy(created.signing_secret!)}><Copy /></Button></div>
          <p className="text-xs text-muted-foreground">{t('api.signingHelp')}</p></div>}
      </AlertDescription></Alert>}
      <TabsContent value="deliveries" className="pt-2"><DeliveriesList wid={wid} /></TabsContent>
      <TabsContent value="mcp" className="pt-2"><McpServerTab wid={wid} open={open} token={created?.token} hasTokens={items.some(tk => !tk.revoked)} /></TabsContent>
      <TabsContent value="tokens" className="space-y-4 pt-2">
      {revokedCount > 0 && <div className="flex items-center justify-end gap-2">
        <Switch id="api-show-revoked" size="sm" checked={showRevoked} onCheckedChange={setShowRevoked} />
        <Label htmlFor="api-show-revoked" className="text-xs text-muted-foreground">{t('api.showRevoked', { count: revokedCount })}</Label></div>}
      <div className="space-y-2">
        {visible.map(tk => <div key={tk.id} data-testid="api-token-row" className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
          <span className="font-medium">{tk.name}</span><span className="font-mono text-xs text-muted-foreground">{tk.prefix}…</span>
          {tk.revoked ? <Badge variant="secondary">{t('api.revoked')}</Badge> : <Badge variant="success">{t('api.active')}</Badge>}
          <span className="ml-auto text-xs text-muted-foreground">{t('api.lastUsed', { when: when(tk.last_used) })}</span>
          {!tk.revoked && tk.signed && <Tip tip={t('api.rotate')}><Button variant="ghost" size="icon-sm" data-testid="api-rotate" aria-label={t('api.rotateAria', { name: tk.name })} onClick={() => rotate(tk.id)}><RefreshCw /></Button></Tip>}
          {!tk.revoked && <Button variant="ghost" size="icon-sm" aria-label={t('api.revokeAria', { name: tk.name })} onClick={() => revoke(tk)}><Trash2 /></Button>}
        </div>)}
        {!visible.length && <p className="text-xs text-muted-foreground">{t('api.empty')}</p>}
      </div>
      <div className="flex items-end gap-2">
        <div className="flex-1 space-y-1.5"><Label htmlFor="api-token-name" className="text-xs text-muted-foreground">{t('api.name')}</Label>
          <Input id="api-token-name" value={name} placeholder="CI, Zapier…" onChange={e => setName(e.target.value)} /></div>
        <Button id="api-create" onClick={add}><Plus />{t('api.create')}</Button>
      </div>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('api.example')}</Label>
        <pre id="api-curl" className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-[11px] text-muted-foreground whitespace-pre">{curl}</pre>
        <p className="text-xs text-muted-foreground">{t('api.modes')}</p></div>
      </TabsContent></div></Tabs>
    </DialogContent>
    {confirmDel.dialog}
  </Dialog>
}
