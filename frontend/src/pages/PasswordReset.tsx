/** Forgot password and reset password pages (TASK-0045). */
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, CircleCheck, KeyRound, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LanguageSwitcher } from '@/components/language-switcher'
import { ThemeToggle } from '@/components/theme-toggle'
import { PasswordRules } from '@/components/password-rules'
import { passwordOk } from '@/lib/password'
import { api } from '@/lib/api'
import { AppMeta } from '@/components/app-meta'

function Frame({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return <div className="relative flex min-h-dvh flex-col bg-muted/40">
    <div className="absolute top-4 right-4 z-10 flex gap-1"><LanguageSwitcher /><ThemeToggle /></div>
    <div className="flex flex-1 items-center justify-center p-4">
    <Card className="w-full max-w-sm">
      <CardHeader className="text-center">
        <div className="mx-auto mb-2 rounded-lg bg-primary text-primary-foreground p-2 w-fit"><KeyRound className="size-5" /></div>
        <CardTitle className="text-xl">{title}</CardTitle><CardDescription>{hint}</CardDescription>
      </CardHeader>{children}</Card>
    </div>
    <AppMeta />
  </div>
}

/** E-mail a reset link when the server can send mail; otherwise say who can make one. Same answer for every address. */
export function ForgotPasswordPage() {
  const { t } = useTranslation(); const [email, setEmail] = useState<string>(useLocation().state?.email || '')
  const [mode, setMode] = useState<'email' | 'admin' | null>(null); const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  useEffect(() => { api<{ reset: 'email' | 'admin' }>('/api/auth/options').then(o => setMode(o.reset)).catch(() => setMode('admin')) }, [])
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setBusy(true)
    try { await api('/api/auth/password-reset', { method: 'POST', json: { email } }); setSent(true) } catch (err: any) { setError(err.message) } finally { setBusy(false) }
  }
  return <Frame title={t('reset.forgotTitle')} hint={mode === 'admin' ? t('reset.askAdmin') : t('reset.forgotHint')}>
    {mode === 'email' && <form onSubmit={submit} noValidate aria-busy={busy}>
      <CardContent className="space-y-4">
        {sent && <div id="reset-sent" role="status" className="flex items-start gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><CircleCheck className="mt-0.5 size-4 shrink-0 text-success" />{t('reset.sent')}</div>}
        {error && <Alert variant="destructive"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="space-y-1.5"><Label htmlFor="reset-email">{t('auth.email')}</Label>
          <Input id="reset-email" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="email" autoComplete="email" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} /></div>
      </CardContent>
      <CardFooter className="flex-col gap-3 mt-6"><Button type="submit" id="reset-request" size="lg" className="w-full" disabled={busy || !email.trim()}>{busy && <Loader2 className="animate-spin" />}{t('reset.send')}</Button></CardFooter>
    </form>}
    <CardFooter className="justify-center pb-6"><Link to="/login" state={{ email }} className="text-sm underline">{t('reset.back')}</Link></CardFooter>
  </Frame>
}

/** Choose a new password from a one-time link (?token=). Older sessions of the account stop working. */
export function ResetPasswordPage() {
  const { t } = useTranslation(); const nav = useNavigate(); const token = useSearchParams()[0].get('token') || ''
  const [password, setPassword] = useState(''); const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const mismatch = confirm.length > 0 && password !== confirm
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      const r = await api<{ email: string }>('/api/auth/password-reset/confirm', { method: 'POST', json: { token, password } })
      nav('/login?reset=1', { replace: true, state: { email: r.email } })
    } catch (err: any) { setError(err.message) } finally { setBusy(false) }
  }
  return <Frame title={t('reset.newTitle')} hint={t('reset.newHint')}>
    <form onSubmit={submit} noValidate aria-busy={busy}>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive" id="reset-error"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="space-y-1.5"><Label htmlFor="new-password">{t('reset.newPassword')}</Label>
          <Input id="new-password" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="password" autoComplete="new-password" required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} aria-describedby="new-pw-rules" />
          <PasswordRules id="new-pw-rules" password={password} /></div>
        <div className="space-y-1.5"><Label htmlFor="new-confirm">{t('auth.confirm')}</Label>
          <Input id="new-confirm" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="password" autoComplete="new-password" required disabled={busy} value={confirm} onChange={e => setConfirm(e.target.value)} aria-invalid={mismatch} />
          {mismatch && <p className="text-xs text-destructive">{t('auth.mismatch')}</p>}</div>
      </CardContent>
      <CardFooter className="flex-col gap-3 mt-6">
        <Button type="submit" id="reset-submit" size="lg" className="w-full" disabled={busy || !token || !passwordOk(password) || password !== confirm}>{busy && <Loader2 className="animate-spin" />}{t('reset.save')}</Button>
        <Link to="/login" className="text-sm underline">{t('reset.back')}</Link>
      </CardFooter>
    </form>
  </Frame>
}
