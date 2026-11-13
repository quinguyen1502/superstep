import { useCallback, useEffect, useId, useState, type FormEvent } from 'react'
import { Check, Copy, Plus, RotateCw, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { datasetUrl, type Dataset } from '@/lib/datasets'

const permissions = ['read', 'write', 'read_write'] as const
type Permission = (typeof permissions)[number]
type Grant = { workflow_id: string; workflow_name: string | null; permission: Permission; allow_delete: boolean }
type Token = { id: string; name: string; prefix: string; permission: Permission; allow_delete: boolean }
type Access = { grants: Grant[]; tokens: Token[]; workflows: { id: string; name: string | null }[] }

function PermissionPicker({ id, value, onChange, disabled }: {
  id: string; value: Permission; onChange: (value: Permission) => void; disabled: boolean
}) {
  const { t } = useTranslation()
  return <div className="min-w-0 space-y-1">
    <Label htmlFor={id}>{t('dataset.accessPermission')}</Label>
    <Select value={value} onValueChange={value => onChange(value as Permission)} disabled={disabled}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{permissions.map(permission =>
        <SelectItem key={permission} value={permission}>{t(`dataset.accessLevel.${permission}`)}</SelectItem>)}
      </SelectContent>
    </Select>
  </div>
}

export function DatasetAccessDialog({ dataset, scope, onClose }: { dataset: Dataset; scope: string; onClose: () => void }) {
  const { t } = useTranslation()
  const id = useId()
  const confirm = useConfirmDelete()
  const path = `${datasetUrl(dataset.id)}/access`
  const [access, setAccess] = useState<Access | null>(null)
  const [workflowId, setWorkflowId] = useState('')
  const [grantPermission, setGrantPermission] = useState<Permission>('read')
  const [grantAllowDelete, setGrantAllowDelete] = useState(false)
  const [tokenPermission, setTokenPermission] = useState<Permission>('read')
  const [tokenAllowDelete, setTokenAllowDelete] = useState(false)
  const [tokenName, setTokenName] = useState('')
  const [secret, setSecret] = useState('')
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setAccess(await api<Access>(path))
  }, [path])

  useEffect(() => {
    void load().catch(failure => setError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR')))
  }, [load, t])

  async function mutate(action: () => Promise<void>) {
    setBusy(true)
    setError('')
    try {
      await action()
      await load()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : t('errors.INTERNAL_ERROR'))
    } finally {
      setBusy(false)
    }
  }

  function grant(event: FormEvent) {
    event.preventDefault()
    if (!workflowId || busy) return
    void mutate(async () => {
      await api(`${path}/grants/${encodeURIComponent(workflowId)}`, {
        method: 'PUT', json: { permission: grantPermission, allow_delete: grantAllowDelete },
      })
      setWorkflowId('')
    })
  }

  function reveal(token: string) {
    setSecret(token)
    setCopied(false)
  }

  function createToken(event: FormEvent) {
    event.preventDefault()
    if (!tokenName.trim() || busy) return
    void mutate(async () => {
      const data = await api<{ token: string }>(`${path}/tokens`, {
        method: 'POST', json: { name: tokenName, permission: tokenPermission, allow_delete: tokenAllowDelete },
      })
      reveal(data.token)
      setTokenName('')
    })
  }

  function revoke(name: string, endpoint: string) {
    confirm.ask({ name, title: t('dataset.accessRevoke'), description: t('dataset.accessRevokeBody'), onConfirm: async () => {
      await api(`${path}/${endpoint}`, { method: 'DELETE' })
      if (endpoint.startsWith('tokens/')) setSecret('')
      await load()
    } })
  }

  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-2xl">
      <DialogHeader><DialogTitle>{t('dataset.access')}</DialogTitle><DialogDescription>{dataset.name} · {scope}</DialogDescription></DialogHeader>
      <DialogBody className="space-y-5">
        {!access && !error && <p role="status" className="text-sm text-muted-foreground">{t('common.loading')}</p>}
        {access && <>
          <section className="space-y-2">
            <h3 className="font-medium">{t('dataset.workflowGrants')}</h3>
            {!access.grants.length && <p className="text-sm text-muted-foreground">{t('dataset.noWorkflowGrants')}</p>}
            {access.grants.map(item => <div key={item.workflow_id} className="flex items-center justify-between gap-2 rounded-md border p-2">
              <div className="min-w-0">
                <p className="wrap-anywhere font-medium">{item.workflow_name ?? item.workflow_id}</p>
                <p className="text-xs text-muted-foreground">{t(`dataset.accessLevel.${item.permission}`)}{item.allow_delete ? ` · ${t('dataset.accessAllowDelete')}` : ''}</p>
              </div>
              <Button variant="ghost" size="icon-sm" className="text-destructive" aria-label={t('dataset.accessRevoke')} disabled={busy}
                onClick={() => revoke(item.workflow_name ?? item.workflow_id, `grants/${encodeURIComponent(item.workflow_id)}`)}><Trash2 /></Button>
            </div>)}
            <form className="grid items-end gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" onSubmit={grant}>
              <div className="min-w-0 space-y-1"><Label htmlFor={`${id}-workflow`}>{t('dataset.accessWorkflow')}</Label>
                <Select disabled={busy || !access.workflows.length} value={workflowId} onValueChange={value => {
                  setWorkflowId(value)
                  const current = access.grants.find(item => item.workflow_id === value)
                  setGrantPermission(current?.permission ?? 'read')
                  setGrantAllowDelete(current?.allow_delete ?? false)
                }}>
                  <SelectTrigger id={`${id}-workflow`} className="w-full"><SelectValue placeholder={t('dataset.accessChooseWorkflow')} /></SelectTrigger>
                  <SelectContent>{access.workflows.map(item =>
                    <SelectItem key={item.id} value={item.id}>{item.name ?? item.id}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <PermissionPicker id={`${id}-grant-permission`} value={grantPermission} onChange={setGrantPermission} disabled={busy || !workflowId} />
              <Button type="submit" disabled={busy || !workflowId}>{t('dataset.accessSaveGrant')}</Button>
              <Label className="flex items-center gap-2 sm:col-span-3"><Checkbox id={`${id}-grant-delete`} checked={grantAllowDelete}
                disabled={busy || !workflowId} onCheckedChange={value => setGrantAllowDelete(value === true)} />{t('dataset.accessAllowDelete')}</Label>
              {grantPermission === 'write' && <p className="text-xs text-muted-foreground sm:col-span-3">{t('dataset.accessWriteOnly')}</p>}
            </form>
            {!access.workflows.length && <p className="text-xs text-muted-foreground">{t('dataset.accessNoEligibleWorkflow')}</p>}
          </section>
          <section className="space-y-2">
            <h3 className="font-medium">{t('dataset.accessTokens')}</h3>
            {!access.tokens.length && <p className="text-sm text-muted-foreground">{t('dataset.noAccessTokens')}</p>}
            {access.tokens.map(item => <div key={item.id} className="flex items-center justify-between gap-2 rounded-md border p-2">
              <div className="min-w-0">
                <p className="wrap-anywhere font-medium">{item.name}</p>
                <p className="text-xs text-muted-foreground">{item.prefix}… · {t(`dataset.accessLevel.${item.permission}`)}{item.allow_delete ? ` · ${t('dataset.accessAllowDelete')}` : ''}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="icon-sm" aria-label={t('dataset.rotateAccessToken')} disabled={busy}
                  onClick={() => void mutate(async () => {
                    const data = await api<{ token: string }>(`${path}/tokens/${item.id}/rotate`, { method: 'POST' })
                    reveal(data.token)
                  })}><RotateCw /></Button>
                <Button variant="ghost" size="icon-sm" className="text-destructive" aria-label={t('dataset.accessRevoke')} disabled={busy}
                  onClick={() => revoke(item.name, `tokens/${item.id}`)}><Trash2 /></Button>
              </div>
            </div>)}
            <form className="grid items-end gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" onSubmit={createToken}>
              <div className="min-w-0 space-y-1">
                <Label htmlFor={`${id}-token-name`}>{t('dataset.accessTokenName')}</Label>
                <Input id={`${id}-token-name`} value={tokenName} maxLength={80} disabled={busy} required onChange={event => setTokenName(event.target.value)} />
              </div>
              <PermissionPicker id={`${id}-token-permission`} value={tokenPermission} onChange={setTokenPermission} disabled={busy} />
              <Button type="submit" disabled={busy || !tokenName.trim()}><Plus />{t('dataset.createAccessToken')}</Button>
              <Label className="flex items-center gap-2 sm:col-span-3"><Checkbox id={`${id}-token-delete`} checked={tokenAllowDelete}
                disabled={busy} onCheckedChange={value => setTokenAllowDelete(value === true)} />{t('dataset.accessAllowDelete')}</Label>
              {tokenPermission === 'write' && <p className="text-xs text-muted-foreground sm:col-span-3">{t('dataset.accessWriteOnly')}</p>}
            </form>
            {secret && <div className="space-y-2 rounded-md border p-3">
              <Label htmlFor={`${id}-secret`}>{t('dataset.accessTokenSecret')}</Label>
              <p className="text-xs text-muted-foreground">{t('dataset.accessTokenOnce')}</p>
              <div className="flex gap-2">
                <Input id={`${id}-secret`} value={secret} readOnly />
                <Button variant="outline" size="icon" aria-label={t('dataset.copyAccessToken')} onClick={async () => {
                  try { await navigator.clipboard.writeText(secret); setCopied(true) }
                  catch { setError(t('dataset.accessCopyFailed')) }
                }}>{copied ? <Check /> : <Copy />}</Button>
              </div>
            </div>}
          </section>
        </>}
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      </DialogBody>
      <DialogFooter><Button variant="outline" disabled={busy} onClick={onClose}>{t('common.close')}</Button></DialogFooter>
      {confirm.dialog}
    </DialogContent>
  </Dialog>
}
