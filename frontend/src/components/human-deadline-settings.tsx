import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Clock } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'

/** A Human node's deadline: durations are "<n>m|h|d"; the server validates and fires them. */
export type Deadline = { after?: string; remind_every?: string; on_timeout?: 'reject' | 'approve' | 'escalate'; escalate_to?: string[] }
const UNITS = ['m', 'h', 'd'] as const
const ACTIONS = ['reject', 'approve', 'escalate'] as const
const split = (v?: string): [string, string] => { const m = /^(\d+)([mhd])$/.exec(v || ''); return m ? [m[1], m[2]] : ['', 'h'] }

function Duration({ id, value, onChange, optional }: { id: string; value?: string; onChange: (v: string) => void; optional?: boolean }) {
  const { t } = useTranslation(); const [n, unit] = split(value)
  const set = (num: string, u: string) => onChange(num ? `${num}${u}` : '')
  return <div className="flex gap-2">
    <Input id={id} type="number" min={1} inputMode="numeric" className="w-24 text-xs" value={n} placeholder={optional ? '—' : '1'}
      onChange={e => set(e.target.value.replace(/\D/g, '').replace(/^0+/, ''), unit)} />
    <Select value={unit} onValueChange={u => set(n || (optional ? '' : '1'), u)}>
      <SelectTrigger className="flex-1" id={`${id}-unit`} aria-label={t('deadline.unit')}><SelectValue /></SelectTrigger>
      <SelectContent>{UNITS.map(u => <SelectItem key={u} value={u}>{t(`deadline.units.${u}`)}</SelectItem>)}</SelectContent>
    </Select>
  </div>
}

export function HumanDeadlineSettings({ value, onChange }: { value?: Deadline; onChange: (v: Deadline | undefined) => void }) {
  const { t } = useTranslation(); const v = value || {}; const on = !!v.after
  const set = (patch: Deadline) => onChange({ ...v, ...patch })
  const [raw, setRaw] = useState((v.escalate_to || []).join(', '))
  return <div className="space-y-3" id="human-deadline">
    <Separator />
    <div className="flex items-center gap-2">
      <Label htmlFor="deadline-on" className="flex flex-1 items-center gap-2 text-xs font-semibold uppercase text-muted-foreground"><Clock className="size-3.5" />{t('deadline.title')}</Label>
      <Switch id="deadline-on" checked={on} onCheckedChange={c => onChange(c ? { after: '1d', on_timeout: 'reject' } : undefined)} />
    </div>
    {!on && <p className="text-xs text-muted-foreground">{t('deadline.off')}</p>}
    {on && <>
      <div className="space-y-1.5"><Label htmlFor="deadline-after" className="text-xs text-muted-foreground">{t('deadline.after')}</Label>
        <Duration id="deadline-after" value={v.after} onChange={x => set({ after: x || '1d' })} /></div>
      <div className="space-y-1.5"><Label htmlFor="deadline-remind" className="text-xs text-muted-foreground">{t('deadline.remindEvery')}</Label>
        <Duration id="deadline-remind" optional value={v.remind_every} onChange={x => set({ remind_every: x || undefined })} />
        <p className="text-xs text-muted-foreground">{t('deadline.remindHelp')}</p></div>
      <div className="space-y-1.5"><Label htmlFor="deadline-action" className="text-xs text-muted-foreground">{t('deadline.onTimeout')}</Label>
        <Select value={v.on_timeout || 'reject'} onValueChange={a => set({ on_timeout: a as Deadline['on_timeout'] })}>
          <SelectTrigger className="w-full" id="deadline-action"><SelectValue /></SelectTrigger>
          <SelectContent>{ACTIONS.map(a => <SelectItem key={a} value={a}>{t(`deadline.actions.${a}`)}</SelectItem>)}</SelectContent>
        </Select></div>
      {v.on_timeout === 'escalate' && <div className="space-y-1.5"><Label htmlFor="deadline-escalate" className="text-xs text-muted-foreground">{t('deadline.escalateTo')}</Label>
        <Input id="deadline-escalate" className="text-xs" value={raw} placeholder="boss@example.com"
          onChange={e => { setRaw(e.target.value); set({ escalate_to: e.target.value.split(',').map(x => x.trim()).filter(Boolean) }) }} />
        <p className="text-xs text-muted-foreground">{t('deadline.escalateHelp')}</p></div>}
    </>}
  </div>
}
