import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import { pct, type AiOpinion, type AutoStatus, type ReviewedWorkflow } from '@/lib/auto-approval'

/** The AI's opinion on a waiting step (suggest mode, TASK-0188): advice for the person, never an answer. */
export function AiOpinionNote({ ai }: { ai: AiOpinion }) {
  const { t } = useTranslation()
  return <div className="space-y-1 rounded-md border bg-muted/50 px-3 py-2 text-sm" data-testid="inbox-ai">
    <div className="flex flex-wrap items-center gap-2"><Badge variant="secondary"><Sparkles />{t('aiReview.badge')}</Badge>
      <span className="font-medium" data-testid="inbox-ai-decision">{t(`aiReview.decision.${ai.decision}`, { defaultValue: ai.decision })}</span>
      {ai.confidence != null && <span className="text-xs tabular-nums text-muted-foreground">{t('aiReview.confidence', { rate: pct(ai.confidence) })}</span>}</div>
    {ai.reason && <p className="whitespace-pre-wrap text-xs text-muted-foreground" data-testid="inbox-ai-reason">{ai.reason}</p>}
  </div>
}

/** AI review on the Approvals page (TASK-0188, REQ-0081): per workflow the last 30 days' counts, the AI/human agreement
 * rate and the pause switch (owner or admin); the organisation switch for admins. Pausing sends requests to people. */
export function AiReviewPanel({ onError }: { onError: (m: string) => void }) {
  const { t } = useTranslation()
  const [rows, setRows] = useState<ReviewedWorkflow[] | null>(null); const [org, setOrg] = useState<AutoStatus | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const load = () => Promise.all([api<ReviewedWorkflow[]>('/api/approvals/auto/workflows'), api<AutoStatus>('/api/approvals/auto')])
    .then(([w, o]) => { setRows(w); setOrg(o) }).catch(e => onError(e.message))
  useEffect(() => { load() }, [])
  const pause = async (key: string, url: string, paused: boolean) => {
    setBusy(key); try { await api(url, { method: 'PUT', json: { paused } }); await load() } catch (e: any) { onError(e.message) } finally { setBusy(null) }
  }
  if (!rows || !org || (!rows.length && !org.can_manage)) return null
  return <Card id="ai-review" className="gap-3">
    <CardHeader className="px-4"><CardTitle className="flex items-center gap-2 text-base"><Sparkles className="size-4" />{t('aiReview.panelTitle')}</CardTitle>
      <CardDescription className="text-xs">{t(org.enabled ? 'aiReview.panelIntro' : 'aiReview.operatorOff')}</CardDescription></CardHeader>
    <CardContent className="space-y-3 px-4">
      {org.can_manage && <div className="flex items-center gap-2 rounded-md border px-3 py-2" id="ai-review-org">
        <Switch id="ai-review-org-pause" checked={org.org_paused} disabled={!org.enabled || busy === 'org'} onCheckedChange={c => pause('org', '/api/approvals/auto', c)} />
        <Label htmlFor="ai-review-org-pause" className="flex-1 text-sm font-normal">{t('aiReview.pauseOrg')}</Label></div>}
      {!rows.length && <p className="text-sm text-muted-foreground" id="ai-review-empty">{t('aiReview.none')}</p>}
      {rows.map(w => { const s = w.stats; const id = `ai-review-pause-${w.workflow_id}`
        return <div key={w.workflow_id} data-testid="ai-review-row" data-workflow={w.workflow_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border px-3 py-2">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2"><Link to={`/workflows/${w.workflow_id}`} className="truncate font-medium hover:underline">{w.name || w.workflow_id}</Link>
              {w.modes.map(m => <Badge key={m} variant="outline">{t(`aiReview.modes.${m}`)}</Badge>)}</div>
            {s && <div className="flex flex-wrap gap-x-3 text-xs tabular-nums text-muted-foreground" data-testid="ai-review-stats">
              <span>{t('aiReview.stats.today', { n: s.today })}</span><span>{t('aiReview.stats.approved', { n: s.approved })}</span>
              <span>{t('aiReview.stats.escalated', { n: s.escalated })}</span><span>{t('aiReview.stats.suggested', { n: s.suggested })}</span>
              <span data-testid="ai-review-agreement">{s.agreement == null ? t('aiReview.agreementNone') : t('aiReview.agreementShort', { rate: pct(s.agreement) })}</span></div>}
          </div>
          <div className="flex items-center gap-2"><Switch id={id} checked={w.paused} disabled={!org.enabled || busy === w.workflow_id}
            onCheckedChange={c => pause(w.workflow_id, `/api/approvals/auto/workflows/${w.workflow_id}`, c)} />
            <Label htmlFor={id} className="text-xs font-normal">{t('aiReview.pause')}</Label></div>
        </div> })}
    </CardContent>
  </Card>
}
