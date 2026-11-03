/** Shared public-page layout; legacy direct visits and SDK-backed embeds keep one presentation. */
import { useEffect, type ComponentProps, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, MessageCircleOff, SquarePen } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tip } from '@/components/tip'
import { waitingTurn, type PublicChatPage as Page, type ChatAttachment } from '@/lib/chat'
import { ChatLogo, ChatIllustration, ChatThread } from '@superstep/react'
import { ChatComposer } from '@/components/chat/chat-composer'
import { ChatMarkdown } from '@/components/chat/chat-markdown'

type Thread = ComponentProps<typeof ChatThread>
type Composer = ComponentProps<typeof ChatComposer>
export type PublicChatViewProps = {
  slug: string; page: Page | null; gone: boolean; err: string; ready: boolean; title: string; logo?: string; embed?: 'iframe' | 'widget';
  sessions: readonly { id: string; title?: string | null }[]; sid: string | null; setSid: (id: string) => void; fresh: () => void;
  chat: Pick<Thread, 'turns' | 'mode' | 'events' | 'trace' | 'pending' | 'pendingFiles' | 'running' | 'onAnswer' | 'onRate' | 'onEdit' | 'onRegenerate' | 'onSource' | 'files'>;
  files?: Composer['files']; onError: (error: string) => void; send: (text: string, files?: ChatAttachment[]) => void; cancel: () => void;
  renderThread?: (intro: ReactNode) => ReactNode; footer?: ReactNode
}
export function PublicChatView({ slug, page, gone, err, ready, title, logo, embed, sessions, sid, setSid, fresh, chat, files, onError, send, cancel, renderThread, footer }: PublicChatViewProps) {
  const { t } = useTranslation()
  useEffect(() => {
    if (page?.title) document.title = page.title
    if (!logo) return
    const studio = [...document.querySelectorAll<HTMLLinkElement>('link[rel="icon"]')]; studio.forEach(l => l.remove())
    const icon = Object.assign(document.createElement('link'), { rel: 'icon', href: logo, id: 'public-chat-favicon' }); document.head.append(icon)
    return () => { icon.remove(); document.head.append(...studio) }
  }, [logo, page?.title])
  const waiting = waitingTurn(chat.turns)
  if (gone) return <main className="flex min-h-svh items-center justify-center bg-background p-4" id="public-chat-gone">
    <Empty><EmptyHeader><EmptyMedia variant="icon"><MessageCircleOff /></EmptyMedia>
      <EmptyTitle>{t('chat.page.goneTitle')}</EmptyTitle><EmptyDescription>{t('chat.page.gone')}</EmptyDescription></EmptyHeader></Empty></main>
  const intro = page && <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-4 px-4 py-6 text-center" id="public-chat-intro">
    {logo ? <ChatLogo src={logo} title={title} className="size-16 rounded-2xl" id="public-chat-hero" /> : <ChatIllustration />}
    <h2 className="text-lg font-semibold">{title}</h2>
    {page.intro ? <ChatMarkdown text={page.intro} /> : <p className="text-sm text-muted-foreground">{t('chat.empty')}</p>}
    {!!page.suggestions.length && <div className="flex flex-wrap justify-center gap-2" id="public-chat-suggestions">
      {page.suggestions.map(x => <Button key={x} variant="outline" /* ui-class-ok: a suggestion can wrap to two lines, so its height follows the text */ className="h-auto min-h-9 py-2 whitespace-normal" data-testid="chat-suggestion" disabled={chat.running || !ready} onClick={() => send(x)}>{x}</Button>)}</div>}
  </div>
  return <main className="flex h-svh min-h-0 flex-col bg-background" id="public-chat" data-slug={slug} data-embed={embed}>
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
      {page && <ChatLogo src={logo} title={title} size="sm" id="public-chat-logo" />}
      <h1 className="min-w-0 flex-1 truncate text-sm font-semibold" id="public-chat-title">{title}</h1>
      {sessions.length > 0 && <Select value={sid ?? ''} onValueChange={setSid}>
        <SelectTrigger size="sm" variant="ghost" className="max-w-48 min-w-0" id="public-chat-sessions" aria-label={t('chat.sessions')}><SelectValue placeholder={t('chat.untitled')} /></SelectTrigger>
        <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.title || t('chat.untitled')}</SelectItem>)}</SelectContent></Select>}
      <Tip tip={t('chat.new')}><Button size="icon-sm" variant="ghost" id="public-chat-new" aria-label={t('chat.new')} disabled={!page || chat.running} onClick={fresh}><SquarePen /></Button></Tip>
    </header>
    {err && <Alert variant="destructive" className="mx-auto mt-3 w-full max-w-3xl"><AlertCircle /><AlertDescription id="public-chat-error">{err}</AlertDescription></Alert>}
    {page && (renderThread ? renderThread(intro) : <ChatThread {...chat} empty={intro} />)}
    {page && (footer ?? <ChatComposer disabled={!ready || waiting?.answered_by === 'reviewer'} running={chat.running} onStop={cancel}
      placeholder={waiting ? t(waiting.answered_by === 'reviewer' ? 'chat.waitingReviewer' : 'chat.answerPlaceholder') : undefined}
      files={files} onError={onError}
      onSend={(text, f) => waiting?.run_id ? chat.onAnswer?.(waiting.run_id, text) : send(text, f)} />)}
  </main>
}
