import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { ChevronDown, Link2, RotateCw, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { datasetShareUrl, type DatasetShare, type DatasetShareInput } from '@/lib/dataset-shares'
import { datasetUrl, type Dataset, type DatasetPage } from '@/lib/datasets'
import { DatasetFilterBuilder } from './dataset-filter-builder'
import { CreateDatasetShare, DatasetShareLink } from './dataset-share-dialogs'
import { DatasetShareError } from './dataset-share-table'

type ShareDialog = { kind: 'create' } | { kind: 'rotate'; share: DatasetShare } | { kind: 'link'; url: string; rotated: boolean }

export function DatasetShareManager({ dataset }: { dataset: Dataset }) {
  const { t } = useTranslation()
  const path = `${datasetUrl(dataset.id)}/shares`
  const [page, setPage] = useState<DatasetPage<DatasetShare>>()
  const [listError, setListError] = useState<unknown>()
  const [request, setRequest] = useState({ offset: 0 })
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState<ShareDialog>()
  const [dialogError, setDialogError] = useState<unknown>()
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const dialogTrigger = useRef<HTMLButtonElement>(null)
  const createTrigger = useRef<HTMLButtonElement>(null)
  const revokeTrigger = useRef<HTMLButtonElement>(null)
  const confirm = useConfirmDelete('dataset-share-revoke', () => {
    requestAnimationFrame(() => {
      const trigger = revokeTrigger.current
      if (trigger?.isConnected) trigger.focus()
      else createTrigger.current?.focus()
    })
  })

  useEffect(() => {
    const controller = new AbortController()
    void api<DatasetPage<DatasetShare>>(`${path}?offset=${request.offset}`, { signal: controller.signal }).then(next => {
      if (controller.signal.aborted) return
      setPage(previous => request.offset === 0 || !previous ? next
        : { ...next, items: [...previous.items, ...next.items.filter(share => !previous.items.some(item => item.id === share.id))] })
      setLoading(false)
    }, error => {
      if (controller.signal.aborted) return
      setListError(error)
      setLoading(false)
    })
    return () => controller.abort()
  }, [path, request])

  function load(offset = 0) {
    setListError(undefined)
    setLoading(true)
    setRequest({ offset })
  }

  function open(event: MouseEvent<HTMLButtonElement>, next: ShareDialog) {
    dialogTrigger.current = event.currentTarget
    setDialogError(undefined)
    setNotice('')
    setDialog(next)
  }

  function close() {
    if (!saving) setDialog(undefined)
  }

  async function issue(share?: DatasetShare, input?: DatasetShareInput) {
    setSaving(true)
    setDialogError(undefined)
    try {
      const endpoint = share ? `${path}/${encodeURIComponent(share.id)}/rotate` : path
      const result = await api<{ token: string }>(endpoint, { method: 'POST', json: input })
      setDialog({ kind: 'link', url: datasetShareUrl(result.token), rotated: !!share })
      load()
    } catch (error) {
      setDialogError(error)
    } finally {
      setSaving(false)
    }
  }

  function revoke(event: MouseEvent<HTMLButtonElement>, share: DatasetShare) {
    revokeTrigger.current = event.currentTarget
    setNotice('')
    confirm.ask({
      name: share.name,
      title: t('dataset.share.revoke'),
      description: t('dataset.share.revokeHelp'),
      confirmLabel: t('dataset.share.revokeAction'),
      onConfirm: async () => {
        await api(`${path}/${encodeURIComponent(share.id)}`, { method: 'DELETE' })
        setPage(previous => previous && ({ ...previous, items: previous.items.filter(item => item.id !== share.id) }))
        setNotice('dataset.share.revoked')
        load()
      },
    })
  }

  return <section className="grid min-w-0 gap-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 className="font-medium">{t('dataset.share.heading')}</h3>
        <p className="text-sm text-muted-foreground">{t('dataset.share.help')}</p>
      </div>
      <Button ref={createTrigger} variant="outline" onClick={event => open(event, { kind: 'create' })}>
        <Link2 />{t('dataset.share.create')}
      </Button>
    </div>
    {notice && <p role="status" className="text-sm text-muted-foreground">{t(notice)}</p>}
    {loading && <p role="status" className="text-sm text-muted-foreground">{t('common.loading')}</p>}
    {!!listError && <div className="grid gap-2">
      <DatasetShareError error={listError} />
      <Button variant="outline" className="justify-self-start" onClick={() => load(request.offset)}>{t('common.retry')}</Button>
    </div>}
    {!loading && !listError && page?.items.length === 0 && <p className="text-sm text-muted-foreground">{t('dataset.share.none')}</p>}
    {page?.items.map(share => <Collapsible key={share.id} className="grid min-w-0 gap-2 rounded-md border p-2">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="wrap-anywhere font-medium">{share.name}</p>
          <p className="wrap-anywhere text-xs text-muted-foreground">
            {share.fields.map(field => dataset.columns.find(column => column.key === field)?.label ?? field).join(', ')}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {!share.available && <Badge variant="warning">{t('dataset.share.unavailable')}</Badge>}
          {share.filter_tree && <CollapsibleTrigger asChild><Button variant="ghost" size="sm">
            {t('dataset.share.filter')}<ChevronDown />
          </Button></CollapsibleTrigger>}
          <Button variant="ghost" size="icon-sm" aria-label={t('dataset.share.rotateNamed', { name: share.name })}
            title={t('dataset.share.rotate')} disabled={!share.available} onClick={event => open(event, { kind: 'rotate', share })}><RotateCw /></Button>
          <Button variant="ghost" size="icon-sm" className="text-destructive" aria-label={t('dataset.share.revokeNamed', { name: share.name })}
            title={t('dataset.share.revoke')} onClick={event => revoke(event, share)}><Trash2 /></Button>
        </div>
      </div>
      {share.filter_tree && <CollapsibleContent className="min-w-0 border-t pt-2">
        <DatasetFilterBuilder tree={share.filter_tree} columns={dataset.columns} disabled onChange={() => {}} />
      </CollapsibleContent>}
    </Collapsible>)}
    {page?.next_offset != null && <Button variant="outline" className="justify-self-start" disabled={loading || !!listError}
      onClick={() => { if (page.next_offset !== null) load(page.next_offset) }}>{t('dataset.share.more')}</Button>}
    <Dialog open={!!dialog} onOpenChange={next => { if (!next) close() }}>
      {dialog && <DialogContent className="flex max-h-[calc(100dvh-2rem)] min-w-0 flex-col sm:max-w-2xl"
        onCloseAutoFocus={event => {
          event.preventDefault()
          const trigger = dialogTrigger.current
          if (trigger?.isConnected && !trigger.disabled) trigger.focus()
          else createTrigger.current?.focus()
        }}>
        {dialog.kind === 'create' && <CreateDatasetShare dataset={dataset} path={path} saving={saving} error={dialogError}
          onClearError={() => setDialogError(undefined)} onCreate={input => { void issue(undefined, input) }} onClose={close} />}
        {dialog.kind === 'rotate' && <>
          <DialogHeader>
            <DialogTitle>{t('dataset.share.rotate')}</DialogTitle>
            <DialogDescription>{t('dataset.share.rotateHelp', { name: dialog.share.name })}</DialogDescription>
          </DialogHeader>
          {!!dialogError && <DialogBody><DatasetShareError error={dialogError} /></DialogBody>}
          <DialogFooter>
            <Button variant="outline" disabled={saving} onClick={close}>{t('common.cancel')}</Button>
            <Button disabled={saving} onClick={() => { void issue(dialog.share) }}><RotateCw />{t('dataset.share.rotate')}</Button>
          </DialogFooter>
        </>}
        {dialog.kind === 'link' && <DatasetShareLink url={dialog.url} rotated={dialog.rotated} />}
      </DialogContent>}
    </Dialog>
    {confirm.dialog}
  </section>
}
