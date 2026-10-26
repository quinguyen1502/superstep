import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'
import { META, TYPES, REDUCERS, INSERTABLE } from './meta'
import { useStudioCtx } from './studio-context'

/** Left panel: node palette and the state schema (TASK-0040). `onAdd` (phones, TASK-0121): a tap on a card adds that
 *  node, since touch screens cannot drag a card onto the canvas. */
export function EditorPalette({ onAdd }: { onAdd?: (type: string) => void }) {
  const { t } = useTranslation()
  const { state, setState, edit, editable } = useStudioCtx()
  const tap = onAdd && editable ? onAdd : undefined
  // two halves, each with its own scroll, so a long node list never hides the state schema
  return <aside className="h-full bg-muted/30 min-h-0 flex flex-col">
      <section className="flex min-h-0 flex-1 basis-0 flex-col" id="palette-nodes">
        <div className="px-3 pt-3 pb-2 text-xs font-semibold uppercase text-muted-foreground">{t('editor.palette')}</div>
        {tap && <p className="px-3 pb-2 text-[11px] text-muted-foreground" id="palette-tap-hint">{t('editor.mobileNav.addHint')}</p>}
        <ScrollArea className="min-h-0 flex-1"><div className="px-3 pb-3 space-y-2">{TYPES.map(t_ => { const m = META[t_]; const I = m.icon
            const add = tap && INSERTABLE.includes(t_) ? () => tap(t_) : undefined
            return <Card key={t_} draggable={edit} onDragStart={e => { e.dataTransfer.setData('nodetype', t_); e.dataTransfer.effectAllowed = 'move' }}
              {...(add ? { role: 'button', tabIndex: 0, onClick: add, onKeyDown: (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); add() } } } : {})}
              data-testid="palette-card" data-type={t_}
              className={cn('flex-row items-center gap-3 p-2.5 cursor-grab hover:bg-accent transition-colors', add && 'cursor-pointer')}>
              <div className={cn('rounded-md p-1.5', m.color)}><I className="size-4" /></div>
              <div><div className="font-medium leading-tight">{m.label}</div><div className="text-[11px] text-muted-foreground">{t(`nodes.${t_}`)}</div></div>
            </Card> })}</div></ScrollArea>
      </section>
      <Separator />
      <section className="flex min-h-0 flex-1 basis-0 flex-col" id="palette-state">
        <div className="px-3 pt-3 pb-2 text-xs font-semibold uppercase text-muted-foreground">{t('editor.stateSchema')}</div>
        <ScrollArea className="min-h-0 flex-1"><div className="px-3 pt-1 pb-2 divide-y">{state.map((f, i) => <div className="@container space-y-1 py-2 first:pt-1" key={i} data-testid="state-field"><div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-1 @max-[13rem]:grid-cols-[minmax(0,1fr)_auto]">
            <Input className="min-w-0 @max-[13rem]:col-span-full" value={f.name} aria-label={t('editor.fieldName')} onChange={e => setState(s => s.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
            <Select value={f.type} onValueChange={v => setState(s => s.map((x, j) => j === i ? { ...x, type: v, reducer: REDUCERS[v]?.includes(x.reducer || '') ? x.reducer : undefined } : x))}>
              <SelectTrigger className="w-24 @max-[13rem]:w-full" aria-label={t('editor.fieldType')}><SelectValue /></SelectTrigger>
              <SelectContent>{['string', 'number', 'integer', 'boolean', 'object', 'list'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
            <Button variant="ghost" size="icon" aria-label={t('editor.removeField', { name: f.name })} onClick={() => setState(s => s.filter((_, j) => j !== i))}><Trash2 /></Button>
            </div>
            {REDUCERS[f.type] && <Select value={f.reducer || 'replace'} onValueChange={v => setState(s => s.map((x, j) => j === i ? { ...x, reducer: v === 'replace' ? undefined : v } : x))}>
              <SelectTrigger className="w-full min-w-0" id={`reducer-${f.name}`} aria-label={t('editor.reducer')}><SelectValue /></SelectTrigger>
              <SelectContent>{REDUCERS[f.type].map(r => <SelectItem key={r} value={r}>{t(`editor.reducers.${r}`)}</SelectItem>)}</SelectContent>
            </Select>}
          </div>)}</div></ScrollArea>
        <div className="px-3 pt-1 pb-3">
          <Button variant="outline" size="sm" className="w-full" onClick={() => setState(s => [...s, { name: 'field' + (s.length + 1), type: 'string' }])}><Plus />{t('editor.addField')}</Button>
        </div>
      </section>
    </aside>
}
