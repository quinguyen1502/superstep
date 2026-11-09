import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { UserCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useInboxCount } from '@/lib/use-inbox-count'

/** Workflows page: how many steps wait for the user, with a link to the Approvals inbox. Hidden at 0. */
export function PendingRuns() {
  const { t } = useTranslation(); const n = useInboxCount()
  if (!n) return null
  return <Card id="pending-runs" className="gap-2">
    <CardHeader className="px-4"><CardTitle className="flex items-center gap-2 text-base"><UserCheck className="size-4 text-node-human" />{t('human.pendingTitle')}<Badge variant="secondary">{n}</Badge></CardTitle>
      <CardDescription>{t('inbox.intro')}</CardDescription>
      <CardAction><Button size="sm" variant="outline" asChild><Link to="/approvals" id="pending-runs-open">{t('inbox.open')}</Link></Button></CardAction></CardHeader>
  </Card>
}
