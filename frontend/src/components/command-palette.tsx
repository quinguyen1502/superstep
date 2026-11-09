/** App-wide command palette: Mod+K. Shows page commands (editor actions, add node, jump to node),
 * workflows and navigation; fuzzy search by cmdk; registry shortcuts shown next to actions. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { LayoutList, Plus, Settings, UserCheck, Workflow as WorkflowIcon } from 'lucide-react'
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Kbd } from '@/components/shortcut-cheatsheet'
import { api, signedIn } from '@/lib/api'
import { grouped, onPaletteRequest, searchValue, usePaletteCommands, type PaletteCommand } from '@/lib/palette'
import { can, loadMe, type Me } from '@/lib/rbac'
import { SHORTCUTS } from '@/lib/shortcuts'
import { useShortcuts } from '@/lib/use-shortcuts'
import { SECTIONS } from '@/pages/settings/sections'
import { useOnChange } from '@/lib/use-when'

type W = { id: string; name: string }

export function CommandPalette() {
  const { t } = useTranslation(); const nav = useNavigate(); const loc = useLocation(); const [me, setMe] = useState<Me | null>(null)
  const [open, setOpen] = useState(false); const [wfs, setWfs] = useState<W[]>([])
  const page = usePaletteCommands()
  useShortcuts({ palette: () => { if (!signedIn() || loc.pathname === '/login' || loc.pathname === '/register') return false; setOpen(true) } })
  useEffect(() => { if (open) { api<W[]>('/api/workflows').then(setWfs).catch(() => setWfs([])); loadMe().then(setMe).catch(() => setMe(null)) } }, [open])  // mounted outside the routes: load on open
  useOnChange(loc.pathname, () => setOpen(false))  // navigating closes the palette
  useEffect(() => onPaletteRequest(() => setOpen(true)), [])

  const current = loc.pathname.startsWith('/workflows/') ? loc.pathname.split('/')[2] : null
  const cmds: PaletteCommand[] = [
    ...page,
    ...wfs.filter(w => w.id !== current).slice(0, 50).map(w => ({ id: `wf:${w.id}`, group: 'workflows' as const, label: w.name, icon: WorkflowIcon, run: () => nav(`/workflows/${w.id}`) })),
    { id: 'nav:workflows', group: 'navigation', label: t('palette.goWorkflows'), icon: LayoutList, run: () => nav('/workflows') },
    { id: 'nav:approvals', group: 'navigation', label: t('inbox.title'), icon: UserCheck, keywords: ['inbox', 'approve', 'pending'], run: () => nav('/approvals') },
    ...(can(me, 'workflows.create') ? [{ id: 'nav:new', group: 'navigation' as const, label: t('common.newWorkflow'), icon: Plus, keywords: ['template', 'create'], run: () => nav('/workflows?new=1') }] : []),
    ...SECTIONS.filter(s => !s.permission || can(me, s.permission)).map(s => ({ id: `nav:settings:${s.id}`, group: 'navigation' as const, label: `${t('settings.title')} › ${t(`settings.nav.${s.id}`)}`, icon: s.icon ?? Settings, run: () => nav(`/settings/${s.id}`) })),
  ]
  const exec = (c: PaletteCommand) => { setOpen(false); window.setTimeout(c.run, 0) }  // let the dialog close (focus returns) first
  const keyOf = (id?: string) => id ? SHORTCUTS.find(s => s.id === id)?.keys[0] : undefined

  return (
    <CommandDialog open={open} onOpenChange={setOpen} title={t('palette.title')} description={t('palette.description')}>
      <CommandInput data-testid="palette-input" placeholder={t('palette.placeholder')} />
      <CommandList data-testid="command-palette">
        <CommandEmpty>{t('palette.empty')}</CommandEmpty>
        {grouped(cmds).map(([g, items]) => <CommandGroup key={g} heading={t(`palette.groups.${g}`)}>
          {items.map(c => { const I = c.icon; const k = keyOf(c.shortcut)
            return <CommandItem key={c.id} value={searchValue(c)} disabled={c.disabled} onSelect={() => exec(c)} data-testid="palette-item" data-id={c.id}>
              {I ? <I /> : <span className="size-4 shrink-0" aria-hidden="true" />}<span className="truncate">{c.label}</span>{c.hint && <span className="truncate text-xs text-muted-foreground">{c.hint}</span>}
              {k && <span className="ml-auto"><Kbd combo={k} /></span>}
            </CommandItem> })}
        </CommandGroup>)}
      </CommandList>
    </CommandDialog>
  )
}
