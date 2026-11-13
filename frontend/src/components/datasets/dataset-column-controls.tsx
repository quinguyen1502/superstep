import { useState, type PointerEvent } from 'react'
import { Columns3, Eye, EyeOff, GripVertical } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import type { DatasetColumn } from '@/lib/datasets'
import { cn } from '@/lib/utils'
import { DatasetFieldIcon } from './dataset-field-icon'

export function DatasetUniqueBadge() {
  const { t } = useTranslation()
  return <Badge variant="outline" size="sm">{t('dataset.unique')}</Badge>
}

type ColumnDrag = { from: number; to: number; startY: number; offset: number; rowStep: number }

function dropIndex(event: PointerEvent<HTMLButtonElement>, list: HTMLElement) {
  const bounds = list.getBoundingClientRect()
  const { clientX: x, clientY: y } = event
  if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) return -1
  return Array.from(list.children).findLastIndex(item => item.getBoundingClientRect().top <= y)
}

export function DatasetColumnControls({ columns, visibleKeys, disabled, onVisibility, onMove }: {
  columns: DatasetColumn[]
  visibleKeys: Set<string>
  disabled: boolean
  onVisibility: (key: string, visible: boolean) => void
  onMove: (from: string, to: string) => void
}) {
  const { t } = useTranslation()
  const [drag, setDrag] = useState<ColumnDrag | null>(null)
  return <Popover>
    <PopoverTrigger asChild>
      <Button variant={visibleKeys.size < columns.length ? 'secondary' : 'outline'}
        aria-label={t('dataset.visibleColumns')} disabled={disabled || !columns.length}>
        <Columns3 /><span className="hidden sm:inline">{t('dataset.visibleColumns')}</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent align="start" aria-label={t('dataset.visibleColumns')} className="w-64 max-w-[calc(100vw-1.5rem)]">
      <ul className="grid max-h-[50dvh] gap-1 overflow-y-auto p-1">
        {columns.map((column, index) => {
          const visible = visibleKeys.has(column.key)
          const dragging = drag?.from === index
          let offset = 0
          if (drag) {
            if (dragging) offset = drag.offset
            else if (index > drag.from && index <= drag.to) offset = -drag.rowStep
            else if (index < drag.from && index >= drag.to && drag.to !== -1) offset = drag.rowStep
          }
          return <li key={column.key} data-dataset-column={column.key} className="min-w-0">
            <div data-dragging={dragging || undefined}
              className={cn('relative flex min-w-0 items-center gap-1 rounded-md', dragging
                ? 'z-10 bg-popover shadow-md ring-1 ring-ring'
                : 'motion-safe:transition-transform motion-safe:duration-150')}
              style={{ transform: offset ? `translateY(${offset}px)` : undefined }}>
              <Button type="button" variant="ghost" size="icon-sm" className="cursor-grab touch-none active:cursor-grabbing"
                aria-label={t('dataset.reorderColumn', { name: column.label })}
                onPointerDown={event => {
                  if (event.button !== 0) return
                  const row = event.currentTarget.closest('li')!
                  const list = row.parentElement!
                  event.currentTarget.setPointerCapture(event.pointerId)
                  setDrag({ from: index, to: index, startY: event.clientY, offset: 0,
                    rowStep: row.offsetHeight + (parseFloat(getComputedStyle(list).rowGap) || 0) })
                }}
                onPointerMove={event => {
                  if (!event.currentTarget.hasPointerCapture(event.pointerId)) return
                  const to = dropIndex(event, event.currentTarget.closest('ul')!)
                  const y = event.clientY
                  setDrag(current => current && { ...current, to, offset: y - current.startY })
                }}
                onPointerUp={event => {
                  if (!event.currentTarget.hasPointerCapture(event.pointerId)) return
                  const destination = columns[dropIndex(event, event.currentTarget.closest('ul')!)]
                  if (destination) onMove(column.key, destination.key)
                  setDrag(null)
                }}
                onLostPointerCapture={() => setDrag(null)}
                onKeyDown={event => {
                  const next = event.key === 'ArrowUp' ? columns[index - 1] : event.key === 'ArrowDown' ? columns[index + 1] : undefined
                  if (!next) return
                  event.preventDefault()
                  onMove(column.key, next.key)
                }}><GripVertical /></Button>
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                <DatasetFieldIcon kind={column.kind} />
                <span className="truncate font-medium" title={column.label}>{column.label}</span>
                {column.unique && <DatasetUniqueBadge />}
                {column.required && <span className="text-destructive" title={t('dataset.required')}>*</span>}
              </div>
              <Button type="button" variant="ghost" size="icon-sm" aria-label={t('dataset.showColumn', { name: column.label })}
                aria-pressed={visible} disabled={visible && visibleKeys.size === 1}
                onClick={() => onVisibility(column.key, !visible)}>{visible ? <Eye /> : <EyeOff />}</Button>
            </div>
          </li>
        })}
      </ul>
    </PopoverContent>
  </Popover>
}
