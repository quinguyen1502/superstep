import { useState } from 'react'
import { ConfirmDeleteDialog, type ConfirmDeleteOptions } from './confirm-delete-dialog.js'

/** `const del = useConfirmDelete(idPrefix?: string); del.ask({...}); return <>{del.dialog}</>` — one dialog per screen, opened on demand. */
export function useConfirmDelete(idPrefix?: string, onClose?: () => void) {
  const [opts, setOpts] = useState<ConfirmDeleteOptions | null>(null)
  const close = () => { setOpts(null); onClose?.() }
  return {
    ask: (o: ConfirmDeleteOptions) => setOpts(o),
    close,
    dialog: opts && <ConfirmDeleteDialog idPrefix={idPrefix} open onOpenChange={o => { if (!o) close() }} {...opts} />,
  }
}
