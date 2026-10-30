/** Chat attachments (TASK-0177, REQ-0077): a file as a chip (shadcn Item, size xs) with its thumbnail or icon, name and
 *  size, and one icon action (remove before sending, download after). A download is fetched with the chat's headers
 *  (the widget's visitor token) and saved from a blob: files are never opened in the page. */
import { useTranslation } from 'react-i18next'
import { Download, FileText, LoaderCircle, X } from 'lucide-react'
import { Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle } from '@/components/ui/item'
import { Button } from '@/components/ui/button'
import { Tip } from '@/components/tip'
import { fileSize, type AttachmentKind, type ChatAttachment } from '@/lib/chat'
import { cn } from '@/lib/utils'
import { downloadFile } from '@/lib/chat-files'

export function AttachmentChip({ name, size, kind, preview, busy, invalid, action, className, ...props }: {
  name: string; size: number; kind: AttachmentKind | null; preview?: string; busy?: boolean; invalid?: boolean
  action?: React.ReactNode; className?: string } & Omit<React.ComponentProps<'div'>, 'children'>) {
  return <Item size="xs" variant="outline" className={cn('w-auto max-w-56 flex-nowrap', invalid && 'border-destructive', className)} data-kind={kind ?? undefined} {...props}>
    <ItemMedia variant={preview ? 'image' : 'icon'}>
      {busy ? <LoaderCircle className="animate-spin" /> : preview ? <img src={preview} alt="" /> : <FileText />}
    </ItemMedia>
    <ItemContent className="min-w-0"><ItemTitle className="block truncate" title={name}>{name}</ItemTitle>
      <ItemDescription className="tabular-nums">{fileSize(size)}</ItemDescription></ItemContent>
    {action && <ItemActions>{action}</ItemActions>}
  </Item>
}

/** The remove action of a chip in the composer. */
export function RemoveFile({ name, onClick }: { name: string; onClick: () => void }) {
  const { t } = useTranslation(); const label = t('chat.files.remove', { name })
  return <Tip tip={label}><Button type="button" size="icon-xs" variant="ghost" aria-label={label} data-testid="chat-file-remove" onClick={onClick}><X /></Button></Tip>
}

/** A sent message's files, each with a download action. `url` gives a file's address; none: no download (a pending turn). */
export function TurnFiles({ files, url, headers, align = 'end' }: { files: ChatAttachment[]; url?: (id: string) => string; headers?: Record<string, string>; align?: 'start' | 'end' }) {
  const { t } = useTranslation()
  if (!files.length) return null
  return <div className={cn('flex flex-wrap gap-2', align === 'end' && 'justify-end')} data-testid="chat-turn-files">
    {files.map(f => <AttachmentChip key={f.id} name={f.name} size={f.size} kind={f.kind} data-testid="chat-turn-file"
      action={url && <Tip tip={t('chat.files.download', { name: f.name })}><Button type="button" size="icon-xs" variant="ghost" data-testid="chat-file-download"
        aria-label={t('chat.files.download', { name: f.name })} onClick={() => downloadFile(url(f.id), f.name, headers).catch(() => {})}><Download /></Button></Tip>} />)}
  </div>
}
