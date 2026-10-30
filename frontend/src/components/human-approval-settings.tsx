import { TextLink } from '@/components/text-link'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquareShare, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { channelLabel, type Channels } from '@/lib/approvals'
import type { AutoPolicy } from '@/lib/auto-approval'

/** channel_id: the connection (personal or org); channel: its kind (kept for labels and older workflows). */
export type Approval = { channel_id?: string; channel?: string; target?: string; approvers?: string[]; auto?: AutoPolicy }  // auto: AI review (TASK-0188)

/** Per-Human-node approval channel (TASK-0022): where the Approve/Reject message goes, and who may answer it, on any
 * Human node, from the channel or the Approvals inbox (TASK-0065). */
export function HumanApprovalSettings({ value, channels, onChange }: { value?: Approval; channels: Channels | null; onChange: (v: Approval) => void }) {
  const { t } = useTranslation(); const v = value || {}
  const set = (patch: Approval) => onChange({ ...v, ...patch })
  const [raw, setRaw] = useState((v.approvers || []).join(', '))  // free text while typing; the list is what is saved
  const list = channels?.channels || []
  const chosen = v.channel_id ? list.find(c => c.id === v.channel_id) : list.find(c => c.kind === v.channel)
  const missing = !!v.channel && !chosen
  return <div className="space-y-3" id="human-approval">
    <Separator />
    <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground"><MessageSquareShare className="size-3.5" />{t('approvals.node.title')}</div>
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('approvals.node.channel')}</Label>
      <Select value={chosen?.id || (missing ? 'missing' : 'none')} onValueChange={id => { const c = list.find(x => x.id === id); set(c ? { channel_id: c.id, channel: c.kind } : { channel_id: '', channel: '' }) }}>
        <SelectTrigger className="w-full" id="approval-channel"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('approvals.node.studioOnly')}</SelectItem>
          {missing && <SelectItem value="missing" disabled><ChannelLogo kind={v.channel || ''} />{t(`approvals.kind.${v.channel}`)} · {t('approvals.notConnected')}</SelectItem>}
          {list.map(c => <SelectItem key={c.id} value={c.id}><ChannelLogo kind={c.kind} />{channelLabel(t, c)}</SelectItem>)}</SelectContent></Select>
      {!list.length && <p className="text-xs text-muted-foreground" id="approval-no-channels">{t('approvals.node.connectFirst')} <TextLink to="/settings/channels" id="approval-open-channels">{t('approvals.node.addChannel')}</TextLink></p>}</div>
    {v.channel && <>
      {missing && <Alert variant="warning" id="approval-not-connected"><TriangleAlert /><AlertDescription className="text-xs">{t('approvals.node.connectFirst')} <TextLink to="/settings/channels">{t('approvals.node.addChannel')}</TextLink></AlertDescription></Alert>}
      {channels?.kinds.find(k => k.kind === v.channel)?.target_required === false
        ? <p className="text-xs text-muted-foreground" id="approval-no-target">{t('approvals.node.noTarget')}</p>
        : <div className="space-y-1.5"><Label htmlFor="approval-target" className="text-xs text-muted-foreground">{t(`approvals.node.target.${v.channel}`)}</Label>
          <Input id="approval-target" className="font-mono text-xs" value={v.target || ''} placeholder={t(`approvals.node.targetPh.${v.channel}`)} onChange={e => set({ target: e.target.value })} /></div>}
    </>}
    <div className="space-y-1.5"><Label htmlFor="approval-approvers" className="text-xs text-muted-foreground">{t('approvals.node.approvers')}</Label>
      <Input id="approval-approvers" className="text-xs" value={raw} placeholder="lead@example.com, ops@example.com"
        onChange={e => { setRaw(e.target.value); set({ approvers: e.target.value.split(',').map(x => x.trim()).filter(Boolean) }) }} />
      <p className="text-xs text-muted-foreground">{t('approvals.node.approversHelp')}</p></div>
  </div>
}
