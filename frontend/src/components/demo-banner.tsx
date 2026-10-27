import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Info, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useDemoMode } from '@/lib/demo'
import { cn } from '@/lib/utils'

const KEY = 'studio.demoBannerHidden'

/** A small notice on every page of the public demo: data resets, the first load is slow, nothing is saved. */
export function DemoBanner() {
  const { t } = useTranslation(); const demo = useDemoMode()
  const [hidden, setHidden] = useState(() => sessionStorage.getItem(KEY) === '1')
  // the phone editor has a 56px tab bar at the bottom (TASK-0121): sit above it so the tabs stay tappable
  const editor = /^\/workflows\/[^/]+/.test(useLocation().pathname)
  if (!demo || hidden) return null
  return <div className={cn('pointer-events-none fixed inset-x-0 bottom-3 z-50 flex justify-center px-3', editor && 'max-md:bottom-17')}>
    <Alert variant="warning" id="demo-banner" className="pointer-events-auto flex max-w-xl items-start gap-2 pr-2 shadow-md">
      <Info /><AlertDescription className="text-xs">{t('demo.banner')}</AlertDescription>
      <Button variant="ghost" size="icon-xs" className="shrink-0" aria-label={t('demo.hide')} id="demo-banner-hide"
              onClick={() => { sessionStorage.setItem(KEY, '1'); setHidden(true) }}><X /></Button>
    </Alert>
  </div>
}
