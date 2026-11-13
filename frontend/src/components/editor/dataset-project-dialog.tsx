import { useState } from 'react'
import { FileArchive } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ApiError } from '@/lib/api'
import { projectDownloadUrl, type ExportLanguage, type ProjectBindingChoice } from '@/lib/code-export'

export type DatasetBindingSummary = { name: string; operations: string[]; columns: { key: string }[] }

const BACKENDS = ['superstep', 'sqlite', 'postgresql'] as const

/** Per-binding backend and optional row snapshot for a project zip. The graph file stays the same. */
export function DatasetProjectDialog({ open, onOpenChange, wid, language, bindings, snapshotMaxRows, onError }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  wid: string
  language: ExportLanguage
  bindings: DatasetBindingSummary[]
  snapshotMaxRows: number
  onError: (message: string) => void
}) {
  const { t } = useTranslation()
  const [choices, setChoices] = useState<Record<string, ProjectBindingChoice>>(() => Object.fromEntries(bindings.map(binding => [binding.name, { name: binding.name, backend: 'superstep', snapshot: false }])))
  const [busy, setBusy] = useState(false)
  const update = (name: string, patch: Partial<ProjectBindingChoice>) => setChoices(current => ({ ...current, [name]: { ...current[name], ...patch } }))
  const download = async () => {
    setBusy(true)
    try {
      const response = await fetch(projectDownloadUrl(wid, language, Object.values(choices)), { headers: { 'X-Requested-With': 'studio' } })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new ApiError(body?.error ?? { code: 'HTTP_ERROR', message: `HTTP ${response.status}` }, response.status)
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') || '')?.[1] || 'project.zip'
      link.click()
      URL.revokeObjectURL(url)
      onOpenChange(false)
    } catch (error) {
      onError(error instanceof Error ? error.message : String(error))
    } finally {
      setBusy(false)
    }
  }
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="flex max-h-[90dvh] flex-col overflow-hidden sm:max-w-3xl" id="dataset-export-dialog">
      <DialogHeader>
        <DialogTitle>{t('codeView.exportTitle')}</DialogTitle>
        <DialogDescription>{t('codeView.exportIntro')}</DialogDescription>
      </DialogHeader>
      <DialogBody className="space-y-3">
        <p className="text-sm text-muted-foreground" id="dataset-export-standalone">{t('codeView.exportStandalone')}</p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('codeView.exportBinding')}</TableHead>
              <TableHead>{t('codeView.exportOperations')}</TableHead>
              <TableHead>{t('codeView.exportBackend')}</TableHead>
              <TableHead>{t('codeView.exportSnapshot')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {bindings.map(binding => {
              const choice = choices[binding.name]
              const standalone = choice?.backend === 'sqlite' || choice?.backend === 'postgresql'
              return <TableRow key={binding.name} id={`dataset-export-${binding.name}`}>
                <TableCell className="font-mono">{binding.name}</TableCell>
                <TableCell>{binding.operations.join(', ')}</TableCell>
                <TableCell>
                  <Select value={choice?.backend ?? 'superstep'} onValueChange={backend => update(binding.name, { backend, snapshot: backend === 'superstep' ? false : choice?.snapshot })}>
                    <SelectTrigger id={`dataset-export-backend-${binding.name}`} aria-label={t('codeView.exportBackend')}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {BACKENDS.map(backend => <SelectItem key={backend} value={backend} id={`dataset-export-backend-${binding.name}-${backend}`}>{t(`codeView.exportBackend${backend[0].toUpperCase()}${backend.slice(1)}`)}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Label className="gap-2 font-normal">
                    <Checkbox id={`dataset-export-snapshot-${binding.name}`} checked={!!choice?.snapshot} disabled={!standalone}
                      onCheckedChange={checked => update(binding.name, { snapshot: checked === true })} />
                    <span className="sr-only">{t('codeView.exportSnapshot')}</span>
                  </Label>
                </TableCell>
              </TableRow>
            })}
          </TableBody>
        </Table>
        <p className="text-sm text-muted-foreground" id="dataset-export-snapshot-hint">{t('codeView.exportSnapshotHint', { max: snapshotMaxRows })}</p>
      </DialogBody>
      <DialogFooter>
        <Button id="dataset-export-download" onClick={() => void download()} disabled={busy}><FileArchive />{t('codeView.exportDownload')}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
}
