import { useTranslation } from 'react-i18next'
import { Workflow } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { TextLink } from '@/components/text-link'
import type { Trace } from '@/lib/trace'

/** Shown above the run timeline while a run waits for the child run of an Agent node's workflow tool (TASK-0135,
 *  DEC-0066): which workflow it is, its status and a link to it. Nobody answers here: the run goes on by itself when the
 *  child ends, and an approval inside the child is in the Approvals inbox. */
export function ChildWaitPanel({ child, name, status }: { child: NonNullable<NonNullable<Trace['waiting']>['child']>; name?: string | null; status?: string }) {
  const { t } = useTranslation()
  return <Alert id="child-wait-panel" className="m-3 w-auto">
    <Workflow />
    <AlertTitle className="flex items-center gap-2">{t('childRuns.waitingTitle')}
      {status && <Badge variant={status === 'waiting' ? 'outline' : 'secondary'} id="child-wait-status">{t(`status.${status}`)}</Badge>}</AlertTitle>
    <AlertDescription className="space-y-1">
      <p className="text-xs">{t('childRuns.waitingFor', { tool: child.tool || '?', name: name || t('childRuns.unknown') })}</p>
      {status === 'waiting' && <p className="text-xs text-muted-foreground" id="child-wait-approval">{t('childRuns.childWaits')}</p>}
      {child.workflowId && <TextLink id="child-wait-open" to={`/workflows/${child.workflowId}?run=${child.runId}`}>{t('childRuns.openChild')}</TextLink>}
    </AlertDescription>
  </Alert>
}
