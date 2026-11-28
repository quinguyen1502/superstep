import { useEffect, useState, type FormEvent } from 'react'
import { ChevronLeft, ChevronRight, Search, Table2, TriangleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ApiError } from '@/lib/api'
import type { DatasetSharePreview } from '@/lib/dataset-shares'
import { displayValue } from '@/lib/datasets'
import { cn } from '@/lib/utils'
import { errorText } from '@/lib/i18n'
import { DatasetFieldIcon } from './dataset-field-icon'

export function DatasetShareError({ error }: { error: unknown }) {
  return <Alert variant="destructive"><TriangleAlert /><AlertDescription>
    {error instanceof ApiError ? error.message : errorText({ code: 'INTERNAL_ERROR' })}
  </AlertDescription></Alert>
}

type Query = { search: string; offsets: number[] }
type Result = { query: Query; page: DatasetSharePreview } | { query: Query; error: unknown }

export type LoadDatasetShare = (search: string, offset: number, signal: AbortSignal) => Promise<DatasetSharePreview>

export function DatasetShareTable({ load, publicPage, onLoaded }: {
  load: LoadDatasetShare
  publicPage?: boolean
  onLoaded?: (ready: boolean) => void
}) {
  const { t } = useTranslation()
  const [query, setQuery] = useState<Query>({ search: '', offsets: [0] })
  const [search, setSearch] = useState('')
  const [result, setResult] = useState<Result>()
  const [view, setView] = useState<DatasetSharePreview['view']>()
  const offset = query.offsets.at(-1) ?? 0
  const current = result?.query === query ? result : undefined
  const page = current && 'page' in current ? current.page : undefined
  const failure = current && 'error' in current ? current.error : undefined
  const lastPage = result && 'page' in result ? result.page : undefined
  const unavailable = publicPage && failure instanceof ApiError && failure.code === 'DATASET_SHARE_NOT_FOUND'

  useEffect(() => {
    const controller = new AbortController()
    void load(query.search, offset, controller.signal).then(page => {
      if (controller.signal.aborted) return
      setView(page.view)
      setResult({ query, page })
      onLoaded?.(true)
    }, error => {
      if (controller.signal.aborted) return
      setResult({ query, error })
      onLoaded?.(false)
    })
    return () => controller.abort()
  }, [load, offset, onLoaded, query])

  function find(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setQuery({ search: search.trim(), offsets: [0] })
  }

  if (unavailable) {
    return <Empty className="border">
      <EmptyHeader>
        <EmptyMedia variant="icon"><Table2 /></EmptyMedia>
        <h1 className="text-lg font-medium">{t('dataset.share.unavailable')}</h1>
        <EmptyDescription>{t('dataset.share.unavailableHelp')}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  }

  return <div className="grid min-w-0 gap-3">
    {publicPage && <h1 className="wrap-anywhere text-xl font-semibold">{view?.name ?? t('dataset.share.sharedDataset')}</h1>}
    {view?.searchable && <form className="flex min-w-0 flex-wrap items-center gap-2" onSubmit={find}>
      <Input type="search" className="min-w-32 flex-1 sm:max-w-xs" maxLength={120}
        aria-label={t('dataset.searchRows')} placeholder={t('dataset.searchRows')}
        value={search} onChange={event => setSearch(event.target.value)} />
      <Button variant="outline" type="submit"><Search />{t('dataset.share.search')}</Button>
    </form>}
    {!current && <p role="status" className="text-sm text-muted-foreground">{t('common.loading')}</p>}
    {current && 'error' in current && <div className="grid gap-2">
      <DatasetShareError error={failure} />
      <Button className="justify-self-start" variant="outline" onClick={() => setQuery({ ...query })}>{t('common.retry')}</Button>
    </div>}
    {page && <div role="region" aria-label={t('dataset.share.rows')} tabIndex={0}
      className={cn(
        'min-w-0 overflow-auto rounded-md border focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&>[data-slot=table-container]]:overflow-visible',
        publicPage ? 'max-h-[65dvh]' : 'max-h-[52dvh]',
      )}>
      <Table aria-label={t('dataset.share.rows')}>
        <TableHeader className="sticky top-0 bg-muted">
          <TableRow>{page.view.columns.map(column => <TableHead key={column.key} scope="col">
            <span className="flex items-center gap-2"><DatasetFieldIcon kind={column.kind} />{column.label}</span>
          </TableHead>)}</TableRow>
        </TableHeader>
        <TableBody>
          {page.items.map((row, index) => <TableRow key={index}>
            {page.view.columns.map(column => <TableCell key={column.key} className="px-2 align-top">
              <div className="max-h-36 max-w-sm min-w-24 overflow-auto whitespace-pre-wrap wrap-anywhere">
                {displayValue(row[column.key] ?? null, t('dataset.valueTrue'), t('dataset.valueFalse'), column.kind)}
              </div>
            </TableCell>)}
          </TableRow>)}
        </TableBody>
      </Table>
      {!page.items.length && <Empty>
        <EmptyHeader>
          <EmptyTitle>{t(query.search ? 'dataset.share.noMatches' : 'dataset.share.noRows')}</EmptyTitle>
        </EmptyHeader>
      </Empty>}
    </div>}
    {lastPage && (query.offsets.length > 1 || lastPage.next_offset !== null) && <nav aria-label={t('dataset.share.pagination')}
      className="flex items-center justify-end gap-2">
      <Button type="button" variant="outline" size="icon-sm" className="aria-disabled:opacity-50" aria-label={t('dataset.previousPage')} aria-disabled={!page || query.offsets.length === 1}
        onClick={() => {
          if (page && query.offsets.length > 1) setQuery({ ...query, offsets: query.offsets.slice(0, -1) })
        }}><ChevronLeft /></Button>
      <span role="status" className="text-sm text-muted-foreground">{t('dataset.share.page', { number: query.offsets.length })}</span>
      <Button type="button" variant="outline" size="icon-sm" className="aria-disabled:opacity-50" aria-label={t('dataset.nextPage')} aria-disabled={page?.next_offset == null}
        onClick={() => {
          if (page?.next_offset != null) setQuery({ ...query, offsets: [...query.offsets, page.next_offset] })
        }}><ChevronRight /></Button>
    </nav>}
  </div>
}
