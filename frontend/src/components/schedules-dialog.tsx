/** Cron schedules of a workflow (TASK-0046): list, turn on/off, delete, and add one with a live preview of its next runs. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CalendarClock, Plus, Trash2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { JsonEditor } from '@/components/json-editor'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import i18n from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'

type Schedule = { id: string; name: string; cron: string; timezone: string; input: Record<string, unknown>; enabled: boolean
  next_runs: number[]; last_run: number | null; last_run_id: string | null; note: string | null }
const PRESETS = ['0 * * * *', '*/15 * * * *', '0 9 * * *', '0 9 * * 1-5', '0 9 * * 1', '0 0 1 * *'] as const
const browserZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
const timeZones = () => typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : []
const at = (ts: number | null, tz: string) => {
  if (!ts) return '—'
  try { return new Date(ts * 1000).toLocaleString(i18n.resolvedLanguage, { timeZone: tz, dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return new Date(ts * 1000).toLocaleString(i18n.resolvedLanguage) }
}

export function SchedulesDialog({ wid, open, onOpenChange, defaultInput }: { wid?: string; open: boolean; onOpenChange: (v: boolean) => void; defaultInput: string }) {
  const { t } = useTranslation(); const [items, setItems] = useState<Schedule[]>([]); const [err, setErr] = useState('')
  const [name, setName] = useState(''); const [expr, setExpr] = useState('0 9 * * 1-5'); const [tz, setTz] = useState(browserZone)
  const [input, setInput] = useState(defaultInput); const [preview, setPreview] = useState<number[] | string>([])
  const [zones] = useState(timeZones)
  const load = () => wid && api<Schedule[]>(`/api/workflows/${wid}/schedules`).then(setItems).catch(e => setErr(e.message))
  useLoadWhen(open, () => { setErr(''); setName(''); setInput(defaultInput); load() })
  useEffect(() => {  // next runs of the expression being typed (the server parses it)
    if (!open) return
    const h = setTimeout(() => api<{ next_runs: number[] }>('/api/schedules/preview', { method: 'POST', json: { cron: expr, timezone: tz } })
      .then(r => setPreview(r.next_runs.slice(0, 3))).catch(e => setPreview(e.message)), 300)
    return () => clearTimeout(h)
  }, [open, expr, tz])
  const run = async (f: () => Promise<unknown>) => { setErr(''); try { await f(); load() } catch (e: any) { setErr(e.message) } }
  const add = () => run(async () => {
    let parsed: unknown
    try { parsed = JSON.parse(input || '{}') } catch { throw new Error(t('schedules.badJson')) }
    await api(`/api/workflows/${wid}/schedules`, { method: 'POST', json: { name: name.trim() || t('schedules.defaultName'), cron: expr, timezone: tz, input: parsed } })
    setName('')
  })
  const toggle = (s: Schedule, on: boolean) => run(() => api(`/api/workflows/${wid}/schedules/${s.id}`, { method: 'PATCH', json: { enabled: on } }))
  const confirmDel = useConfirmDelete()
  const remove = (s: Schedule) => confirmDel.ask({ title: t('schedules.deleteTitle', { name: s.name }), name: s.name, description: t('schedules.deleteBody'),
    onConfirm: async () => { await api(`/api/workflows/${wid}/schedules/${s.id}`, { method: 'DELETE' }); load() } })
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-2xl max-h-[90dvh] flex flex-col overflow-hidden" id="schedules-dialog">
      <DialogHeader className="shrink-0"><DialogTitle>{t('schedules.title')}</DialogTitle><DialogDescription>{t('schedules.desc')}</DialogDescription></DialogHeader>
      <div className="-mx-1 min-h-0 flex-1 space-y-4 overflow-y-auto px-1">
        {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
        <div className="space-y-2" id="schedule-list">
          {items.map(s => <div key={s.id} data-testid="schedule-row" data-name={s.name} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm">
            <Switch checked={s.enabled} onCheckedChange={v => toggle(s, v)} aria-label={t('schedules.enabledFor', { name: s.name })} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><span className="truncate font-medium">{s.name}</span><code className="font-mono text-xs text-muted-foreground">{s.cron}</code></div>
              <div className="text-xs text-muted-foreground" data-testid="schedule-next">
                {s.enabled ? t('schedules.next', { when: at(s.next_runs[0] ?? null, s.timezone), tz: s.timezone })
                  : s.note ? <span className="text-warning">{t(`schedules.notes.${s.note}`)}</span> : t('schedules.off')}
                {s.last_run && <> · {t('schedules.last', { when: at(s.last_run, s.timezone) })}</>}</div>
            </div>
            {!s.enabled && s.note && <Badge variant="outline" className="border-warning text-warning">{t('schedules.stopped')}</Badge>}
            <Button variant="ghost" size="icon-sm" aria-label={t('schedules.deleteFor', { name: s.name })} onClick={() => remove(s)}><Trash2 /></Button>
          </div>)}
          {!items.length && <p className="text-xs text-muted-foreground">{t('schedules.empty')}</p>}
        </div>
        <div className="space-y-3 rounded-md border p-3">
          <div className="text-xs font-semibold uppercase text-muted-foreground">{t('schedules.add')}</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5"><Label htmlFor="schedule-name" className="text-xs text-muted-foreground">{t('schedules.name')}</Label>
              <Input id="schedule-name" value={name} placeholder={t('schedules.defaultName')} onChange={e => setName(e.target.value)} /></div>
            <div className="space-y-1.5"><Label htmlFor="schedule-preset" className="text-xs text-muted-foreground">{t('schedules.preset')}</Label>
              <Select value={(PRESETS as readonly string[]).includes(expr) ? expr : 'custom'} onValueChange={v => v !== 'custom' && setExpr(v)}>
                <SelectTrigger id="schedule-preset" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{PRESETS.map(p => <SelectItem key={p} value={p}>{t(`schedules.presets.${p}`)}</SelectItem>)}
                  <SelectItem value="custom">{t('schedules.presets.custom')}</SelectItem></SelectContent></Select></div>
            <div className="space-y-1.5"><Label htmlFor="schedule-cron" className="text-xs text-muted-foreground">{t('schedules.cron')}</Label>
              <Input id="schedule-cron" className="font-mono text-xs" value={expr} onChange={e => setExpr(e.target.value)} aria-describedby="schedule-preview" /></div>
            <div className="space-y-1.5"><Label htmlFor="schedule-tz" className="text-xs text-muted-foreground">{t('schedules.timezone')}</Label>
              <Select value={tz} onValueChange={setTz}>
                <SelectTrigger id="schedule-tz" className="w-full font-mono"><SelectValue /></SelectTrigger>
                <SelectContent>{[...new Set(['UTC', browserZone(), tz, ...zones])].sort().map(zone => <SelectItem key={zone} value={zone}>{zone}</SelectItem>)}</SelectContent>
              </Select></div>
          </div>
          <div id="schedule-preview" className="text-xs" aria-live="polite">
            {typeof preview === 'string' ? <span className="text-destructive">{preview}</span>
              : preview.length > 0 && <span className="text-muted-foreground"><CalendarClock className="mr-1 inline size-3.5 align-[-2px]" />{t('schedules.preview', { times: preview.map(p => at(p, tz)).join(' · ') })}</span>}
          </div>
          <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('schedules.input')}</Label>
            <JsonEditor id="schedule-input" value={input} onChange={setInput} className="h-28" /></div>
          <div className="flex justify-end"><Button id="schedule-create" onClick={add} disabled={!wid || typeof preview === 'string'}><Plus />{t('schedules.create')}</Button></div>
        </div>
        <p className="text-xs text-muted-foreground">{t('schedules.help')}</p>
      </div>
    </DialogContent>
    {confirmDel.dialog}
  </Dialog>
}
