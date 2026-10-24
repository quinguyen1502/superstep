import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { GitBranch, RotateCcw } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { JsonEditor } from '@/components/json-editor'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

export type Checkpoint = { index: number; nodes: string[]; labels: string[]; state: unknown; counts: Record<string, number>
  ts: number | null; forkable: boolean; final?: boolean }
const pretty = (v: unknown) => JSON.stringify(v, null, 2)

/** Time travel: the checkpoints of a finished run (the nodes that ran next and the state before them, then the
 * final state). Pick one, inspect or edit its state, and fork: a new run starts at those nodes with that state. */
export function TimeTravelDialog({ runId, open, onOpenChange, onFork }: { runId: string; open: boolean; onOpenChange: (o: boolean) => void
  onFork: (checkpoint: number, state?: Record<string, unknown>) => void }) {
  const { t } = useTranslation()
  const [cps, setCps] = useState<Checkpoint[] | null>(null); const [sel, setSel] = useState(0)
  const [text, setText] = useState(''); const [err, setErr] = useState('')
  const choose = (list: Checkpoint[], i: number) => { setSel(i); setText(pretty(list[i]?.state ?? {})); setErr('') }
  useEffect(() => {
    if (!open) return
    setCps(null); setErr('')
    api<{ checkpoints: Checkpoint[] }>(`/api/runs/${runId}/checkpoints`).then(d => { setCps(d.checkpoints); choose(d.checkpoints, 0) }).catch(e => setErr(e.message))
  }, [open, runId])  // eslint-disable-line react-hooks/exhaustive-deps
  const cp = cps?.[sel]
  const edited = !!cp && text !== pretty(cp.state)
  const fork = () => {
    if (!cp) return
    let state: unknown; try { state = JSON.parse(text) } catch { setErr(t('timeTravel.badJson')); return }
    if (!state || typeof state !== 'object' || Array.isArray(state)) { setErr(t('timeTravel.badJson')); return }
    onOpenChange(false); onFork(cp.index, edited ? state as Record<string, unknown> : undefined)
  }
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="flex max-h-[80vh] flex-col sm:max-w-4xl" id="time-travel-dialog">
      <DialogHeader><DialogTitle>{t('timeTravel.title')}</DialogTitle><DialogDescription>{t('timeTravel.intro')}</DialogDescription></DialogHeader>
      {err && <Alert variant="destructive"><AlertDescription id="time-travel-error">{err}</AlertDescription></Alert>}
      {cps && !cps.length && <p className="text-sm text-muted-foreground">{t('timeTravel.none')}</p>}
      {!!cps?.length && <div className="grid min-h-0 flex-1 grid-cols-[16rem_1fr] gap-3">
        <ScrollArea className="min-h-0 rounded-md border"><ol className="space-y-1 p-1" id="checkpoint-list">
          {cps.map(c => <li key={c.index}><button type="button" data-testid="checkpoint" aria-current={c.index === sel}
            onClick={() => choose(cps, c.index)}
            className={cn('flex w-full items-baseline gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent', c.index === sel && 'bg-accent')}>
            <span className="w-6 shrink-0 tabular-nums text-muted-foreground">{c.index + 1}</span>
            <span className="min-w-0 flex-1 truncate">{c.final ? t('timeTravel.final') : t('timeTravel.before', { nodes: c.labels.join(', ') })}</span>
            {!c.final && !c.forkable && <Badge variant="secondary">{t('timeTravel.tooLarge')}</Badge>}
          </button></li>)}
        </ol></ScrollArea>
        <div className="flex min-h-0 flex-col gap-2">
          <span className="flex items-baseline gap-2 text-xs font-medium text-muted-foreground">{t('timeTravel.state')}
            {edited && <Badge variant="outline" id="time-travel-edited">{t('timeTravel.edited')}</Badge>}</span>
          <JsonEditor id="checkpoint-state" value={text} onChange={setText} readOnly={!cp?.forkable} className="min-h-64 flex-1" />
        </div>
      </div>}
      <DialogFooter>
        {edited && <Button variant="ghost" id="time-travel-reset" onClick={() => cp && setText(pretty(cp.state))}><RotateCcw />{t('timeTravel.reset')}</Button>}
        <Button id="time-travel-fork" disabled={!cp?.forkable} onClick={fork}><GitBranch />{t('timeTravel.fork')}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
}
