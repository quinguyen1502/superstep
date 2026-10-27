import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Maximize2, Minimize2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tip } from '@/components/tip'
import { cn } from '@/lib/utils'
import { ChatPanel } from './chat-panel'

/** Chat as its own panel beside the editor (TASK-0085), opened from the header or Shift+C. Fullscreen turns the same
 * element into a full-viewport overlay, so the conversation, the draft and the scroll position stay; Esc leaves
 * fullscreen; × closes the panel. The narrow panel picks sessions from a Select, fullscreen shows the session list. */

export function ChatSidePanel({ wid, canConfigure, canEdit, dirty, onClose }: { wid: string; canConfigure: boolean; canEdit: boolean; dirty: boolean; onClose: () => void }) {
  const { t } = useTranslation(); const [full, setFull] = useState(false)
  useEffect(() => { if (!full) return; const k = (e: KeyboardEvent) => { if (e.key === 'Escape') setFull(false) }; addEventListener('keydown', k); return () => removeEventListener('keydown', k) }, [full])
  const actions = <>
    <Tip tip={full ? t('chat.exitFullscreen') : t('chat.fullscreen')}><Button size="icon-sm" variant="ghost" id="chat-fullscreen" aria-label={full ? t('chat.exitFullscreen') : t('chat.fullscreen')} aria-pressed={full} onClick={() => setFull(f => !f)}>{full ? <Minimize2 /> : <Maximize2 />}</Button></Tip>
    <Tip tip={t('common.close')}><Button size="icon-sm" variant="ghost" id="chat-close" aria-label={t('common.close')} onClick={onClose}><X /></Button></Tip></>
  return <div id="chat-side" data-fullscreen={full || undefined} className={cn('flex h-full min-h-0 flex-col border-l bg-background', full && 'fixed inset-0 z-50 border-0')}>
    <ChatPanel wid={wid} active canConfigure={canConfigure} canEdit={canEdit} dirty={dirty} compact={!full} actions={actions} />
  </div>
}
