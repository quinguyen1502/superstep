/** Settings navigation (ids, icons, permissions) without the section components, so the command palette can list
 *  the pages without loading them (TASK-0039: Settings is a lazy route). Components are mapped in SettingsPage. */
import { CircleUser, Database, History, MessageSquareShare, Plug, ScrollText, UserCheck, Users, UsersRound, type LucideIcon } from 'lucide-react'

export const SECTION_IDS = ['profile', 'channels', 'accounts', 'audit', 'knowledge', 'mcp', 'users', 'teams', 'activity'] as const
export type SectionId = typeof SECTION_IDS[number]
export type Section = { id: SectionId; icon: LucideIcon; permission?: string }
export const SECTIONS: Section[] = [
  { id: 'profile', icon: CircleUser },
  { id: 'channels', icon: MessageSquareShare },
  { id: 'accounts', icon: UserCheck },
  { id: 'audit', icon: ScrollText },
  { id: 'knowledge', icon: Database, permission: 'resources.manage' },  // a viewer owns none and cannot create one
  { id: 'mcp', icon: Plug },
  { id: 'users', icon: Users, permission: 'users.manage' },
  { id: 'teams', icon: UsersRound, permission: 'users.manage' },
  { id: 'activity', icon: History, permission: 'users.manage' },
]
