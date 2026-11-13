import type { Ref } from 'react'
import { Columns3, Eye, KeyRound, MoreHorizontal, Pencil, Settings, Trash2, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

type MenuAction = { label: string; onSelect: () => void; disabled?: boolean }

export function DatasetActionsMenu({ label, remove, edit, schema, view, access, actions, triggerRef, triggerId, size = 'icon-sm', disabled, note }: {
  label: string
  remove?: MenuAction
  edit?: MenuAction
  schema?: MenuAction
  view?: MenuAction
  access?: MenuAction
  actions?: (MenuAction & { icon: LucideIcon })[]
  triggerId?: string
  triggerRef?: Ref<HTMLButtonElement>
  size?: 'icon' | 'icon-sm'
  disabled?: boolean
  note?: string
}) {
  return <DropdownMenu modal={false}>
    <DropdownMenuTrigger asChild>
      <Button ref={triggerRef} id={triggerId} variant="ghost" size={size} aria-label={label} disabled={disabled}>{schema ? <Settings /> : <MoreHorizontal />}</Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-max max-w-(--radix-dropdown-menu-content-available-width)">
      {schema && <DropdownMenuItem onSelect={schema.onSelect}><Columns3 />{schema.label}</DropdownMenuItem>}
      {view && <DropdownMenuItem onSelect={view.onSelect}><Eye />{view.label}</DropdownMenuItem>}
      {edit && <DropdownMenuItem disabled={edit.disabled} onSelect={edit.onSelect}><Pencil />{edit.label}</DropdownMenuItem>}
      {access && <DropdownMenuItem disabled={access.disabled} onSelect={access.onSelect}><KeyRound />{access.label}</DropdownMenuItem>}
      {actions?.map(({ icon: Icon, label: actionLabel, onSelect, disabled: off }) => <DropdownMenuItem key={actionLabel} disabled={off} onSelect={onSelect}><Icon />{actionLabel}</DropdownMenuItem>)}
      {note && <p className="max-w-64 px-2 py-1.5 text-xs text-muted-foreground">{note}</p>}
      {remove && <DropdownMenuItem variant="destructive" disabled={remove.disabled} onSelect={remove.onSelect}><Trash2 /><span className="wrap-anywhere">{remove.label}</span></DropdownMenuItem>}
    </DropdownMenuContent>
  </DropdownMenu>
}
