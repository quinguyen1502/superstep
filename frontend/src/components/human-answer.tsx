import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

/** Approve, Reject or a text reply to a waiting Human node: the editor's Human panel and each Approvals inbox row
 * . `ids` gives the controls the editor's element ids; inbox rows use data-testid only. */
export function HumanAnswer({ onRespond, busy = false, ids = false }: { onRespond: (response: string) => void; busy?: boolean; ids?: boolean }) {
  const { t } = useTranslation(); const [text, setText] = useState('')
  const id = (k: string) => ids ? `human-${k}` : undefined
  return <div className="space-y-2">
    <Textarea id={id('response')} data-testid="answer-text" aria-label={t('human.response')} rows={2} className="text-xs bg-background" placeholder={t('human.placeholder')}
      value={text} onChange={e => setText(e.target.value)} />
    <div className="flex flex-wrap gap-2">
      <Button size="sm" id={id('approve')} data-testid="answer-approve" disabled={busy} onClick={() => onRespond('approved')}><Check />{t('human.approve')}</Button>
      <Button size="sm" variant="outline" id={id('reject')} data-testid="answer-reject" disabled={busy} onClick={() => onRespond('rejected')}><X />{t('human.reject')}</Button>
      <Button size="sm" variant="secondary" id={id('submit')} data-testid="answer-submit" disabled={busy || !text.trim()} onClick={() => onRespond(text.trim())}><Send />{t('human.submit')}</Button>
    </div>
  </div>
}
