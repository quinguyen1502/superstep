/** Settings → Access tokens (TASK-0167). The secret is shown once. Revoke asks for the token's name; the DELETE has no confirm field. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, KeyRound, Loader2, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import { useMe } from '@/lib/rbac'

type TokenRow = { id: string; name: string; prefix: string; created: number; last_used: number | null }

export function TokensSection() {
  const { t } = useTranslation(); const me = useMe(); const confirmDel = useConfirmDelete()
  const [items, setItems] = useState<TokenRow[] | null>(null)
  const [name, setName] = useState(''); const [secret, setSecret] = useState('')
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const readOnly = !!me?.read_only
  const load = () => api<{ items: TokenRow[] }>('/api/me/tokens').then(r => setItems(r.items)).catch((e: any) => setError(e.message || ''))
  useEffect(() => { load() }, [])
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      const created = await api<{ token: string }>('/api/me/tokens', { method: 'POST', json: { name: name.trim() } })
      setSecret(created.token); setName(''); await load()
    } catch (err: any) { setError(err.message || '') } finally { setBusy(false) }
  }
  return <div className="space-y-4">
    {confirmDel.dialog}
    {readOnly && <Alert variant="warning" id="token-read-only"><ShieldAlert /><AlertDescription>{t('tokens.readOnly')}</AlertDescription></Alert>}
    <Card id="token-create-card"><CardHeader><CardTitle>{t('tokens.create')}</CardTitle></CardHeader>
      <CardContent>
        {secret && <Alert id="token-secret-once" className="mb-4"><KeyRound /><AlertDescription className="space-y-2">
          <p>{t('tokens.secretOnce')}</p>
          <Input id="token-secret" readOnly value={secret} className="font-mono" />
          <p className="text-muted-foreground">{t('tokens.secretHint')}</p>
        </AlertDescription></Alert>}
        {error && <Alert variant="destructive" id="token-error" className="mb-4"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        <form onSubmit={create} className="flex max-w-md flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1 space-y-1.5"><Label htmlFor="token-name">{t('tokens.name')}</Label>
            <Input id="token-name" value={name} maxLength={80} placeholder={t('tokens.namePh')} disabled={busy || readOnly} onChange={e => setName(e.target.value)} /></div>
          <Button type="submit" id="token-create" disabled={busy || readOnly || !name.trim()}>{busy && <Loader2 className="animate-spin" />}{t('tokens.create')}</Button>
        </form>
      </CardContent>
    </Card>
    <Card id="token-list"><CardHeader><CardTitle>{t('settings.nav.tokens')}</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {items?.length === 0 && <p className="text-sm text-muted-foreground" id="token-empty">{t('tokens.empty')}</p>}
        {items?.map(it => <div key={it.id} id={`token-${it.id}`} className="flex flex-col gap-2 border-b py-3 last:border-0 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium">{it.name}</p>
            <p className="font-mono text-xs text-muted-foreground">{it.prefix}</p>
            <p className="text-xs text-muted-foreground">{t('tokens.created')} {fmtDate(it.created)} · {t('tokens.lastUsed')} {it.last_used ? fmtDate(it.last_used) : t('tokens.never')}</p>
          </div>
          <Button variant="outline" size="sm" id={`token-revoke-${it.id}`} disabled={readOnly} onClick={() => confirmDel.ask({
            title: t('tokens.revokeTitle', { name: it.name }), name: it.name, description: t('tokens.revokeBody'), confirmLabel: t('tokens.revoke'),
            onConfirm: async () => { await api(`/api/me/tokens/${it.id}`, { method: 'DELETE' }); setSecret(''); await load() },
          })}>{t('tokens.revoke')}</Button>
        </div>)}
      </CardContent>
    </Card>
  </div>
}
