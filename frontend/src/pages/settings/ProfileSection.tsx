/** My profile (TASK-0052): the account, language and notifications, and a password change that signs out
 *  every other session of the account (this browser gets a fresh one). */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CircleCheck, Loader2, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { NotificationSettingsDialog } from '@/components/notification-settings-dialog'
import { PasswordRules } from '@/components/password-rules'
import { api, scheduleExpiry, setSession } from '@/lib/api'
import { fmtDate, LANGS } from '@/lib/i18n'
import { setLanguage } from '@/lib/language'
import { passwordOk } from '@/lib/password'
import { useMe } from '@/lib/rbac'

function Row({ label, hint, children }: { label: React.ReactNode; hint?: string; children: React.ReactNode }) {
  return <div className="flex flex-col gap-2 border-b py-3 last:border-0 sm:flex-row sm:items-center sm:justify-between">
    <div className="space-y-0.5">{label}{hint && <p className="text-xs text-muted-foreground">{hint}</p>}</div>
    <div className="shrink-0">{children}</div>
  </div>
}

function AccountCard() {
  const { t, i18n } = useTranslation(); const me = useMe(); const [notify, setNotify] = useState(false)
  return <Card id="profile-account"><CardHeader><CardTitle>{t('profile.account')}</CardTitle></CardHeader>
    <CardContent /* ui-class-ok: content-only card row; the Card already pads vertically */ className="py-0">
      <Row label={<p className="text-sm font-medium">{t('auth.email')}</p>} hint={t('profile.emailHint')}><span className="text-sm" id="profile-email">{me?.email}</span></Row>
      <Row label={<p className="text-sm font-medium">{t('profile.role')}</p>}>{me && <Badge variant="secondary" id="profile-role">{t(`users.roles.${me.role}`)}</Badge>}</Row>
      <Row label={<p className="text-sm font-medium">{t('users.created')}</p>}><span className="text-sm text-muted-foreground" id="profile-created">{me?.created ? fmtDate(me.created) : '—'}</span></Row>
      <Row label={<Label htmlFor="profile-lang">{t('common.language')}</Label>} hint={t('profile.languageHint')}>
        <Select value={i18n.resolvedLanguage} onValueChange={setLanguage}>
          <SelectTrigger className="w-40" id="profile-lang"><SelectValue /></SelectTrigger>
          <SelectContent>{LANGS.map(l => <SelectItem key={l} value={l}>{t(`lang.${l}`)}</SelectItem>)}</SelectContent></Select>
      </Row>
      <Row label={<p className="text-sm font-medium">{t('notifyPrefs.title')}</p>} hint={t('notifyPrefs.description')}>
        <Button variant="outline" size="sm" id="profile-notify" onClick={() => setNotify(true)}>{t('profile.manage')}</Button>
      </Row>
    </CardContent>
    <NotificationSettingsDialog open={notify} onOpenChange={setNotify} />
  </Card>
}

function PasswordCard() {
  const { t } = useTranslation(); const readOnly = !!useMe()?.read_only  // the demo visitor: the API refuses the change
  const [current, setCurrent] = useState(''); const [password, setPassword] = useState(''); const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [done, setDone] = useState(false)
  const mismatch = confirm.length > 0 && password !== confirm
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setDone(false); setBusy(true)
    try {
      setSession(await api('/api/me/password', { method: 'POST', json: { current_password: current, new_password: password } })); scheduleExpiry()
      setCurrent(''); setPassword(''); setConfirm(''); setDone(true)
    } catch (err: any) { setError(err.message) } finally { setBusy(false) }
  }
  return <Card id="profile-password"><CardHeader><CardTitle>{t('profile.passwordTitle')}</CardTitle><CardDescription>{t('profile.passwordIntro')}</CardDescription></CardHeader>
    <CardContent>
      {readOnly && <Alert variant="warning" id="password-read-only" className="mb-4 max-w-sm"><ShieldAlert /><AlertDescription>{t('demo.readOnly')}</AlertDescription></Alert>}
      <form onSubmit={submit} noValidate aria-busy={busy} className="max-w-sm"><fieldset disabled={readOnly} className="min-w-0 space-y-4">
        {done && <div id="password-changed" role="status" className="flex items-start gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><CircleCheck className="mt-0.5 size-4 shrink-0 text-success" />{t('profile.passwordChanged')}</div>}
        {error && <Alert variant="destructive" id="password-error"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="space-y-1.5"><Label htmlFor="current-password">{t('profile.currentPassword')}</Label>
          <Input id="current-password" type="password" autoComplete="current-password" required disabled={busy} value={current} onChange={e => setCurrent(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="new-password">{t('reset.newPassword')}</Label>
          <Input id="new-password" type="password" autoComplete="new-password" required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} aria-describedby="new-pw-rules" />
          <PasswordRules id="new-pw-rules" password={password} /></div>
        <div className="space-y-1.5"><Label htmlFor="new-confirm">{t('auth.confirm')}</Label>
          <Input id="new-confirm" type="password" autoComplete="new-password" required disabled={busy} value={confirm} onChange={e => setConfirm(e.target.value)} aria-invalid={mismatch} />
          {mismatch && <p className="text-xs text-destructive">{t('auth.mismatch')}</p>}</div>
        <Button type="submit" id="password-save" disabled={busy || !current || !passwordOk(password) || password !== confirm}>{busy && <Loader2 className="animate-spin" />}{t('reset.save')}</Button>
      </fieldset></form>
    </CardContent>
  </Card>
}

export function ProfileSection() {
  return <div className="space-y-4"><AccountCard /><PasswordCard /></div>
}
