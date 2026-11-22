import { useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Table2 } from 'lucide-react'
import { DatasetShareTable } from '@/components/datasets/dataset-share-table'
import { LanguageSwitcher } from '@/components/language-switcher'
import { ThemeToggle } from '@/components/theme-toggle'
import { ApiError, api } from '@/lib/api'
import {
  DATASET_SHARE_API, DATASET_SHARE_HEADER, DATASET_SHARE_PAGE_SIZE, datasetShareToken,
  type DatasetShareRows, type DatasetShareView,
} from '@/lib/dataset-shares'
import { useSystemTheme } from '@/lib/theme'

function PublicDatasetReader({ token }: { token: string }) {
  const savedView = useRef<DatasetShareView>(null)
  const load = useCallback(async (search: string, offset: number, signal: AbortSignal) => {
    if (!token) throw new ApiError({ code: 'DATASET_SHARE_NOT_FOUND' }, 404)
    const options = {
      headers: { [DATASET_SHARE_HEADER]: token }, signal, credentials: 'omit', cache: 'no-store',
      redirect: 'error', referrerPolicy: 'no-referrer',
    } as const
    const params = new URLSearchParams({ limit: String(DATASET_SHARE_PAGE_SIZE), offset: String(offset) })
    if (search) params.set('search', search)
    const [view, rows] = await Promise.all([
      savedView.current ?? api<DatasetShareView>(DATASET_SHARE_API, options),
      api<DatasetShareRows>(`${DATASET_SHARE_API}/rows?${params}`, options),
    ])
    if (!signal.aborted) savedView.current = view
    return { view, ...rows }
  }, [token])

  return <DatasetShareTable load={load} publicPage />
}

export function PublicDatasetPage() {
  const { t } = useTranslation()
  const token = datasetShareToken(useLocation().hash)
  useSystemTheme()

  return <div className="min-h-dvh bg-background text-foreground">
    <title>{t('dataset.share.sharedDataset')}</title>
    <meta name="robots" content="noindex" />
    <meta name="referrer" content="no-referrer" />
    <header className="border-b">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
        <span className="flex items-center gap-2 text-sm font-medium"><Table2 className="size-4" aria-hidden="true" />{t('dataset.share.readOnly')}</span>
        <div className="flex items-center gap-1"><LanguageSwitcher localOnly /><ThemeToggle /></div>
      </div>
    </header>
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <PublicDatasetReader key={token} token={token} />
    </main>
  </div>
}
