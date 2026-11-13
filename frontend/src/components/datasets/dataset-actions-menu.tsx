import type { Ref } from 'react'
import { Columns3, Eye, KeyRound, MoreHorizontal, Pencil, Settings, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

type MenuAction = { label: string; onSelect: () => void }

export function DatasetActionsMenu({ label, remove, edit, schema, view, access, triggerRef, triggerId, size = 'icon-sm', disabled }: {
  label: string
  remove?: MenuAction
  edit?: MenuAction
  schema?: MenuAction
  view?: MenuAction
  access?: MenuAction
  triggerId?: string
  triggerRef?: Ref<HTMLButtonElement>
  size?: 'icon' | 'icon-sm'
  disabled?: boolean
}) {
  return <DropdownMenu modal={false}>
    <DropdownMenuTrigger asChild>
      <Button ref={triggerRef} id={triggerId} variant="ghost" size={size} aria-label={label} disabled={disabled}>{schema ? <Settings /> : <MoreHorizontal />}</Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-max max-w-(--radix-dropdown-menu-content-available-width)">
      {schema && <DropdownMenuItem onSelect={schema.onSelect}><Columns3 />{schema.label}</DropdownMenuItem>}
      {view && <DropdownMenuItem onSelect={view.onSelect}><Eye />{view.label}</DropdownMenuItem>}
      {edit && <DropdownMenuItem onSelect={edit.onSelect}><Pencil />{edit.label}</DropdownMenuItem>}
      {access && <DropdownMenuItem onSelect={access.onSelect}><KeyRound />{access.label}</DropdownMenuItem>}
      {remove && <DropdownMenuItem variant="destructive" onSelect={remove.onSelect}><Trash2 /><span className="wrap-anywhere">{remove.label}</span></DropdownMenuItem>}
    </DropdownMenuContent>
  </DropdownMenu>
}
