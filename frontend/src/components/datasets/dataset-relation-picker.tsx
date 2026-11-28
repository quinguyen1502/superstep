import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { errorText } from '@/lib/i18n'
import { type Dataset, type DatasetPage } from '@/lib/datasets'
import { readRelationChoices, RELATION_PAGE_SIZE, type RelationChoice } from './use-dataset-relations'

export function DatasetRelationPicker({ dataset, field, value, busy, onPick, children }: {
  dataset: Pick<Dataset, 'id' | 'revision'>
  field: string
  value: string | null
  busy?: boolean
  onPick: (choice: RelationChoice) => void
  children?: ReactNode
}) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<{ query: string; page?: DatasetPage<RelationChoice>; error?: string }>()
  const { id, revision } = dataset
  const query = JSON.stringify([id, revision, field, search, offset, retry])
  const current = result?.query === query ? result : undefined
  const nextOffset = current?.page?.next_offset
  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void readRelationChoices({ id, revision }, field, { search: search.trim(), offset }, controller.signal)
        .then(page => { if (!controller.signal.aborted) setResult({ query, page }) })
        .catch(error => {
          if (!controller.signal.aborted) setResult({ query, error: error instanceof Error ? error.message : errorText({ code: 'INTERNAL_ERROR' }) })
        })
    }, search ? 200 : 0)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [field, id, offset, query, revision, search])

  return <>
    <Command shouldFilter={false} label={t('dataset.relation.search')} className="min-h-0">
      <CommandInput aria-label={t('dataset.relation.search')} placeholder={t('dataset.relation.search')} maxLength={120}
        value={search} onValueChange={next => { setSearch(next); setOffset(0) }} disabled={busy} />
      <CommandList className="min-h-0">
        {!current && <p role="status" className="px-3 py-2 text-muted-foreground">{t('common.loading')}</p>}
        {current?.page && <CommandEmpty>{t('dataset.relation.noRows')}</CommandEmpty>}
        <CommandGroup>
          {current?.page?.items.map(choice => <CommandItem key={choice.id} value={choice.id} disabled={busy}
            onSelect={() => onPick(choice)}>
            <span className="min-w-0 flex-1">
              <span className="block truncate">{choice.label?.trim() ? choice.label : choice.id}</span>
              {!!choice.label?.trim() && <span className="block truncate font-mono text-xs text-muted-foreground">{choice.id}</span>}
            </span>
            {choice.id === value && <Check aria-label={t('dataset.relation.current')} />}
          </CommandItem>)}
        </CommandGroup>
      </CommandList>
    </Command>
    {current?.error && <div className="space-y-2">
      <Alert variant="destructive"><AlertDescription>{current.error}</AlertDescription></Alert>
      <Button type="button" variant="outline" size="sm" onClick={() => setRetry(count => count + 1)}>{t('common.retry')}</Button>
    </div>}
    {(children || offset > 0 || nextOffset != null) && <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
      {children}
      <div className="ms-auto flex gap-2">
        {offset > 0 && <Button type="button" variant="outline" size="icon-sm" disabled={busy} aria-label={t('dataset.relation.previousPage')}
          onClick={() => setOffset(Math.max(0, offset - RELATION_PAGE_SIZE))}><ChevronLeft /></Button>}
        {nextOffset != null && <Button type="button" variant="outline" size="icon-sm" disabled={busy} aria-label={t('dataset.relation.nextPage')}
          onClick={() => setOffset(nextOffset)}><ChevronRight /></Button>}
      </div>
    </div>}
  </>
}

export function DatasetRelationFilterValue({ dataset, id, label, field, value, disabled, onChange }: {
  dataset: Dataset; id: string; label: string; field: string; value: string | null; disabled: boolean; onChange: (id: string) => void
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [result, setResult] = useState<{ key: string; label: string }>()
  const key = JSON.stringify([dataset.id, dataset.revision, field, value])
  useEffect(() => {
    if (!value || result?.key === key) return
    const controller = new AbortController()
    void readRelationChoices(dataset, field, { rowIds: [value] }, controller.signal)
      .then(page => {
        const choice = page.items.find(item => item.id === value)
        if (!controller.signal.aborted) setResult({ key, label: choice ? choice.label?.trim() ? choice.label : choice.id : t('dataset.relation.unavailable') })
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ key, label: t('dataset.relation.unavailable') })
      })
    return () => controller.abort()
  }, [dataset, field, key, result?.key, t, value])
  const display = result?.key === key ? result.label : t(value ? 'common.loading' : 'dataset.relation.chooseRow')
  return <Popover open={open} onOpenChange={setOpen}>
    <PopoverTrigger asChild>
      <Button id={id} type="button" className="w-full justify-between" variant="outline" disabled={disabled} aria-label={label}>
        <span className="truncate">{display}</span><ChevronDown />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="start" aria-label={t('dataset.relation.chooseRow')} className="max-h-(--radix-popover-content-available-height) max-w-[calc(100vw-1.5rem)] overflow-hidden">
      <DatasetRelationPicker dataset={dataset} field={field} value={value} onPick={choice => {
        onChange(choice.id)
        setOpen(false)
      }} />
    </PopoverContent>
  </Popover>
}
