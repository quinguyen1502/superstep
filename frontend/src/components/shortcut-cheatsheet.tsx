/** Keyboard shortcut cheat sheet: every registry entry, grouped, with platform-specific key caps. */
import { Fragment, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { GROUPS, SHORTCUTS, isMac, keyCaps, type Shortcut } from '@/lib/shortcuts'

export function Kbd({ combo }: { combo: string }) {
  const mac = isMac()
  return <span className="inline-flex items-center gap-0.5">{keyCaps(combo, mac).map((k, i) =>
    <kbd key={i} className="pointer-events-none inline-flex h-5 min-w-5 items-center justify-center rounded border bg-muted px-1 font-sans text-[11px] leading-none font-medium text-muted-foreground">{k}</kbd>)}</span>
}

export function ShortcutKeys({ s }: { s: Shortcut }) {
  const { t } = useTranslation()
  return <span className="flex items-center gap-1.5">{s.keys.map((c, i) => <Fragment key={c}>{i > 0 && <span className="text-xs text-muted-foreground">{t('shortcuts.or')}</span>}<Kbd combo={c} /></Fragment>)}</span>
}

export function ShortcutCheatsheet({ open, onOpenChange, list = SHORTCUTS, intro, trigger }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  list?: Shortcut[]
  intro?: string
  trigger?: ReactNode
}) {
  const { t } = useTranslation()
  return <Dialog open={open} onOpenChange={onOpenChange}>
    {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-2xl" id="shortcut-cheatsheet">
      <DialogHeader><DialogTitle>{t('shortcuts.title')}</DialogTitle><DialogDescription>{intro ?? t('shortcuts.intro')}</DialogDescription></DialogHeader>
      <DialogBody className="grid gap-5 sm:grid-cols-2">{GROUPS.map(g => {
        const items = list.filter(s => s.group === g); if (!items.length) return null
        return <section key={g} className="space-y-2" aria-labelledby={`sc-${g}`}>
          <h3 id={`sc-${g}`} className="text-xs font-semibold uppercase text-muted-foreground">{t(`shortcuts.groups.${g}`)}</h3>
          <ul className="space-y-1.5">{items.map(s => <li key={s.id} className="flex min-h-6 items-center justify-between gap-3 text-sm" data-testid="shortcut-row" data-id={s.id}>
            <span className="min-w-0">{t(s.labelKey ?? `shortcuts.actions.${s.id}`)}</span><ShortcutKeys s={s} /></li>)}</ul>
        </section> })}</DialogBody>
    </DialogContent>
  </Dialog>
}
