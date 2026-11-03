import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { RefreshCw, SquarePen, AlertCircle } from 'lucide-react'
import { ChatThread } from '../components/chat-thread.js'
import { ChatComposer } from '../components/chat-composer.js'
import { ChatRatingBar } from '../components/chat-rating.js'
import { ChatLogo, ChatIllustration } from '../components/chat-logo.js'
import { ChatMarkdown } from '../components/chat-markdown.js'
import { useConfirmDelete } from '../components/use-confirm-delete.js'
import { Button } from '../ui/button.js'
import { Alert, AlertDescription } from '../ui/alert.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select.js'
import { errorText, type ApiErrorBody } from '../lib/errors.js'
import type { ChatTurn, ChatAttachment } from '../lib/chat.js'
import { useChat, type UseChatOptions, type ChatController } from './use-chat.js'
import { ChatProvider, useChatController, type ChatTheme, type ChatMessages } from './provider.js'
import { QuestionCard } from './question-card.js'
import type { ChatTurn as SDKChatTurn } from '@superstep/sdk/chat'

const attachments = (files: readonly import('@superstep/sdk/chat').ChatAttachment[]): ChatAttachment[] => files.flatMap(f => f.kind === 'image' || f.kind === 'document' ? [{ ...f, kind: f.kind }] : [])

function useRating(chat: ChatController) {
  const { t, i18n } = useTranslation(), id = useId(), confirmation = useConfirmDelete(`ss-rating-${id}`)
  useEffect(() => { confirmation.close() }, [chat.resourceKey, chat.selectionKey])
  const onRate = (turn: string, value: 'up' | 'down' | null, comment?: string) => {
    if (value === null) confirmation.ask({ title: t('chat.toolkit.removeRatingTitle'), name: t('chat.toolkit.ratingName'), onConfirm: () => chat.rate(turn, null).catch(error => { throw new Error(errorText(error, i18n)) }) })
    else void chat.rate(turn, value, comment).catch(() => {})
  }
  return { onRate, dialog: confirmation.dialog }
}
export function Rating({ turn, chat: explicit }: { turn: SDKChatTurn; chat?: ChatController }) {
  const chat = useChatController(explicit), rating = useRating(chat)
  return <><ChatRatingBar turn={{ id: turn.id, role: turn.role, text: turn.text, created: turn.created, rating: turn.rating, run_id: turn.run_id, run_exists: turn.run_exists ?? undefined, inherited: turn.inherited }} onRate={chat.busy ? undefined : rating.onRate} />{rating.dialog}</>
}
export function MessageList({ chat: explicit, empty: customEmpty }: { chat?: ChatController; empty?: ReactNode }) {
  const chat = useChatController(explicit), { t } = useTranslation(), rating = useRating(chat)
  const empty = chat.page && <div className="mx-auto flex max-w-3xl flex-1 flex-col items-center justify-center gap-4 px-4 py-6 text-center">
    <ChatIllustration /><h2 className="text-lg font-semibold">{chat.page.title || t('chat.page.title')}</h2>
    {chat.page.intro ? <ChatMarkdown text={chat.page.intro} /> : <p className="text-sm text-muted-foreground">{t('chat.empty')}</p>}
    {!!chat.page.suggestions?.length && <div className="flex flex-wrap justify-center gap-2">{chat.page.suggestions.map(value => <Button key={value} variant="outline" disabled={chat.busy} onClick={() => void chat.send(value).catch(() => {})}>{value}</Button>)}</div>}
  </div>
  return <><ChatThread turns={[...chat.turns] as ChatTurn[]} mode={chat.page?.steps_mode ?? 'labels'} events={chat.text ? [{ type: 'node_token', node: 'answer', delta: chat.text }] : []} trace={{ spans: [] }}
    pending={chat.pending} pendingFiles={attachments(chat.pendingFiles)} running={chat.busy} replyPending={chat.status === 'streaming' && chat.pending === null} onRate={chat.busy ? undefined : rating.onRate}
    onEdit={chat.edit} onSource={chat.sourceSessionId ? () => void chat.load(chat.sourceSessionId!).catch(() => {}) : undefined}
    files={{ download: chat.download }} empty={chat.loading ? <p role="status" className="p-4 text-sm text-muted-foreground">{t('chat.toolkit.loading')}</p> : customEmpty ?? empty} />{rating.dialog}</>
}
export function Composer({ chat: explicit, idPrefix }: { chat?: ChatController; idPrefix?: string }) {
  const chat = useChatController(explicit), { t, i18n } = useTranslation(), id = useId(), pending = useRef<((value: boolean) => void) | null>(null), [error, setError] = useState('')
  const settle = (value: boolean) => { pending.current?.(value); pending.current = null }
  const confirmation = useConfirmDelete(`ss-file-${id}`, () => settle(false))
  useEffect(() => () => { pending.current?.(false) }, [])
  useEffect(() => { confirmation.close(); setError('') }, [chat.resourceKey, chat.selectionKey])
  const limits = chat.page?.attachments
  const confirmRemove = (file: { name: string }) => new Promise<boolean>(resolve => { settle(false); pending.current = resolve; confirmation.ask({ title: t('chat.toolkit.removeFileTitle'), name: file.name, onConfirm: () => settle(true) }) })
  return <><ChatComposer key={`${chat.resourceKey}:${chat.selectionKey}`} idPrefix={idPrefix ?? `ss-composer-${id}`} disabled={chat.loading || chat.waiting || chat.status === 'loading'} running={chat.status === 'streaming' || (chat.busy && chat.pending !== null)}
    onSend={(text, files) => { void chat.send(text, files).catch(() => {}) }} onStop={chat.cancel} confirmRemove={confirmRemove}
    onError={setError} files={limits && !chat.waiting ? { ...limits, kinds: limits.kinds.filter((k): k is 'image' | 'document' => k === 'image' || k === 'document'), upload: async file => { const [stored] = attachments([await chat.upload(file).catch(error => { throw new Error(errorText(error, i18n)) })]); if (!stored) throw new Error(t('chat.toolkit.requestFailed')); return stored }, remove: chat.removeFile } : null} />{error && <p role="alert" className="px-4 text-sm text-destructive">{error}</p>}{confirmation.dialog}</>
}
function Header({ title }: { title?: string }) {
  const chat = useChatController(), { t } = useTranslation()
  return <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
    <ChatLogo title={title || chat.page?.title || t('chat.page.title')} size="sm" />
    <h1 className="min-w-0 flex-1 truncate text-sm font-semibold">{title || chat.page?.title || t('chat.page.title')}</h1>
    {!!chat.sessions.length && <Select value={chat.sessionId ?? ''} disabled={chat.busy} onValueChange={id => void chat.load(id).catch(() => {})}>
      <SelectTrigger size="sm" variant="ghost" className="max-w-48 min-w-0" aria-label={t('chat.sessions')}><SelectValue placeholder={t('chat.untitled')} /></SelectTrigger>
      <SelectContent>{chat.sessions.map(session => <SelectItem key={session.id} value={session.id}>{session.title || t('chat.untitled')}</SelectItem>)}</SelectContent>
    </Select>}
    <Button variant="ghost" size="icon-sm" disabled={chat.busy} aria-label={t('chat.toolkit.refresh')} onClick={() => void chat.refresh().catch(() => {})}><RefreshCw /></Button>
    <Button variant="ghost" size="icon-sm" disabled={chat.busy} aria-label={t('chat.new')} onClick={() => void chat.start().catch(() => {})}><SquarePen /></Button>
  </header>
}
function ErrorNotice() {
  const chat = useChatController(), { t, i18n } = useTranslation()
  if (!chat.error) return null
  const error = chat.error as ApiErrorBody
  const message = error.code && i18n.exists(`errors.${error.code}`) ? errorText(error, i18n) : t('chat.toolkit.requestFailed')
  return <Alert variant="destructive" className="mx-3 mt-3 w-auto" role="alert"><AlertCircle /><AlertDescription>{message}</AlertDescription></Alert>
}
export interface ChatProps extends UseChatOptions { theme?: ChatTheme; messages?: ChatMessages; title?: string; className?: string; style?: CSSProperties }
export function Chat({ theme, messages, title, className, style, ...options }: ChatProps) {
  const chat = useChat(options)
  return <ChatProvider chat={chat} locale={options.locale} theme={theme} messages={messages} className={`ss-chat ${className ?? ''}`} style={style}>
    <Header title={title} /><ErrorNotice /><MessageList /><QuestionCard showPrompt={false} /><Composer />
  </ChatProvider>
}
