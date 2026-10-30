/** Settings (/settings/:section): left navigation, one URL per section. New sections (credentials, API tokens)
 *  need an entry in SECTIONS (sections.ts) and in COMPONENTS. */
import type { ComponentType } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LanguageSwitcher } from '@/components/language-switcher'
import { ThemeToggle } from '@/components/theme-toggle'
import { UserMenu } from '@/components/user-menu'
import { cn } from '@/lib/utils'
import { ProfileSection } from './ProfileSection'
import { TokensSection } from './TokensSection'
import { ChannelsSection } from './ChannelsSection'
import { AccountsSection } from './AccountsSection'
import { AuditSection } from './AuditSection'
import { KnowledgeSection } from './KnowledgeSection'
import { McpSection } from './McpSection'
import { UsersSection } from './UsersSection'
import { TeamsSection } from './TeamsSection'
import { ActivitySection } from './ActivitySection'
import { can, useMe } from '@/lib/rbac'
import { SECTIONS, type SectionId } from './sections'
import { Logo } from '@/components/logo'

const COMPONENTS: Record<SectionId, ComponentType> = {
  profile: ProfileSection, tokens: TokensSection, channels: ChannelsSection, accounts: AccountsSection, audit: AuditSection, knowledge: KnowledgeSection,
  mcp: McpSection, users: UsersSection, teams: TeamsSection, activity: ActivitySection,
}

export function SettingsPage() {
  const { t } = useTranslation(); const { section } = useParams(); const me = useMe()
  const visible = SECTIONS.filter(s => !s.permission || can(me, s.permission))
  const current = SECTIONS.find(s => s.id === section)
  // an unknown section, or one the role may not open (a bookmarked link): the first section instead
  if (!current || (me && current.permission && !can(me, current.permission))) return <Navigate to={`/settings/${SECTIONS[0].id}`} replace />
  const Component = COMPONENTS[current.id]
  return <div className="min-h-dvh bg-background">
    <header className="flex h-14 items-center gap-3 border-b px-4 md:px-6">
      <Link to="/workflows"><Logo /></Link>
      <div className="ml-auto flex items-center gap-1"><LanguageSwitcher /><ThemeToggle /><UserMenu /></div>
    </header>
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 md:flex-row md:p-6">
      <aside className="min-w-0 shrink-0 md:w-56">
        <Button variant="ghost" size="sm" asChild className="mb-3 -ml-2"><Link to="/workflows" id="settings-back"><ArrowLeft />{t('settings.back')}</Link></Button>
        <h1 className="mb-3 text-2xl font-semibold tracking-tight">{t('settings.title')}</h1>
        <nav className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-col md:overflow-visible md:px-0 md:pb-0" aria-label={t('settings.title')}>
          {visible.map(s => <Button key={s.id} variant="ghost" asChild className={cn('justify-start', s.id === current.id && 'bg-accent text-accent-foreground')}>
            <Link to={`/settings/${s.id}`} id={`settings-nav-${s.id}`} aria-current={s.id === current.id ? 'page' : undefined}><s.icon />{t(`settings.nav.${s.id}`)}</Link>
          </Button>)}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 space-y-4" id={`settings-${current.id}`}>
        <div><h2 className="text-xl font-semibold tracking-tight">{t(`settings.nav.${current.id}`)}</h2>
          <p className="text-sm text-muted-foreground">{t(`settings.intro.${current.id}`)}</p></div>
        <Component />
      </main>
    </div>
  </div>
}
