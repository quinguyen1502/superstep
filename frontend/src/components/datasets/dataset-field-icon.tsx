import { AtSign, CalendarClock, CalendarDays, Hash, SquareFunction, Link2, ListChecks, ListCollapse, TextAlignStart, ToggleLeft, Type } from 'lucide-react'
import type { DatasetKind } from '@/lib/datasets'

const FIELD_ICON = { text: Type, number: Hash, boolean: ToggleLeft, date: CalendarDays, datetime: CalendarClock, email: AtSign, select: ListCollapse, long_text: TextAlignStart, url: Link2, created_time: CalendarClock, updated_time: CalendarClock, multi_select: ListChecks, auto_number: Hash, relation: Link2, formula: SquareFunction }

export function DatasetFieldIcon({ kind }: { kind: DatasetKind | 'formula' }) {
  const Icon = FIELD_ICON[kind]
  return <Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
}
