import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

let cached: Promise<string | null> | undefined

/** One health read per page load. The footer still renders when this fails. */
function loadVersion(): Promise<string | null> {
  cached ??= api<{ version?: unknown }>('/api/health')
    .then(h => (typeof h.version === 'string' && h.version.trim() ? h.version.trim() : null))
    .catch(() => null)
  return cached
}

/** MIT copyright plus the running server version from GET /api/health. */
export function AppMeta({ className }: { className?: string }) {
  const { t } = useTranslation()
  const [version, setVersion] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    loadVersion().then(v => { if (live) setVersion(v) })
    return () => { live = false }
  }, [])
  const year = new Date().getFullYear()
  return <footer className={cn('px-4 py-3 text-center text-xs text-muted-foreground', className)} data-testid="app-meta">
    <p>
      <span>{t('meta.copyright', { year })}</span>
      {version && <span> · {t('meta.version', { version })}</span>}
    </p>
  </footer>
}
