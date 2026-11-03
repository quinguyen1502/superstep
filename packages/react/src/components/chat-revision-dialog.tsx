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

/** A revision is a confirmed new execution; cancelling never changes the saved message. */
export function ChatRevisionDialog({ turn, action = 'edit', onClose, onConfirm }: { turn: ChatTurn | null; action?: 'edit' | 'regenerate'; onClose: () => void; onConfirm: (turn: string, text: string, operationId: string) => Promise<unknown> }) {
  const { t, i18n } = useTranslation(), id = useId()
  const [text, setText] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const operation = useRef('')
  useEffect(() => { setText(turn?.text ?? ''); setError(''); operation.current = turn ? crypto.randomUUID() : '' }, [turn?.id, action])
  const save = async () => {
    if (!turn || busy) return
    setBusy(true); setError('')
    try { await onConfirm(turn.id, text, operation.current); onClose() }
    catch (e) {
      const failure = e as ApiErrorBody | undefined
      setError(failure?.code && i18n.exists(`errors.${failure.code}`) ? errorText(failure, i18n) : t('chat.toolkit.requestFailed'))
    }
    finally { setBusy(false) }
  }
  return <Dialog open={!!turn} onOpenChange={open => { if (!open && !busy) onClose() }}><DialogContent>
    <DialogHeader><DialogTitle>{t(`chat.${action}.title`)}</DialogTitle><DialogDescription>{t(`chat.${action}.description`)}</DialogDescription></DialogHeader>
    {action === 'edit' && <><Label htmlFor={id}>{t('chat.edit.message')}</Label>
    <Textarea id={id} value={text} maxLength={MAX_MESSAGE} disabled={busy} onChange={e => { setText(e.target.value); operation.current = crypto.randomUUID() }} autoFocus /></>}
    <Alert variant="warning"><AlertCircle /><AlertDescription>{t('chat.edit.rerunWarning')}</AlertDescription></Alert>
    {error && <Alert variant="destructive"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert>}
    <DialogFooter><Button variant="outline" disabled={busy} onClick={onClose}>{t('confirmDelete.cancel')}</Button>
      <Button disabled={busy || (action === 'edit' && (text.trim() === turn?.text.trim() || (!text.trim() && !turn?.attachments?.length)))} onClick={() => void save()}>{t(action === 'edit' ? 'chat.edit.saveRun' : 'chat.regenerate.run')}</Button></DialogFooter>
  </DialogContent></Dialog>
}
