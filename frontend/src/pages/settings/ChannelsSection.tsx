/** Channels: one collapsible card per platform with its status, Org / Personal connections (tabs inside the card),
 *  Test connection, and my verified accounts for that platform inline. Search + status + scope filters. */
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Building2, ChevronDown, CircleCheck, CircleDashed, SearchX, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AddConnection, ConnectionItem, ErrorAlert } from '@/components/approvals/channel-parts'
import { IdentityRow } from '@/components/approvals/identity-row'
import { slotKey, useSlots, type Slot, type Slots } from '@/components/approvals/slots'
import { AddToSlack, SlackOAuthNotice } from '@/components/approvals/add-to-slack'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { FilterBar } from '@/components/settings/filter-bar'
import type { Channel, ChannelKind, Channels } from '@/lib/approvals'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useOnChange } from '@/lib/use-when'

type Scope = 'org' | 'user'
const SCOPES: Scope[] = ['org', 'user']

function PlatformCard({ k, data, conns, slots, onSlots, reload, initialScope }: {
  k: ChannelKind; data: Channels; conns: Channel[]; slots: Slot[]; onSlots: (d: Slots) => void; reload: () => void; initialScope: Scope | null
}) {
  const { t } = useTranslation()
  const has = (s: Scope) => conns.some(c => c.scope === s)
  const [open, setOpen] = useState(() => conns.length > 0)
  const [tab, setTab] = useState<Scope>(initialScope || (has('org') && !has('user') ? 'org' : 'user'))
  useOnChange(initialScope, v => { if (v) setTab(v) })
  const connected = conns.length > 0
  return <Collapsible open={open} onOpenChange={setOpen} asChild>
    <Card data-testid={`channel-card-${k.kind}`} className="gap-4">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2"><ChannelLogo kind={k.kind} className="size-5" />{t(`approvals.kind.${k.kind}`)}
          <Badge variant={connected ? 'default' : 'outline'} data-testid="status">{connected ? <CircleCheck /> : <CircleDashed />}{t(connected ? 'settings.status.connected' : 'settings.status.notSetUp')}</Badge>
          {has('org') && <Badge variant="secondary"><Building2 />{t('approvals.scope.org')}</Badge>}
          {has('user') && <Badge variant="secondary"><User />{t('approvals.scope.user')}</Badge>}
        </CardTitle>
        <CardDescription>{t(`settings.platform.${k.kind}`)}</CardDescription>
        <CardAction><CollapsibleTrigger asChild><Button variant="ghost" size="icon" aria-label={t('settings.toggle')} id={`channel-card-${k.kind}-toggle`}>
          <ChevronDown className={cn('transition-transform', open && 'rotate-180')} /></Button></CollapsibleTrigger></CardAction>
      </CardHeader>
      <CollapsibleContent>
        <CardContent className="space-y-4">
          <Tabs value={tab} onValueChange={v => setTab(v as Scope)}>
            <TabsList>{SCOPES.map(s => <TabsTrigger key={s} value={s} id={`channel-card-${k.kind}-tab-${s}`}>
              {s === 'org' ? <Building2 /> : <User />}{t(`approvals.scope.${s}`)}<Badge variant="outline" className="ml-1 px-1.5">{conns.filter(c => c.scope === s).length}</Badge></TabsTrigger>)}</TabsList>
            {SCOPES.map(s => <TabsContent key={s} value={s} className="space-y-3 pt-2">
              <p className="text-xs text-muted-foreground">{t(`settings.scopeHelp.${s}`)}</p>
              {conns.filter(c => c.scope === s).map(c => <ConnectionItem key={c.id} c={c} k={k} publicUrl={data.public_url} onChange={reload} />)}
              {s === 'org' && !data.is_admin
                ? !has('org') && <p className="text-sm text-muted-foreground">{t('settings.orgAskAdmin')}</p>
                : <>{k.kind === 'slack' && <AddToSlack scope={s} />}<AddConnection k={k} scope={s} onChange={reload} collapsed={has(s)} /></>}
            </TabsContent>)}
          </Tabs>
          <Separator />
          <div className="space-y-3" data-testid={`channel-card-${k.kind}-accounts`}>
            <div><h3 className="text-sm font-medium">{t('settings.myAccounts')}</h3>
              <p className="text-xs text-muted-foreground">{t('settings.myAccountsHelp')}</p></div>
            {slots.length ? slots.map(s => <IdentityRow key={slotKey(s)} slot={s} onChange={onSlots} />)
              : <p className="text-sm text-muted-foreground">{t('settings.noAccountSlot')}</p>}
          </div>
        </CardContent>
      </CollapsibleContent>
    </Card>
  </Collapsible>
}

export function ChannelsSection() {
  const { t } = useTranslation()
  const [data, setData] = useState<Channels | null>(null); const [err, setErr] = useState('')
  const { slots, setData: setSlots, load: loadSlots, err: slotErr } = useSlots()
  const [q, setQ] = useState(''); const [status, setStatus] = useState('all'); const [scope, setScope] = useState('all')
  const load = () => api<Channels>('/api/approvals/channels').then(d => { setData(d); setErr('') }).catch(e => setErr(e.message))
  const reload = () => { load(); loadSlots() }
  useEffect(() => { load() }, [])
  const cards = useMemo(() => (data?.kinds || []).map(k => ({ k, conns: data!.channels.filter(c => c.kind === k.kind) })).filter(({ k, conns }) => {
    const needle = q.trim().toLowerCase()
    const text = [t(`approvals.kind.${k.kind}`), ...conns.flatMap(c => [c.name, c.team_id])].filter(Boolean).join(' ').toLowerCase()
    return (!needle || text.includes(needle)) && (status === 'all' || (status === 'connected') === conns.length > 0)
      && (scope === 'all' || conns.some(c => c.scope === scope))
  }), [data, q, status, scope, t])
  const all = (label: string) => ({ value: 'all', label })
  return <div className="space-y-4">
    <SlackOAuthNotice />
    {data?.org_usable === false && <ErrorAlert>{t('policy.blockedChannels')}</ErrorAlert>}
    <FilterBar id="channel-filters" q={q} onQ={setQ} placeholder={t('settings.searchChannels')} filters={[
      { id: 'status', label: t('settings.filter.status'), value: status, onChange: setStatus,
        options: [all(t('settings.filter.anyStatus')), { value: 'connected', label: t('settings.status.connected') }, { value: 'not_set_up', label: t('settings.status.notSetUp') }] },
      { id: 'scope', label: t('settings.filter.scope'), value: scope, onChange: setScope,
        options: [all(t('settings.filter.anyScope')), ...SCOPES.map(s => ({ value: s, label: t(`approvals.scope.${s}`) }))] },
    ]} />
    {(err || slotErr) && <ErrorAlert>{err || slotErr}</ErrorAlert>}
    {!data && !err && <div className="space-y-3" aria-busy="true"><span className="sr-only">{t('common.loading')}</span>{Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-28 w-full" />)}</div>}
    {data && !cards.length && <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-sm text-muted-foreground" id="channels-none">
      <SearchX className="size-6" />{t('settings.noMatch')}</div>}
    {data && cards.map(({ k, conns }) => <PlatformCard key={k.kind} k={k} data={data} conns={conns} reload={reload}
      slots={(slots || []).filter(s => s.kind === k.kind)} onSlots={setSlots} initialScope={scope === 'all' ? null : scope as Scope} />)}
  </div>
}
