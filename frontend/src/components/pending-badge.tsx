import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { UserCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useInboxCount } from '@/lib/use-inbox-count'

/** Header entry to the Approvals inbox, with the number of steps waiting for the user. */
export function PendingBadge() {
  const { t } = useTranslation(); const nav = useNavigate(); const n = useInboxCount()
  const label = n ? t('human.pendingCount', { count: n }) : t('inbox.title')
  return <Tooltip><TooltipTrigger asChild>
    <Button variant="ghost" id="pending-badge" aria-label={label} onClick={() => nav('/approvals')}>
      <UserCheck className="text-node-human" />{n > 0 && <Badge variant="secondary" data-testid="pending-count">{n}</Badge>}
    </Button></TooltipTrigger><TooltipContent>{label}</TooltipContent></Tooltip>
}
