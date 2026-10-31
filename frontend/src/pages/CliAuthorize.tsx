/** Browser approval for `superstep login` (TASK-0167). Nothing is sent until Approve or Deny is pressed. The person
 * types the code their own terminal shows; a code in the link is ignored, so a link someone else sent cannot be
 * approved with one click (TASK-0205, DEC-0076). */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CircleCheck, Loader2, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { useMe } from '@/lib/rbac'

export function CliAuthorizePage() {
  const { t } = useTranslation(); const me = useMe()
  const [code, setCode] = useState('')
  const [name, setName] = useState('CLI')
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [done, setDone] = useState<'approved' | 'denied' | ''>('')
  const typed = code.trim()
  const send = async (path: '/api/auth/cli/devices/approve' | '/api/auth/cli/devices/deny') => {
    setError(''); setBusy(true)
    try {
      await api(path, { method: 'POST', json: { user_code: typed, name: name.trim() } })
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
        {done && <Alert id="cli-done"><CircleCheck className="text-success" /><AlertDescription>{t(done === 'approved' ? 'cliAuth.approved' : 'cliAuth.denied')}</AlertDescription></Alert>}
        {error && <Alert variant="destructive" id="cli-error"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        {!done && <>
          <Alert id="cli-warning"><ShieldAlert /><AlertDescription>{t('cliAuth.warning')}</AlertDescription></Alert>
          <div className="space-y-1.5"><Label htmlFor="cli-code">{t('cliAuth.code')}</Label>
            <Input id="cli-code" className="font-mono" value={code} maxLength={32} autoComplete="off" spellCheck={false} disabled={busy}
              aria-describedby="cli-code-hint" onChange={e => setCode(e.target.value)} />
            <p id="cli-code-hint" className="text-sm text-muted-foreground">{t('cliAuth.codeHint')}</p></div>
          <div className="space-y-1.5"><Label htmlFor="cli-name">{t('cliAuth.name')}</Label>
            <Input id="cli-name" value={name} maxLength={80} disabled={busy} onChange={e => setName(e.target.value)} /></div>
          <div className="flex gap-2">
            <Button id="cli-approve" disabled={busy || !typed || !name.trim()} onClick={() => send('/api/auth/cli/devices/approve')}>{busy && <Loader2 className="animate-spin" />}{t('cliAuth.approve')}</Button>
            <Button id="cli-deny" variant="outline" disabled={busy || !typed} onClick={() => send('/api/auth/cli/devices/deny')}>{t('cliAuth.deny')}</Button>
          </div>
        </>}
      </CardContent>
    </Card>
  </main>
}
