import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle } from 'lucide-react'
import { AlertDialog as Dialog, AlertDialogContent as DialogContent, AlertDialogDescription as DialogDescription, AlertDialogFooter as DialogFooter, AlertDialogHeader as DialogHeader, AlertDialogTitle as DialogTitle } from '../ui/alert-dialog.js'
import { Alert, AlertDescription } from '../ui/alert.js'
import { Textarea } from '../ui/textarea.js'
import { Label } from '../ui/label.js'
import { Button } from '../ui/button.js'
import { errorText, type ApiErrorBody } from '../lib/errors.js'
import { MAX_MESSAGE, type ChatTurn } from '../lib/chat.js'

/** Editing is a confirmed new execution; cancelling never changes the saved message. */
export function ChatEditDialog({ turn, onClose, onEdit }: { turn: ChatTurn | null; onClose: () => void; onEdit: (turn: string, text: string, operationId: string) => Promise<unknown> }) {
  const { t, i18n } = useTranslation(), id = useId()
  const [text, setText] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const operation = useRef('')
  useEffect(() => { setText(turn?.text ?? ''); setError(''); operation.current = turn ? crypto.randomUUID() : '' }, [turn?.id])
  const save = async () => {
    if (!turn || busy) return
    setBusy(true); setError('')
    try { await onEdit(turn.id, text, operation.current); onClose() }
    catch (e) {
      const failure = e as ApiErrorBody | undefined
      setError(failure?.code && i18n.exists(`errors.${failure.code}`) ? errorText(failure, i18n) : t('chat.toolkit.requestFailed'))
    }
    finally { setBusy(false) }
  }
  return <Dialog open={!!turn} onOpenChange={open => { if (!open && !busy) onClose() }}><DialogContent>
    <DialogHeader><DialogTitle>{t('chat.edit.title')}</DialogTitle><DialogDescription>{t('chat.edit.description')}</DialogDescription></DialogHeader>
    <Label htmlFor={id}>{t('chat.edit.message')}</Label>
    <Textarea id={id} value={text} maxLength={MAX_MESSAGE} disabled={busy} onChange={e => { setText(e.target.value); operation.current = crypto.randomUUID() }} autoFocus />
    <Alert variant="warning"><AlertCircle /><AlertDescription>{t('chat.edit.rerunWarning')}</AlertDescription></Alert>
    {error && <Alert variant="destructive"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
    <DialogFooter><Button variant="outline" disabled={busy} onClick={onClose}>{t('confirmDelete.cancel')}</Button>
      <Button disabled={busy || text.trim() === turn?.text.trim() || (!text.trim() && !turn?.attachments?.length)} onClick={() => void save()}>{t('chat.edit.saveRun')}</Button></DialogFooter>
  </DialogContent></Dialog>
}
