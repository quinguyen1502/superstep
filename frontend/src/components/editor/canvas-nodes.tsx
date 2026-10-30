import { useContext, useEffect, useRef } from 'react'
import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react'
import { Loader2, CheckCircle2, XCircle, Sparkles, UserCheck, Square, ShieldAlert } from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'
import { META } from './meta'
import { HANDOFF_HANDLE } from '@/lib/handoffs'
import { CanvasEdit } from './canvas-edit'
import { Tip } from '@/components/tip'
import { useCodeRuntime } from '@/lib/code-runtime'

export const LOCK_CLOSED = 'M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z'
export const LOCK_OPEN = 'M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z'

/** Filled React Flow lock mark. Control CSS clamps every svg to 12×12, which squashes the stock 25×32 viewBox, so the mark sits in a square. */
export function CanvasLockIcon({ locked }: { locked: boolean }) {
  return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <path transform="translate(3.5 0)" d={locked ? LOCK_CLOSED : LOCK_OPEN} />
  </svg>
}

export function StatusBadge({ s }: { s?: string }) {
  const { t } = useTranslation()
  if (s === 'running') return <Badge variant="warning" className="gap-1"><Loader2 className="size-3 animate-spin" />{t('status.running')}</Badge>
  if (s === 'done') return <Badge variant="success" className="gap-1"><CheckCircle2 className="size-3" />{t('status.done')}</Badge>
  if (s === 'error') return <Badge variant="destructive" className="gap-1"><XCircle className="size-3" />{t('status.error')}</Badge>
  if (s === 'waiting') return <Badge variant="outline" className="gap-1 border-node-human text-node-human"><UserCheck className="size-3" />{t('status.waiting')}</Badge>
  if (s === 'cancelled') return <Badge variant="secondary" className="gap-1"><Square className="size-3" />{t('status.cancelled')}</Badge>
  return null
}

/** Tool node in Code mode while the server runs code without isolation (TASK-0056). */
function UnisolatedBadge() {
  const { t } = useTranslation(); const rt = useCodeRuntime()
  if (rt?.code_runtime !== 'subprocess') return null
  return <Tip tip={t('code.notIsolatedTip')}><Badge variant="warning" size="sm" className="mt-0.5" data-testid="node-unisolated"><ShieldAlert />{t('code.notIsolatedNode')}</Badge></Tip>
}

export function StudioNode({ data, type, selected }: NodeProps) {
  const d = data as any; const m = META[type!]; const I = m.icon
  return <div className="relative" data-status={d._status || undefined}>
    {type !== 'start' && <Handle type="target" position={Position.Left} />}
    <div className={cn(type === 'code' && 'border-node-code/60 border-dashed', 'rounded-xl border bg-card text-card-foreground shadow-sm px-3 py-2 min-w-44 transition-all',
      selected && 'ring-2 ring-ring', d._hl && 'ring-4 ring-primary/40 shadow-md', d._status === 'running' && 'border-warning ring-4 ring-warning/30',
      d._status === 'done' && 'border-success', d._status === 'waiting' && 'border-node-human ring-4 ring-node-human/30', d._status === 'error' && 'border-destructive')}>
    <div className="flex items-center gap-2">
      <div className={cn('rounded-md p-1.5', m.color)}><I className="size-4" /></div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{m.label}</div>
        <div className="text-sm font-medium truncate">{d.label}</div>
        {type === 'tool' && d.mode === 'code' && <UnisolatedBadge />}
        {type === 'tool' && d.mode === 'code' && d.language === 'typescript' && <Badge variant="outline" size="sm" className="font-mono" data-testid="node-language">TS</Badge>}
        {type === 'code' && <div className="flex gap-1 mt-0.5">{d.is_llm && <Badge variant="outline" size="sm"><Sparkles />LLM</Badge>}{d.kind && <span className="text-[9px] text-muted-foreground font-mono">{d.kind}</span>}</div>}
      </div>
    </div>
    {(d._status || d._dur != null) && <div className="mt-2 flex items-center justify-between gap-2">
      <StatusBadge s={d._status} />{d._dur != null && <span className="text-[10px] text-muted-foreground">{d._dur} ms</span>}</div>}
    </div>
    {type !== 'end' && <Handle type="source" position={Position.Right} />}
    {type === 'agent' && <HandoffHandle />}
  </div>
}

/** An Agent node's hand-off handle (TASK-0182): a link drawn from it to another Agent adds a hand-off target. */
function HandoffHandle() {
  const { t } = useTranslation()
  return <Handle type="source" id={HANDOFF_HANDLE} position={Position.Bottom} aria-label={t('handoff.handle')} data-testid="handoff-handle"
    style={{ background: 'var(--background)', borderStyle: 'dashed', borderColor: 'var(--node-agent)' }} />
}
export function Sticky({ id, data, selected }: NodeProps) {
  const { t } = useTranslation()
  const edit = useContext(CanvasEdit)
  const { setNodes } = useReactFlow()
  const box = useRef<HTMLTextAreaElement>(null)
  const text = String((data as any).text || '')
  useEffect(() => {
    if (!selected || !edit) return
    // Right-click selects the note while its menu is opening. Leave focus there.
    if (document.querySelector('[data-slot="context-menu-content"]')) return
    box.current?.focus()
  }, [selected, edit])
  return <div className={cn('w-52 rounded-sm border border-node-note/50 bg-node-note-muted text-card-foreground shadow-md', selected && 'ring-2 ring-node-note')}>
    <div className="h-2 rounded-t-sm bg-node-note/70" />
    <div className="px-3 py-2">
      {selected && edit
        ? <Textarea ref={box} id="note-text" rows={5} value={text} placeholder={t('editor.notePlaceholder')}
            onChange={e => setNodes(ns => ns.map(n => n.id === id ? { ...n, data: { ...n.data, text: e.target.value } } : n))}
            className="nodrag nowheel min-h-24 resize-none border-0 bg-transparent p-0 shadow-none ring-0 focus-visible:border-transparent focus-visible:ring-0 dark:bg-transparent md:text-sm" />
        : <div className={cn('min-h-24 whitespace-pre-wrap break-words text-sm', text.trim() ? '' : 'text-muted-foreground')}>{text.trim() ? text : t('editor.notePlaceholder')}</div>}
    </div>
  </div>
}
