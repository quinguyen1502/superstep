import { Languages, Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useEffect } from 'react'
import { LANGS } from '@/lib/i18n'
import { setLanguage, syncLanguage } from '@/lib/language'
import { Tip } from '@/components/tip'

export function LanguageSwitcher({ localOnly = false }: { localOnly?: boolean }) {
  const { t, i18n } = useTranslation()
  useEffect(() => { if (!localOnly) syncLanguage() }, [localOnly])
  return <DropdownMenu>
    <Tip tip={t('common.language')}><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" id="lang-switch" aria-label={t('common.language')}><Languages /></Button></DropdownMenuTrigger></Tip>
    <DropdownMenuContent align="end">
      {LANGS.map(l => <DropdownMenuItem key={l} data-lang={l} onClick={() => {
        if (localOnly) void i18n.changeLanguage(l)
        else setLanguage(l)
      }}>
        <Check className={i18n.resolvedLanguage === l ? '' : 'invisible'} />{t(`lang.${l}`)}</DropdownMenuItem>)}
    </DropdownMenuContent>
  </DropdownMenu>
}
