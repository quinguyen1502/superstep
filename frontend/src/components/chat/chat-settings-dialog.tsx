/** A workflow's Chat settings (TASK-0085, REQ-0048): on/off, who may chat, the input / reply / messages fields, the memory
 *  window, which steps visitors see and how long chats are kept. Anyone with the link or signed-in users publish the chat
 *  at /c/{slug} (TASK-0142, DEC-0067): its address, title, intro, suggested messages and daily limit. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Check, Copy, ExternalLink, Plus, Save, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { InputGroup, InputGroupAddon, InputGroupInput, InputGroupText } from '@/components/ui/input-group'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { api, ApiError } from '@/lib/api'
import { ACCESS, MAX_SUGGESTIONS, pageUrl, published, STEPS, type ChatSettings } from '@/lib/chat'
import { useLoadWhen } from '@/lib/use-when'

type Field = { name: string; type: string }
const NONE = '__none'

export function ChatSettingsDialog({ wid, open, onOpenChange, onSaved }: { wid?: string; open: boolean; onOpenChange: (v: boolean) => void; onSaved?: (s: ChatSettings) => void }) {
  const { t } = useTranslation(); const [v, setV] = useState<ChatSettings | null>(null); const [fields, setFields] = useState<Field[]>([])
  const [err, setErr] = useState(''); const [bad, setBad] = useState(''); const [busy, setBusy] = useState(false)
  useLoadWhen(open, () => {
    setErr(''); setBad('')
    Promise.all([api<ChatSettings>(`/api/workflows/${wid}/chat`), api<{ state?: Field[] }>(`/api/workflows/${wid}`)])
      .then(([s, wf]) => { setV(s); setFields(wf.state || []) }).catch(e => setErr(e.message))
  })
  const set = (p: Partial<ChatSettings>) => setV(x => x && { ...x, ...p })
  const save = () => { if (!v) return; setBusy(true); setErr(''); setBad('')
    const body = { ...v, suggestions: v.suggestions.map(x => x.trim()).filter(Boolean) }
    api<ChatSettings>(`/api/workflows/${wid}/chat`, { method: 'PUT', json: body }).then(s => { setV(s); onSaved?.(s); onOpenChange(false) })
      .catch(e => { setErr(e.message); if (e instanceof ApiError) setBad(e.code?.startsWith('CHAT_SLUG') ? 'slug' : e.details?.field ?? '') }).finally(() => setBusy(false)) }
  const [copied, setCopied] = useState(false)
  const copy = () => v && navigator.clipboard.writeText(pageUrl(v.slug)).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }).catch(() => {})
  const names = (pred: (f: Field) => boolean) => fields.filter(pred).map(f => f.name)
  const pick = (id: keyof ChatSettings, opts: string[], none = false) => <Select value={(v?.[id] as string) || (none ? NONE : '')} onValueChange={x => set({ [id]: x === NONE ? '' : x } as any)}>
    <SelectTrigger className="w-full" id={`chat-${id}`} aria-invalid={bad === id || undefined}><SelectValue placeholder={t('chat.settings.pickField')} /></SelectTrigger>
    <SelectContent>{none && <SelectItem value={NONE}>{t('chat.settings.noMemory')}</SelectItem>}{opts.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent></Select>
  const row = (id: string, label: string, hint: string | null, control: React.ReactNode) => <div className="grid gap-1.5">
    <Label htmlFor={`chat-${id}`}>{label}</Label>{control}{hint && <p className="text-xs text-muted-foreground">{hint}</p>}</div>
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg" id="chat-settings">
      <DialogHeader><DialogTitle>{t('chat.settings.title')}</DialogTitle><DialogDescription>{t('chat.settings.desc')}</DialogDescription></DialogHeader>
      {err && <Alert variant="destructive"><AlertCircle /><AlertDescription id="chat-settings-error">{err}</AlertDescription></Alert>}
      {v && <div className="grid gap-4">
        <div className="flex items-center justify-between gap-3 rounded-lg border p-3">
          <div className="grid gap-0.5"><Label htmlFor="chat-enabled">{t('chat.settings.enabled')}</Label><p className="text-xs text-muted-foreground">{t('chat.settings.enabledHint')}</p></div>
          <Switch id="chat-enabled" checked={v.enabled} onCheckedChange={enabled => set({ enabled })} /></div>
        {row('access', t('chat.settings.access'), t('chat.settings.accessHint'), <Select value={v.access} onValueChange={access => set({ access })}>
          <SelectTrigger className="w-full" id="chat-access"><SelectValue /></SelectTrigger>
          <SelectContent>{ACCESS.map(a => <SelectItem key={a} value={a}>{t(`chat.access.${a}`)}</SelectItem>)}</SelectContent></Select>)}
        {v.access !== 'studio' && <div className="grid gap-4 rounded-lg border p-3" id="chat-publish">
          {row('slug', t('chat.publish.slug'), t('chat.publish.slugHint'), <InputGroup aria-invalid={bad === 'slug' || undefined}>
            <InputGroupAddon><InputGroupText>/c/</InputGroupText></InputGroupAddon>
            <InputGroupInput id="chat-slug" value={v.slug} aria-invalid={bad === 'slug' || undefined} onChange={e => set({ slug: e.target.value.toLowerCase() })} /></InputGroup>)}
          {published(v) && <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" id="chat-copy-link" onClick={copy}>{copied ? <Check /> : <Copy />}{t(copied ? 'chat.copied' : 'chat.publish.copyLink')}</Button>
            <Button size="sm" variant="outline" id="chat-open-page" asChild><a href={pageUrl(v.slug)} target="_blank" rel="noreferrer"><ExternalLink />{t('chat.publish.openPage')}</a></Button></div>}
          {!v.enabled && <p className="text-xs text-muted-foreground" id="chat-publish-off">{t('chat.publish.off')}</p>}
          <Separator />
          {row('title', t('chat.publish.title'), t('chat.publish.titleHint'), <Input id="chat-title" maxLength={60} aria-invalid={bad === 'title' || undefined} value={v.title} onChange={e => set({ title: e.target.value })} />)}
          {row('intro', t('chat.publish.intro'), t('chat.publish.introHint'), <Textarea id="chat-intro" rows={3} maxLength={1000} aria-invalid={bad === 'intro' || undefined} value={v.intro} onChange={e => set({ intro: e.target.value })} />)}
          <div className="grid gap-1.5"><Label>{t('chat.publish.suggestions')}</Label>
            {v.suggestions.map((x, i) => <div key={i} className="flex gap-2">
              <Input id={`chat-suggestion-${i}`} maxLength={120} aria-label={t('chat.publish.suggestion', { n: i + 1 })} aria-invalid={bad === 'suggestions' || undefined} value={x}
                onChange={e => set({ suggestions: v.suggestions.map((y, j) => j === i ? e.target.value : y) })} />
              <Button size="icon" variant="ghost" aria-label={t('chat.publish.removeSuggestion')} onClick={() => set({ suggestions: v.suggestions.filter((_, j) => j !== i) })}><X /></Button></div>)}
            {v.suggestions.length < MAX_SUGGESTIONS && <Button size="sm" variant="ghost" className="justify-self-start" id="chat-add-suggestion" onClick={() => set({ suggestions: [...v.suggestions, ''] })}><Plus />{t('chat.publish.addSuggestion')}</Button>}
            <p className="text-xs text-muted-foreground">{t('chat.publish.suggestionsHint')}</p></div>
          {row('daily_limit', t('chat.publish.dailyLimit'), t('chat.publish.dailyLimitHint'), <Input id="chat-daily_limit" type="number" min={0} max={100000}
            aria-invalid={bad === 'daily_limit' || undefined} value={v.daily_limit} onChange={e => set({ daily_limit: Number(e.target.value) })} />)}
        </div>}
        <div className="grid grid-cols-2 gap-3">
          {row('input_field', t('chat.settings.inputField'), null, pick('input_field', names(f => f.type === 'string' || f.type === 'list')))}
          {row('reply_field', t('chat.settings.replyField'), null, pick('reply_field', names(() => true)))}
        </div>
        {row('messages_field', t('chat.settings.messagesField'), t('chat.settings.messagesHint'), pick('messages_field', names(f => f.type === 'list' && f.name !== v.input_field), true))}
        <div className="grid grid-cols-2 gap-3">
          {row('max_turns', t('chat.settings.maxTurns'), t('chat.settings.maxTurnsHint'), <Input id="chat-max_turns" type="number" min={1} max={50} disabled={!v.messages_field}
            aria-invalid={bad === 'max_turns' || undefined} value={v.max_turns} onChange={e => set({ max_turns: Number(e.target.value) })} />)}
          {row('retention_days', t('chat.settings.retention'), t('chat.settings.retentionHint'), <Input id="chat-retention_days" type="number" min={1} max={3650}
            aria-invalid={bad === 'retention_days' || undefined} value={v.retention_days} onChange={e => set({ retention_days: Number(e.target.value) })} />)}
        </div>
        {row('steps', t('chat.settings.steps'), t('chat.settings.stepsHint'), <Select value={v.steps} onValueChange={steps => set({ steps: steps as ChatSettings['steps'] })}>
          <SelectTrigger className="w-full" id="chat-steps"><SelectValue /></SelectTrigger>
          <SelectContent>{STEPS.map(s => <SelectItem key={s} value={s}>{t(`chat.steps.${s}`)}</SelectItem>)}</SelectContent></Select>)}
      </div>}
      <DialogFooter><Button id="chat-settings-save" disabled={!v || busy} onClick={save}><Save />{t('common.save')}</Button></DialogFooter>
    </DialogContent>
  </Dialog>
}
