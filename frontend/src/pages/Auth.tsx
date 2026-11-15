import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, AlertCircle, Clock, CircleCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { api, scheduleExpiry, setSession } from '@/lib/api'
import { authOptions, type DemoAccount } from '@/lib/demo'
import { ThemeToggle } from '@/components/theme-toggle'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LanguageSwitcher } from '@/components/language-switcher'
import { PasswordRules } from '@/components/password-rules'
import { passwordOk } from '@/lib/password'
import { LogoMark } from '@/components/logo'
import { AppMeta } from '@/components/app-meta'

const safeNext = (n: string | null) => (n && n.startsWith('/') && !n.startsWith('//') && !n.startsWith('/login') && !n.startsWith('/register') ? n : '/workflows')

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { t } = useTranslation(); const nav = useNavigate(); const isLogin = mode === 'login'
  const [params] = useSearchParams(); const expired = params.get('expired') === '1'; const next = safeNext(params.get('next'))
  const reset = params.get('reset') === '1'  // back from a password reset
  const [email, setEmail] = useState<string>(useLocation().state?.email || '')  // router state, not the URL
  // the demo hint and e-mail exist only where the server seeds the demo account (not in production)
  const [demo, setDemo] = useState(false)
  const [visitor, setVisitor] = useState<DemoAccount | null>(null)  // the public demo (STUDIO_DEMO_MODE)
  useEffect(() => { if (isLogin) authOptions().then(o => { setDemo(o.demo); setVisitor(o.demo_mode ?? null); if (o.demo) setEmail(e => e || 'admin@example.com') }).catch(() => {}) }, [isLogin])
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const pwOk = passwordOk(password)
  const mismatch = !isLogin && confirm.length > 0 && password !== confirm
  const canSubmit = !busy && email.trim() && password && (isLogin || (pwOk && confirm && !mismatch))
  const signIn = async (path: string, json: { email: string; password: string }) => {
    setBusy(true)
    try { setSession(await api(path, { method: 'POST', json })); scheduleExpiry(); nav(next, { replace: true }) }
    catch (err: any) { setError(err.message) } finally { setBusy(false) }
  }
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    if (!isLogin && !pwOk) { setError(t('auth.weak')); return }
    if (!isLogin && password !== confirm) { setError(t('auth.mismatch')); return }
    await signIn(`/api/auth/${mode}`, { email, password })
  }
  const other = isLogin ? '/register' : '/login'
  return <div className="relative flex min-h-dvh flex-col bg-muted/40">
    <div className="absolute top-4 right-4 z-10 flex gap-1"><LanguageSwitcher /><ThemeToggle /></div>
    <div className="flex flex-1 items-center justify-center p-4">
    <Card className="w-full max-w-sm">
      <CardHeader className="text-center">
        <LogoMark className="mx-auto mb-2 size-10" />
        <CardTitle className="text-xl">{t(isLogin ? 'auth.loginTitle' : 'auth.registerTitle')}</CardTitle>
        <CardDescription>{t(isLogin ? (demo ? 'auth.loginHint' : 'auth.loginPlain') : 'auth.registerHint')}</CardDescription>
      </CardHeader>
      <form onSubmit={submit} noValidate aria-busy={busy}>
        <CardContent className="space-y-4">
          {reset && !error && <div id="reset-notice" role="status" className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><CircleCheck className="size-4 shrink-0 text-success" />{t('auth.resetDone')}</div>}
          {expired && !error && <div id="expired-notice" role="status" className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><Clock className="size-4 shrink-0 text-warning" />{t('auth.expired')}</div>}
          {error && <Alert variant="destructive" id="auth-error"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
          <div className="space-y-1.5"><Label htmlFor="email">{t('auth.email')}</Label><Input id="email" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="email" autoComplete="email" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" /></div>
          <div className="space-y-1.5"><Label htmlFor="password">{t('auth.password')}</Label>
            <Input id="password" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="password" autoComplete={isLogin ? 'current-password' : 'new-password'} required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} aria-describedby={isLogin ? undefined : 'pw-rules'} />
            {!isLogin && <PasswordRules id="pw-rules" password={password} />}
            {isLogin && <div className="text-right"><Link to="/forgot-password" state={{ email }} id="forgot-link" className="text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground">{t('auth.forgot')}</Link></div>}
          </div>
          {!isLogin && <div className="space-y-1.5"><Label htmlFor="confirm">{t('auth.confirm')}</Label>
            <Input id="confirm" /* ui-class-ok: auth card uses 40px fields as large touch targets; Input has no size variant */ className="h-10" type="password" autoComplete="new-password" required disabled={busy} value={confirm} onChange={e => setConfirm(e.target.value)} aria-invalid={mismatch} />
            {mismatch && <p className="text-xs text-destructive">{t('auth.mismatch')}</p>}</div>}
        </CardContent>
        <CardFooter className="flex-col gap-3 mt-6">
          {visitor && <div className="w-full space-y-1.5"><Button type="button" id="demo-try" variant="secondary" size="lg" /* ui-class-ok: same 44px full-width touch target as the submit button */ className="w-full h-11 text-base" disabled={busy}
            onClick={() => { setError(''); signIn('/api/auth/login', visitor) }}>{t('demo.try')}</Button>
            <p className="text-xs text-muted-foreground text-center">{t('demo.tryHint')}</p></div>}
          <Button type="submit" id="auth-submit" size="lg" /* ui-class-ok: auth submit is a 44px full-width touch target, larger than Button lg */ className="w-full h-11 text-base" disabled={!canSubmit}>{busy && <Loader2 className="animate-spin" />}{t(isLogin ? 'auth.login' : 'auth.register')}</Button>
          <p className="text-sm text-muted-foreground">{t(isLogin ? 'auth.noAccount' : 'auth.haveAccount')}<Link className="underline text-foreground" to={next !== '/workflows' ? `${other}?next=${encodeURIComponent(next)}` : other}>{t(isLogin ? 'auth.register' : 'auth.login')}</Link></p>
        </CardFooter>
      </form>
    </Card>
    </div>
    <AppMeta />
  </div>
}
