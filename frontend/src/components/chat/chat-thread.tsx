/** A chat's thread (TASK-0085), built as the shadcn Chat pattern: Message Scroller (autoScroll, a messageId on every
 *  item, the person's turns as scroll anchors), the person's turns as muted Bubbles, the agent's as Trace steps then
 *  Markdown with a Message footer of actions (Message pattern), an Empty state, and the scroll button. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowDown, Check, Copy, LoaderCircle, MessageCircleDashed } from 'lucide-react'
import { MessageScroller, MessageScrollerButton, MessageScrollerContent, MessageScrollerItem, MessageScrollerProvider, MessageScrollerViewport } from '@/components/ui/message-scroller'
import { Message, MessageContent, MessageFooter } from '@/components/ui/message'
import { Bubble, BubbleContent } from '@/components/ui/bubble'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Trace, TraceIcon, TraceLine, TraceTitle } from '@/components/ui/trace'
import { errorText } from '@/lib/i18n'
import { liveReply, liveSteps, waitingTurn, type ChatStep, type ChatTurn, type StepsMode } from '@/lib/chat'
import type { RunEvent, Trace as RunTrace } from '@/lib/trace'
import { ChatMarkdown } from './chat-markdown'
import { ChatRatingBar } from './chat-rating'
import { ChatSteps } from './chat-steps'
import { ChatConfirmation } from './chat-confirmation'

/** The Message pattern's action: a ghost icon button with a tooltip, its label as the aria-label. */
function MessageAction({ label, children, ...props }: React.ComponentProps<typeof Button> & { label: string }) {
  return <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-sm" aria-label={label} {...props}>{children}</Button></TooltipTrigger>
    <TooltipContent><p>{label}</p></TooltipContent></Tooltip>
}

function CopyAction({ text }: { text: string }) {
  const { t } = useTranslation(); const [copied, setCopied] = useState(false)
  useEffect(() => { if (!copied) return; const id = setTimeout(() => setCopied(false), 2000); return () => clearTimeout(id) }, [copied])
  return <MessageAction label={copied ? t('chat.copied') : t('chat.copy')} data-testid="chat-copy"
    onClick={() => navigator.clipboard.writeText(text).then(() => setCopied(true)).catch(() => {})}>{copied ? <Check /> : <Copy />}</MessageAction>
}

function Answer({ text, steps, mode, status, code, live, turn, onRate, onSaveTest, children }: {
  text: string; steps?: ChatStep[]; mode: StepsMode; status?: string | null; code?: string | null; live?: string
  turn?: ChatTurn; onRate?: (turnId: string, value: 'up' | 'down' | null, comment?: string) => void
  onSaveTest?: (runId: string) => void; children?: React.ReactNode }) {
  const { t } = useTranslation(); const failed = status && !['ok', 'waiting'].includes(status)
  const rateable = !!turn && (status === 'ok' || status === 'error')
  const showRating = rateable && (!!onRate || !!turn.rating || !!onSaveTest)
  return <Message data-testid="chat-answer" data-status={status ?? 'running'}>
    <MessageContent className="gap-3">
      <ChatSteps steps={steps ?? []} mode={mode} />
      {live && <Trace><TraceLine status="running" id="chat-thinking"><TraceIcon><LoaderCircle className="animate-spin" /></TraceIcon><TraceTitle>{live}</TraceTitle></TraceLine></Trace>}
      {failed ? <Bubble variant="destructive"><BubbleContent data-testid="chat-error">{code ? errorText({ code, message: text }) : text || t('chat.failed')}</BubbleContent></Bubble>
        : text ? <ChatMarkdown text={text} /> : null}
      {children}
      {(status === 'ok' && text) || showRating ? <MessageFooter className="flex-wrap px-0">
        {status === 'ok' && text && <CopyAction text={text} />}
        {showRating && turn && <ChatRatingBar turn={turn} onRate={onRate} onSaveTest={onSaveTest} />}
      </MessageFooter> : null}
    </MessageContent>
  </Message>
}

const Mine = ({ text }: { text: string }) => <Message align="end" data-testid="chat-mine">
  <MessageContent><Bubble align="end" variant="muted"><BubbleContent className="whitespace-pre-wrap">{text}</BubbleContent></Bubble></MessageContent></Message>

/** `replyField`: the field whose tokens are the answer; none on the public page, whose socket sends only those (TASK-0142).
 *  `empty`: what an empty chat shows instead of the default (the page's intro and suggestions). */
export function ChatThread({ turns, mode, replyField, events, trace, pending, running, onAnswer, onRate, onSaveTest, empty }: {
  turns: ChatTurn[]; mode: StepsMode; replyField?: string; events: RunEvent[]; trace: RunTrace; pending: string | null; running: boolean
  onAnswer?: (runId: string, response: string) => void
  onRate?: (turnId: string, value: 'up' | 'down' | null, comment?: string) => void
  onSaveTest?: (runId: string) => void; empty?: React.ReactNode }) {
  const { t } = useTranslation(); const wait = waitingTurn(turns); const reply = liveReply(events, replyField)
  const live = liveSteps(trace.spans, mode)
  if (!turns.length && pending === null && empty) return <>{empty}</>
  if (!turns.length && pending === null) return <Empty className="flex-1" id="chat-empty">
    <EmptyHeader><EmptyMedia variant="icon"><MessageCircleDashed /></EmptyMedia>
      <EmptyTitle>{t('chat.emptyTitle')}</EmptyTitle><EmptyDescription>{t('chat.empty')}</EmptyDescription></EmptyHeader></Empty>
  return <MessageScrollerProvider autoScroll><MessageScroller className="min-h-0 flex-1">
    <MessageScrollerViewport><MessageScrollerContent /* ui-class-ok: reading padding of the message column, a layout container, not a control */ aria-busy={running} className="mx-auto max-w-3xl gap-6 px-4 py-4" id="chat-thread">
      {turns.map(x => <MessageScrollerItem key={x.id} messageId={x.id} scrollAnchor={x.role === 'user'}>
        {x.role === 'user' ? <Mine text={x.text} />
          : <Answer text={x.text} steps={x.steps} mode={mode} status={x.status} code={x.code} turn={x} onRate={onRate} onSaveTest={onSaveTest}>
              {x === wait && !running && onAnswer && <ChatConfirmation turn={x} busy={running} onAnswer={r => onAnswer(x.run_id!, r)} />}</Answer>}
      </MessageScrollerItem>)}
      {pending !== null && <MessageScrollerItem messageId="pending-user" scrollAnchor><Mine text={pending} /></MessageScrollerItem>}
      {pending !== null && <MessageScrollerItem messageId="pending-answer">
        <Answer text={reply} steps={live} mode={mode} live={!running ? t('chat.saving') : !live.some(s => s.status === 'running') ? t('chat.thinking') : undefined} />
      </MessageScrollerItem>}
    </MessageScrollerContent></MessageScrollerViewport>
    <MessageScrollerButton><ArrowDown /><span className="sr-only">{t('chat.scrollEnd')}</span></MessageScrollerButton>
  </MessageScroller></MessageScrollerProvider>
}
