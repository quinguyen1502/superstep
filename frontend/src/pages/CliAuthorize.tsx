/** Browser approval for `superstep login` (TASK-0167). Nothing is sent until Approve or Deny is pressed. */
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CircleCheck, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { useMe } from '@/lib/rbac'

export function CliAuthorizePage() {
  const { t } = useTranslation(); const me = useMe(); const [params] = useSearchParams()
  const code = params.get('code') || ''
  const [name, setName] = useState('CLI')
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [done, setDone] = useState<'approved' | 'denied' | ''>('')
  const send = async (path: '/api/auth/cli/devices/approve' | '/api/auth/cli/devices/deny') => {
    setError(''); setBusy(true)
    try {
      await api(path, { method: 'POST', json: { user_code: code, name: name.trim() } })
      setDone(path.endsWith('approve') ? 'approved' : 'denied')
    } catch (err: any) { setError(err.message || '') } finally { setBusy(false) }
  }
  return <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center p-4">
    <Card id="cli-authorize">
      <CardHeader>
        <CardTitle>{t('cliAuth.title')}</CardTitle>
        <CardDescription>{t('cliAuth.intro')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {me?.email && <p className="text-sm" id="cli-account">{me.email}</p>}
        {!code && <Alert variant="destructive" id="cli-missing"><AlertCircle /><AlertDescription>{t('cliAuth.missing')}</AlertDescription></Alert>}
        {done && <Alert id="cli-done"><CircleCheck className="text-success" /><AlertDescription>{t(done === 'approved' ? 'cliAuth.approved' : 'cliAuth.denied')}</AlertDescription></Alert>}
        {error && <Alert variant="destructive" id="cli-error"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        {code && !done && <>
          <div className="space-y-1.5"><Label>{t('cliAuth.code')}</Label><p className="font-mono text-lg" id="cli-code">{code}</p></div>
          <div className="space-y-1.5"><Label htmlFor="cli-name">{t('cliAuth.name')}</Label>
            <Input id="cli-name" value={name} maxLength={80} disabled={busy} onChange={e => setName(e.target.value)} /></div>
          <div className="flex gap-2">
            <Button id="cli-approve" disabled={busy || !name.trim()} onClick={() => send('/api/auth/cli/devices/approve')}>{busy && <Loader2 className="animate-spin" />}{t('cliAuth.approve')}</Button>
            <Button id="cli-deny" variant="outline" disabled={busy} onClick={() => send('/api/auth/cli/devices/deny')}>{t('cliAuth.deny')}</Button>
          </div>
        </>}
      </CardContent>
    </Card>
  </main>
}
