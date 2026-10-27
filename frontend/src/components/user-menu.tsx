import { useNavigate } from 'react-router-dom'
import { CircleUser, LogOut, Settings, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { getUser, logout } from '@/lib/api'
import { useTranslation } from 'react-i18next'

export function UserMenu() {
  const { t } = useTranslation(); const u = getUser(); const nav = useNavigate()
  return <DropdownMenu>
    <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="rounded-full" id="user-menu">
      <Avatar className="size-7"><AvatarFallback className="text-xs">{(u?.email || '?')[0].toUpperCase()}</AvatarFallback></Avatar></Button></DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-56">
      <DropdownMenuLabel className="flex items-center gap-2 font-normal"><User className="size-4 shrink-0" /><span className="min-w-0 break-all">{u?.email}</span></DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuItem onClick={() => nav('/settings/profile')} id="profile-item"><CircleUser />{t('settings.nav.profile')}</DropdownMenuItem>
      <DropdownMenuItem onClick={() => nav('/settings/channels')} id="settings-item"><Settings />{t('settings.title')}</DropdownMenuItem>
      <DropdownMenuItem onClick={logout}><LogOut />{t('common.logout')}</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
}
