/** /approvals (TASK-0065, DEC-0043): every step waiting for the signed-in user, as run owner or listed approver,
 * across workflows, answered in place. Approvers see the request only; "Open run" is for those who may read the run. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ArrowLeft, CircleCheck, Inbox, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AiOpinionNote, AiReviewPanel } from '@/components/approvals/ai-review-panel'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { HumanAnswer } from '@/components/human-answer'
import { LanguageSwitcher } from '@/components/language-switcher'
import { NotificationBell } from '@/components/notification-bell'
import { PendingBadge } from '@/components/pending-badge'
import { ThemeToggle } from '@/components/theme-toggle'
import { UserMenu } from '@/components/user-menu'
import { api } from '@/lib/api'
import { INBOX_POLL_MS, type InboxItem } from '@/lib/approvals'
import { fmtDate } from '@/lib/i18n'
import { Logo } from '@/components/logo'

export function ApprovalsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<InboxItem[] | null>(null); const [err, setErr] = useState('')
  const [busy, setBusy] = useState<string | null>(null); const [sent, setSent] = useState<string[]>([])
  const rowKey = (it: InboxItem) => `${it.run_id}:${it.node}`
  const [now, setNow] = useState(() => Date.now())
  const load = () => api<InboxItem[]>('/api/approvals/inbox').then(xs => { setItems(xs); setErr(''); setNow(Date.now()) }).catch(e => setErr(e.message))
  useEffect(() => {
    load(); const id = setInterval(load, INBOX_POLL_MS)
    window.addEventListener('focus', load)
    return () => { clearInterval(id); window.removeEventListener('focus', load) }
  }, [])
  const answer = async (it: InboxItem, response: string) => {
    const key = rowKey(it); setBusy(key); setErr('')
    try { await api(`/api/approvals/inbox/${it.run_id}`, { method: 'POST', json: { response, node: it.node } }); setSent(s => s.includes(key) ? s : [...s, key]) }
    catch (e: any) { setErr(e.message) } finally { setBusy(null); load() }
  }
  return <div className="min-h-dvh bg-background text-foreground">
    <header className="flex h-14 items-center gap-3 border-b px-6">
      <Link to="/workflows"><Logo /></Link>
      <div className="ml-auto flex items-center gap-1"><PendingBadge /><NotificationBell /><LanguageSwitcher /><ThemeToggle /><UserMenu /></div>
    </header>
    <main className="mx-auto max-w-3xl space-y-4 p-6" id="approvals-page">
      <Button variant="ghost" size="sm" asChild className="-ml-2"><Link to="/workflows" id="approvals-back"><ArrowLeft />{t('settings.back')}</Link></Button>
      <div><h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">{t('inbox.title')}{!!items?.length && <Badge variant="secondary" id="inbox-count">{items.length}</Badge>}</h1>
        <p className="text-sm text-muted-foreground">{t('inbox.intro')}</p></div>
      {err && <Alert variant="destructive" id="inbox-error"><AlertDescription>{err}</AlertDescription></Alert>}
      {sent.length > 0 && <div role="status" id="inbox-sent" className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm"><CircleCheck className="size-4 shrink-0 text-success" />{t('inbox.sent')}</div>}
      {!items && !err && <Loader2 className="size-5 animate-spin text-muted-foreground" />}
      {items && !items.length && <div id="inbox-empty" className="flex flex-col items-center gap-2 py-14 text-center">
        <div className="rounded-full bg-muted p-3 text-muted-foreground"><Inbox className="size-5" /></div>
        <div className="font-medium">{t('inbox.empty')}</div><div className="text-sm text-muted-foreground">{t('inbox.emptyHelp')}</div></div>}
      {items?.map(it => <Card key={`${it.run_id}:${it.node}`} data-testid="inbox-row" data-run={it.run_id} data-node={it.node} className="gap-3">
        <CardHeader className="px-4">
          <CardTitle className="text-base">{it.workflow_name || it.workflow_id || it.run_id}</CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
            <span>{t('human.node', { label: it.label || it.node })}</span>
            <span className="flex items-center gap-1">{it.channel ? <><ChannelLogo kind={it.channel} className="size-3.5" />{t(`approvals.kind.${it.channel}`)}</> : t('inbox.studio')}</span>
            {it.owner_email && <span data-testid="inbox-owner">{t('inbox.from', { email: it.owner_email })}</span>}
            <span className="tabular-nums">{t('inbox.since', { when: fmtDate(it.waiting_since) })}</span>
            {it.due_at != null && (it.due_at * 1000 < now
              ? <Badge variant="destructive" data-testid="inbox-overdue">{t('inbox.overdue')}</Badge>
              : <span className="tabular-nums" data-testid="inbox-due">{t('inbox.due', { when: fmtDate(it.due_at) })}</span>)}
          </CardDescription>
          {it.can_open && it.workflow_id && <CardAction><Button size="sm" variant="outline" asChild>
            <Link to={`/workflows/${it.workflow_id}?run=${it.run_id}`} data-testid="inbox-open">{t('inbox.openRun')}</Link></Button></CardAction>}
        </CardHeader>
        <CardContent className="space-y-3 px-4">
          {it.prompt && <p className="whitespace-pre-wrap text-sm" data-testid="inbox-question">{it.prompt}</p>}
          {it.ai && <AiOpinionNote ai={it.ai} />}
          <HumanAnswer busy={busy === rowKey(it)} onRespond={r => answer(it, r)} />
        </CardContent>
      </Card>)}
      <AiReviewPanel onError={setErr} />
    </main>
  </div>
}
