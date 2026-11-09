/** Add to Slack: OAuth install of the studio's Slack app, shown when SLACK_CLIENT_ID/SECRET are configured.
 *  Slack sends the browser back to /settings/channels?slack=installed (or ?slack_error=CODE): see SlackOAuthNotice. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { AlertCircle, CircleCheck, ExternalLink, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { errorText } from '@/lib/i18n'

type Info = { enabled: boolean; redirect_uri: string | null; scopes: string }
let info: Promise<Info> | null = null

export function AddToSlack({ scope }: { scope: 'user' | 'org' }) {
  const { t } = useTranslation(); const [on, setOn] = useState(false); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  useEffect(() => { (info ??= api<Info>('/api/approvals/slack/oauth')).then(i => setOn(i.enabled)).catch(() => { info = null }) }, [])
  if (!on) return null
  const go = async () => {
    setBusy(true); setErr('')
    try { location.href = (await api<{ url: string }>('/api/approvals/slack/oauth/start', { method: 'POST', json: { scope } })).url }
    catch (e: any) { setErr(e.message); setBusy(false) }
  }
  return <div className="flex flex-wrap items-center gap-2 rounded-md border border-dashed p-3">
    <div className="min-w-0 flex-1"><div className="text-sm font-medium">{t('slackOauth.title')}</div><p className="text-xs text-muted-foreground">{t('slackOauth.help')}</p></div>
    <Button size="sm" onClick={go} disabled={busy} id={`add-to-slack-${scope}`}>{busy ? <Loader2 className="animate-spin" /> : <ExternalLink />}{t('slackOauth.button')}</Button>
    {err && <p role="alert" className="w-full text-sm text-destructive">{err}</p>}
  </div>
}

export function SlackOAuthNotice() {
  const { t } = useTranslation(); const [params, setParams] = useSearchParams()
  const ok = params.get('slack') === 'installed'; const code = params.get('slack_error')
  if (!ok && !code) return null
  const close = () => { params.delete('slack'); params.delete('slack_error'); setParams(params, { replace: true }) }
  return <Alert variant={ok ? 'default' : 'destructive'} id="slack-oauth-notice">{ok ? <CircleCheck /> : <AlertCircle />}
    <AlertDescription className="flex items-center gap-2">{ok ? t('slackOauth.installed') : errorText({ code: code! })}
      <Button size="sm" variant="ghost" className="ml-auto" onClick={close}>{t('common.close')}</Button></AlertDescription></Alert>
}
