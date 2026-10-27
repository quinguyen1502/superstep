import { useTranslation } from 'react-i18next'
import { ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ErrorAlert } from '@/components/approvals/channel-parts'
import { IdentityRow } from '@/components/approvals/identity-row'
import { slotKey, useSlots } from '@/components/approvals/slots'
import { useMe } from '@/lib/rbac'

/** My chat accounts across every platform / workspace. The public demo's visitor sees them read-only. */
export function AccountsSection() {
  const { t } = useTranslation(); const { slots, setData, err } = useSlots(); const readOnly = !!useMe()?.read_only
  return <div className="space-y-3">
    {readOnly && <Alert variant="warning" id="accounts-read-only"><ShieldAlert /><AlertDescription>{t('approvals.demoReadOnly')}</AlertDescription></Alert>}
    {err && <ErrorAlert>{err}</ErrorAlert>}
    {slots && !slots.length && <p className="text-sm text-muted-foreground">{t('approvals.noChannels')}</p>}
    {slots?.map(s => <IdentityRow key={slotKey(s)} slot={s} onChange={setData} readOnly={readOnly} />)}
  </div>
}
