/** Agent hand-offs in the Config panel (TASK-0182, REQ-0078, DEC-0073): the agents this one may hand the conversation
 *  to, each with a description the model reads, and the workflow's hand-off limit. The canvas shows the same targets as
 *  dashed links (`lib/handoffs.ts`). */
import { useTranslation } from 'react-i18next'
import { ArrowRightLeft, ChevronDown, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tip } from '@/components/tip'
import { DEFAULT_MAX_HANDOFFS, MAX_HANDOFFS, handoffsOf, type Handoff } from '@/lib/handoffs'

type Agent = { id: string; label: string }

/** The run-wide hand-off limit (workflow `max_handoffs`); empty means the default. */
export function MaxHandoffs({ value, onChange }: { value?: number; onChange: (v: number | undefined) => void }) {
  const { t } = useTranslation()
  return <div className="space-y-1.5">
    <Label htmlFor="max-handoffs" className="text-xs">{t('handoff.max')}</Label>
    <Input id="max-handoffs" type="number" min={0} max={MAX_HANDOFFS} placeholder={String(DEFAULT_MAX_HANDOFFS)} value={value ?? ''}
      onChange={e => onChange(e.target.value === '' ? undefined : Math.max(0, Math.min(MAX_HANDOFFS, Math.round(Number(e.target.value)) || 0)))} />
    <p className="text-[11px] text-muted-foreground">{t('handoff.maxHint', { n: DEFAULT_MAX_HANDOFFS, max: MAX_HANDOFFS })}</p>
  </div>
}

export function AgentHandoffs({ nodeId, data, agents, readOnly, onChange, maxHandoffs, setMaxHandoffs }: {
  nodeId: string; data: Record<string, any>; agents: Agent[]; readOnly?: boolean; onChange: (p: { handoffs: Handoff[] }) => void
  maxHandoffs?: number; setMaxHandoffs: (v: number | undefined) => void }) {
  const { t } = useTranslation()
  const list = handoffsOf(data)
  const others = agents.filter(a => a.id !== nodeId)
  const free = others.filter(a => !list.some(h => h.target === a.id))
  const label = (id: string) => others.find(a => a.id === id)?.label || id
  const set = (next: Handoff[]) => onChange({ handoffs: next })
  return <div className="space-y-3" id="agent-handoffs">
    <div className="flex items-center gap-2">
      <span className="flex-1 text-xs font-semibold uppercase text-muted-foreground">{t('handoff.title')}</span>
      <DropdownMenu><DropdownMenuTrigger asChild disabled={readOnly || !free.length}>
        <Button variant="outline" size="sm" id="agent-add-handoff"><Plus />{t('handoff.add')}<ChevronDown /></Button></DropdownMenuTrigger>
        <DropdownMenuContent align="end">{free.map(a => <DropdownMenuItem key={a.id} id={`agent-handoff-pick-${a.id}`}
          onSelect={() => set([...list, { target: a.id, description: '' }])}><ArrowRightLeft />{a.label}</DropdownMenuItem>)}</DropdownMenuContent></DropdownMenu>
    </div>
    <p className="text-[11px] text-muted-foreground">{t(others.length ? 'handoff.hint' : 'handoff.noAgents')}</p>
    {list.map((h, i) => <div key={h.target} className="space-y-1.5 rounded-md border p-2" data-testid="agent-handoff" data-target={h.target}>
      <div className="flex items-center gap-2">
        <ArrowRightLeft className="size-4 text-muted-foreground" />
        <span className="min-w-0 flex-1 truncate text-sm font-medium">{label(h.target)}</span>
        <Tip tip={t('handoff.remove', { name: label(h.target) })}><Button variant="ghost" size="icon" aria-label={t('handoff.remove', { name: label(h.target) })}
          id={`agent-handoff-remove-${h.target}`} disabled={readOnly} onClick={() => set(list.filter((_, j) => j !== i))}><X /></Button></Tip>
      </div>
      <Input value={h.description || ''} aria-label={t('handoff.description')} placeholder={t('handoff.descriptionPlaceholder')} id={`agent-handoff-desc-${h.target}`}
        onChange={e => set(list.map((x, j) => j === i ? { ...x, description: e.target.value } : x))} />
    </div>)}
    {list.length > 0 && <MaxHandoffs value={maxHandoffs} onChange={setMaxHandoffs} />}
  </div>
}
