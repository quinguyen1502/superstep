import { AtSign, CalendarClock, CalendarDays, CircleDot, Hash, ToggleLeft, Type } from 'lucide-react'
import type { DatasetKind } from '@/lib/datasets'

const FIELD_ICON = { text: Type, number: Hash, boolean: ToggleLeft, date: CalendarDays, datetime: CalendarClock, email: AtSign, select: CircleDot }

export function DatasetFieldIcon({ kind }: { kind: DatasetKind }) {
  const Icon = FIELD_ICON[kind]
  return <Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
}
