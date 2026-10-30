/** Thumbs on a finished answer (TASK-0163, TASK-0164, REQ-0075). `onRate` is absent when the builder is only reading
 *  a visitor's chat: the mark and the comment stay, and nothing is written. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FlaskConical, ThumbsDown, ThumbsUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tip } from '@/components/tip'
import type { ChatTurn } from '@/lib/chat'

const COMMENT_MAX = 1000

export function ChatRatingBar({ turn, onRate, onSaveTest }: {
  turn: ChatTurn
  onRate?: (turnId: string, value: 'up' | 'down' | null, comment?: string) => void
  onSaveTest?: (runId: string) => void
}) {
  const { t } = useTranslation()
  const rating = turn.rating ?? null
  const [box, setBox] = useState(false)
  const [text, setText] = useState(rating?.comment ?? '')
  const set = (value: 'up' | 'down') => {
    if (!onRate) return
    if (rating?.value === value) { onRate(turn.id, null); setBox(false); return }
    onRate(turn.id, value)
    setBox(value === 'down')
    if (value === 'up') setText('')
  }
  const send = () => { onRate?.(turn.id, 'down', text.trim()); setBox(false) }
  const gone = turn.run_exists === false
  const save = onSaveTest && rating && turn.run_id ? <Tip tip={gone ? t('chat.rating.runGone') : t('tests.saveFromRun')}>
    <Button size="icon-sm" variant="ghost" data-testid="chat-save-test" aria-label={t('tests.saveFromRun')} disabled={gone}
      onClick={() => onSaveTest(turn.run_id!)}><FlaskConical /></Button></Tip> : null
  if (!onRate) return <div className="flex flex-wrap items-center gap-2" data-testid="chat-rating-mark" data-value={rating?.value ?? ''}>
    {rating && <span className="text-xs text-muted-foreground">{t(rating.value === 'up' ? 'chat.rating.up' : 'chat.rating.down')}</span>}
    {rating?.comment ? <p className="w-full text-sm text-muted-foreground" data-testid="chat-rating-comment">{rating.comment}</p> : null}
    {save}
  </div>
  return <div className="flex flex-col gap-2">
    <div className="flex flex-wrap items-center gap-1">
      <Tip tip={rating?.value === 'up' ? t('chat.rating.remove') : t('chat.rating.up')}>
        <Button size="icon-sm" variant={rating?.value === 'up' ? 'secondary' : 'ghost'} data-testid="chat-rate-up" aria-pressed={rating?.value === 'up'}
          aria-label={t('chat.rating.up')} onClick={() => set('up')}><ThumbsUp /></Button></Tip>
      <Tip tip={rating?.value === 'down' ? t('chat.rating.remove') : t('chat.rating.down')}>
        <Button size="icon-sm" variant={rating?.value === 'down' ? 'secondary' : 'ghost'} data-testid="chat-rate-down" aria-pressed={rating?.value === 'down'}
          aria-label={t('chat.rating.down')} onClick={() => set('down')}><ThumbsDown /></Button></Tip>
      {save}
    </div>
    {rating?.comment && !box && <p className="text-sm text-muted-foreground" data-testid="chat-rating-comment">{rating.comment}</p>}
    {box && <form className="flex flex-col gap-2" onSubmit={e => { e.preventDefault(); send() }}>
      <label className="text-xs text-muted-foreground" htmlFor={`chat-rating-${turn.id}`}>{t('chat.rating.comment')}</label>
      <div className="flex items-center gap-2">
        <Input id={`chat-rating-${turn.id}`} value={text} maxLength={COMMENT_MAX} placeholder={t('chat.rating.commentPlaceholder')}
          data-testid="chat-rating-input" onChange={e => setText(e.target.value)} />
        <Button type="submit" size="sm" variant="secondary" data-testid="chat-rating-send">{t('chat.rating.sendComment')}</Button>
      </div>
    </form>}
  </div>
}
