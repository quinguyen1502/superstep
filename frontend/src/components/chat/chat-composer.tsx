/** The message box (TASK-0085), built as the shadcn Prompt Input pattern: a form with an Input Group, its textarea and
 *  a block-end addon with the send button (Stop while a run goes). Enter sends, Shift+Enter adds a line. A counter
 *  shows near the limit.
 *  Attachments (TASK-0177, REQ-0077): when the chat accepts files, a paperclip button and drag-and-drop add them. Each
 *  file is checked here first (kind, size, count: the chat's limits), then uploaded at once and shown as a chip with a
 *  thumbnail for images and a remove action. Send waits until every upload is done. */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowUp, Paperclip, Square } from 'lucide-react'
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupText, InputGroupTextarea } from '@/components/ui/input-group'
import { Tip } from '@/components/tip'
import { errorText } from '@/lib/i18n'
import { acceptOf, attachmentKind, attachmentProblem, MAX_MESSAGE, type AttachmentLimits, type ChatAttachment } from '@/lib/chat'
import { AttachmentChip, RemoveFile } from './chat-attachments'
import { cn } from '@/lib/utils'

/** What the composer needs for files: the chat's limits, and how to store and drop one. */
export type ComposerFiles = AttachmentLimits & { upload: (file: File) => Promise<ChatAttachment>; remove: (id: string) => Promise<unknown> }
type Pending = { key: string; name: string; size: number; preview?: string; done?: ChatAttachment }

export function ChatComposer({ disabled, running, onSend, onStop, placeholder, files, onError }: {
  disabled: boolean; running: boolean; onSend: (text: string, files: ChatAttachment[]) => void; onStop: () => void; placeholder?: string
  files?: ComposerFiles | null; onError?: (message: string) => void }) {   // onError(''): clear the message
  const { t } = useTranslation(); const [text, setText] = useState(''); const form = useRef<HTMLFormElement>(null)
  const picker = useRef<HTMLInputElement>(null); const [items, setItems] = useState<Pending[]>([]); const [over, setOver] = useState(false)
  const allowed = !!files?.enabled && files.kinds.length > 0
  const uploading = items.some(x => !x.done)
  useEffect(() => () => items.forEach(x => x.preview && URL.revokeObjectURL(x.preview)), [])  // eslint-disable-line react-hooks/exhaustive-deps -- on unmount
  const canSend = (!!text.trim() || items.length > 0) && text.length <= MAX_MESSAGE && !disabled && !running && !uploading
  const add = (list: FileList | File[]) => {
    if (!files || !allowed) return
    let count = items.length
    for (const f of Array.from(list)) {
      const problem = attachmentProblem(f, files, count)
      if (problem) { onError?.(errorText({ code: problem.code, details: problem.params })); continue }
      count += 1; onError?.('')   // a good file clears an earlier refusal
      const key = `${Date.now()}-${Math.random()}`
      const preview = attachmentKind(f.name) === 'image' ? URL.createObjectURL(f) : undefined
      setItems(l => [...l, { key, name: f.name, size: f.size, preview }])
      files.upload(f).then(done => setItems(l => l.map(x => x.key === key ? { ...x, done } : x)))
        .catch(e => { setItems(l => l.filter(x => x.key !== key)); if (preview) URL.revokeObjectURL(preview); onError?.(e.message) })
    }
  }
  const drop = (x: Pending) => { setItems(l => l.filter(y => y.key !== x.key)); if (x.preview) URL.revokeObjectURL(x.preview)
    if (x.done) files?.remove(x.done.id).catch(() => {}) }
  const submit = (e: React.FormEvent) => { e.preventDefault(); if (!canSend) return
    onSend(text.trim(), items.flatMap(x => x.done ? [x.done] : [])); setText('')
    items.forEach(x => x.preview && URL.revokeObjectURL(x.preview)); setItems([]) }
  const dragging = (e: React.DragEvent) => { if (!allowed || disabled || !e.dataTransfer.types.includes('Files')) return; e.preventDefault(); setOver(true) }
  return <form ref={form} onSubmit={submit} className="mx-auto w-full max-w-3xl p-3" id="chat-form"
    onDragOver={dragging} onDragEnter={dragging} onDragLeave={() => setOver(false)}
    onDrop={e => { if (!allowed || disabled) return; e.preventDefault(); setOver(false); add(e.dataTransfer.files) }}>
    <InputGroup className={cn(over && 'border-primary ring-[3px] ring-ring/50')} data-dragging={over || undefined}>
      {items.length > 0 && <InputGroupAddon align="block-start" className="flex-wrap gap-2" id="chat-files">
        {items.map(x => <AttachmentChip key={x.key} name={x.name} size={x.size} kind={attachmentKind(x.name)} preview={x.preview} busy={!x.done}
          data-testid="chat-file" data-state={x.done ? 'done' : 'uploading'} action={<RemoveFile name={x.name} onClick={() => drop(x)} />} />)}
      </InputGroupAddon>}
      <InputGroupTextarea id="chat-input" aria-label={t('chat.message')} placeholder={placeholder ?? t('chat.placeholder')} disabled={disabled}
        className="max-h-40 min-h-14" value={text} onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); form.current?.requestSubmit() } }} />
      <InputGroupAddon align="block-end" className="pt-1">
        {allowed && <>
          <input ref={picker} type="file" multiple className="sr-only" id="chat-file-input" accept={acceptOf(files!.kinds)} tabIndex={-1}
            onChange={e => { if (e.target.files) add(e.target.files); e.target.value = '' }} />
          <Tip tip={t('chat.files.attach', { max: files!.max_files, max_mb: files!.max_mb })}><InputGroupButton type="button" size="icon-sm" variant="ghost" className="rounded-full" id="chat-attach"
            aria-label={t('chat.files.attachLabel')} disabled={disabled || running} onClick={() => picker.current?.click()}><Paperclip /></InputGroupButton></Tip></>}
        {text.length > MAX_MESSAGE * 0.9 && <InputGroupText id="chat-count" className={text.length > MAX_MESSAGE ? 'text-destructive' : undefined}>{text.length}/{MAX_MESSAGE}</InputGroupText>}
        {running
          ? <InputGroupButton type="button" size="icon-sm" variant="outline" className="ml-auto rounded-full" id="chat-stop" aria-label={t('chat.stop')} onClick={onStop}><Square /></InputGroupButton>
          : <Tip tip={uploading ? t('chat.files.uploading') : null}><InputGroupButton type="submit" size="icon-sm" variant="default" className="ml-auto rounded-full" id="chat-send" aria-label={t('chat.send')} disabled={!canSend}><ArrowUp /></InputGroupButton></Tip>}
      </InputGroupAddon>
    </InputGroup>
  </form>
}
