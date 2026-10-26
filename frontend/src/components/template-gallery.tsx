/** "New workflow" gallery (TASK-0025): blank canvas, built-in / personal / org templates, import & export of template files. */
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Download, FilePlus2, FlaskConical, Loader2, Trash2, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { TemplatePreview } from '@/components/template-preview'
import { api } from '@/lib/api'
import type { Issue } from '@/lib/i18n'
import { download, readTemplateFile, type Template } from '@/lib/templates'
import { useLoadWhen } from '@/lib/use-when'

type Props = { open: boolean; onOpenChange: (v: boolean) => void; onBlank: () => Promise<void> | void }

export function TemplateGallery({ open, onOpenChange, onBlank }: Props) {
  const { t } = useTranslation(); const nav = useNavigate()
  const [items, setItems] = useState<Template[] | null>(null)
  const [err, setErr] = useState(''); const [busy, setBusy] = useState<string | null>(null)
  const file = useRef<HTMLInputElement>(null)
  const confirmDel = useConfirmDelete()
  const load = () => api<Template[]>('/api/templates').then(setItems).catch(e => setErr(e.message))
  useLoadWhen(open, () => { setErr(''); load() })

  const run = async (key: string, f: () => Promise<void>) => {
    setBusy(key); setErr('')
    try { await f() } catch (e: any) { setErr(e.message === 'invalid-json' ? t('templates.invalidJson') : e.message) } finally { setBusy(null) }
  }
  const use = (tp: Template) => run(tp.id, async () => {
    const r = await api<{ id: string; errors?: string[]; issues?: Issue[] }>(`/api/templates/${tp.id}/use`, { method: 'POST', json: {} })
    nav(`/workflows/${r.id}`, { state: { errors: r.errors ?? [], issues: r.issues } })  // the editor lists what the new workflow still needs
  })
  const exp = (tp: Template) => run(`x-${tp.id}`, async () => download(tp.name, await api(`/api/templates/${tp.id}/export`)))
  const imp = (f?: File) => f && run('import', async () => { await api('/api/templates/import', { method: 'POST', json: { file: await readTemplateFile(f) } }); await load() })
  // built-ins show their name and description in the UI language (TASK-0064); saved and imported ones keep their author's text
  const text = (tp: Template) => tp.scope === 'builtin'
    ? { name: t(`templates.builtin.${tp.id}.name`, { defaultValue: tp.name }), description: t(`templates.builtin.${tp.id}.description`, { defaultValue: tp.description }) }
    : { name: tp.name, description: tp.description }
  const del = (tp: Template) => confirmDel.ask({ title: t('templates.deleteTitle'), name: tp.name, description: t('templates.deleteBody', { name: tp.name }),
    onConfirm: async () => { await api(`/api/templates/${tp.id}`, { method: 'DELETE' }); await load() } })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent id="template-gallery" className="sm:max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('templates.title')}</DialogTitle>
          <DialogDescription>{t('templates.subtitle')}</DialogDescription>
        </DialogHeader>
        <div className="flex justify-end">
          <input ref={file} id="tpl-import-file" type="file" accept=".json,application/json" className="hidden" onChange={e => { imp(e.target.files?.[0]); e.target.value = '' }} />
          <Button variant="outline" size="sm" id="tpl-import" disabled={busy === 'import'} onClick={() => file.current?.click()}>
            {busy === 'import' ? <Loader2 className="animate-spin" /> : <Upload />}{t('templates.import')}</Button>
        </div>
        {err && <Alert variant="destructive" id="tpl-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <button type="button" id="tpl-blank" disabled={!!busy} onClick={() => run('blank', async () => { await onBlank() })}
            className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-40">
            {busy === 'blank' ? <Loader2 className="animate-spin" /> : <FilePlus2 className="size-6" />}
            <span className="font-medium text-foreground">{t('templates.blank')}</span><span>{t('templates.blankHint')}</span>
          </button>
          {items === null && !err && Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="min-h-40" aria-busy={i === 0 || undefined} />)}
          {items?.map(tp => { const tx = text(tp); return (
            <div key={tp.id} data-testid="tpl-card" data-id={tp.id} className="group relative flex flex-col gap-2 rounded-lg border bg-card p-3 text-card-foreground">
              <button type="button" className="flex flex-col gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md" disabled={!!busy}
                onClick={() => use(tp)} aria-label={t('templates.useNamed', { name: tx.name })}>
                <TemplatePreview tpl={tp} />
                <div className="flex items-center gap-2"><span className="font-medium truncate">{tx.name}</span>
                  {busy === tp.id && <Loader2 className="size-4 animate-spin" />}
                  <Badge variant={tp.scope === 'builtin' ? 'secondary' : 'outline'} className="ml-auto shrink-0">{t(`templates.scope.${tp.scope}`)}</Badge></div>
                <p className="text-xs text-muted-foreground line-clamp-2 min-h-8">{tx.description || t('templates.noDescription')}</p>
              </button>
              <div className="flex items-center gap-1 justify-end">
                {tp.tests > 0 && <span className="mr-auto flex items-center gap-1 text-xs text-muted-foreground" data-testid="tpl-tests"><FlaskConical className="size-3.5" />{t('templates.tests', { count: tp.tests })}</span>}
                <Button variant="ghost" size="sm" data-testid="tpl-export" onClick={() => exp(tp)}><Download />{t('templates.export')}</Button>
                {tp.deletable && <Button variant="ghost" size="sm" data-testid="tpl-delete" className="text-destructive hover:text-destructive" onClick={() => del(tp)}><Trash2 />{t('common.delete')}</Button>}
              </div>
            </div>
          ) })}
        </div>
        {confirmDel.dialog}
      </DialogContent>
    </Dialog>
  )
}
