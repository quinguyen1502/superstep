/** The one delete confirmation (UI rule, docs/ui-conventions.md, DEC-0025): the destructive button stays disabled until the
 * user types the item's exact name. Confirmation is UI-only — the API stays a plain DELETE. `children` is the
 * reasons/warnings slot; errors thrown by `onConfirm` are shown inside the dialog. */
import { useState, type ReactNode } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { Loader2, Trash2, TriangleAlert } from 'lucide-react'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog.js'
import { Button } from '../ui/button.js'
import { Input } from '../ui/input.js'
import { Label } from '../ui/label.js'

export type ConfirmDeleteOptions = {
  title: string
  idPrefix?: string
  name: string                 // what the user must type
  description?: ReactNode
  confirmLabel?: string
  children?: ReactNode         // reasons / warnings / extra fields
  disabled?: boolean           // extra condition (e.g. a required field in the slot)
  onConfirm: () => Promise<unknown> | unknown
}

export function ConfirmDeleteDialog({ open, onOpenChange, title, name, description, confirmLabel, children, disabled, onConfirm, idPrefix = 'confirm-delete' }:
  ConfirmDeleteOptions & { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { t } = useTranslation()
  const [typed, setTyped] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const change = (o: boolean) => { if (busy) return; if (!o) { setTyped(''); setErr('') } onOpenChange(o) }
  const go = async () => {
    setBusy(true); setErr('')
    try { await onConfirm(); setTyped(''); onOpenChange(false) } catch (e: any) { setErr(e?.message || String(e)) } finally { setBusy(false) }
  }
  const match = typed === name
  return <AlertDialog open={open} onOpenChange={change}>
    <AlertDialogContent id={idPrefix}>
      <AlertDialogHeader className="text-left"><AlertDialogTitle className="flex items-start gap-2 wrap-break-word"><TriangleAlert className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden />{title}</AlertDialogTitle>
        <AlertDialogDescription className="text-left wrap-break-word">{description ?? t('confirmDelete.irreversible')}</AlertDialogDescription></AlertDialogHeader>
      {children}
      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-input`} className="block wrap-break-word font-normal"><span className="leading-relaxed">
          <Trans i18nKey="confirmDelete.typeToConfirm" values={{ name }} components={{ b: <code className="box-decoration-clone rounded-md border bg-muted px-1.5 py-0.5 font-mono font-semibold text-foreground" /> }} /></span></Label>
        <Input id={`${idPrefix}-input`} autoComplete="off" spellCheck={false} placeholder={t('confirmDelete.placeholder')} value={typed}
          onChange={e => setTyped(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && match && !disabled && !busy) go() }} aria-invalid={!!typed && !match} />
      </div>
      {err && <p role="alert" id={`${idPrefix}-error`} className="text-sm text-destructive">{err}</p>}
      <AlertDialogFooter><AlertDialogCancel disabled={busy}>{t('confirmDelete.cancel')}</AlertDialogCancel>
        <Button id={`${idPrefix}-submit`} variant="destructive" disabled={!match || disabled || busy} onClick={go}>
          {busy ? <Loader2 className="animate-spin" /> : <Trash2 />}{confirmLabel ?? t('confirmDelete.delete')}</Button></AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
}
