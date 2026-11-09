/** Chat triggers of a workflow: a command word that starts it from a Slack or Telegram message.
 *  List, turn on/off, edit, delete by typed name, and add one; the fields come from the saved graph, the connections from Channels. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { AlertCircle, MessageSquare, Pencil, Plus, Save, Trash2, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ChannelLogo } from '@/components/approvals/channel-logo'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { api } from '@/lib/api'
import { channelLabel, type Channel, type Channels } from '@/lib/approvals'
import { DM, newEventPolicy, normCommand, sampleMessage, validCommand, type ChatTrigger, type ChatTriggerForm } from '@/lib/chat-triggers'
import { EventBindingSettings } from '@/components/event-binding-settings'
import { fmtDate } from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'

const EMPTY: ChatTriggerForm = { name: '', channel_id: '', place: DM, command: '', input_field: '', reply_field: '', event: null }

export function ChatTriggersDialog({ wid, open, onOpenChange }: { wid?: string; open: boolean; onOpenChange: (v: boolean) => void }) {
  const { t } = useTranslation(); const [items, setItems] = useState<ChatTrigger[]>([]); const [err, setErr] = useState('')
  const [conns, setConns] = useState<Channel[]>([]); const [fields, setFields] = useState<string[]>([])
  const [form, setForm] = useState<ChatTriggerForm>(EMPTY); const [editing, setEditing] = useState<string | null>(null)
  const load = () => wid && api<ChatTrigger[]>(`/api/workflows/${wid}/chat-triggers`).then(setItems).catch(e => setErr(e.message))
  const fresh = (cs: Channel[], fs: string[]): ChatTriggerForm => ({ ...EMPTY, channel_id: cs[0]?.id ?? '', input_field: fs[0] ?? '', reply_field: fs[fs.length - 1] ?? '',
    event: cs[0]?.kind === 'webhook' ? newEventPolicy(fs[0]) : null })
  useLoadWhen(open, () => {
    setErr(''); setEditing(null); load()
    Promise.all([api<Channels>('/api/approvals/channels'), api<{ state?: { name: string }[] }>(`/api/workflows/${wid}`)]).then(([ch, wf]) => {
      const cs = ch.channels.filter(c => c.chat); const fs = (wf.state || []).map(f => f.name)
      setConns(cs); setFields(fs); setForm(fresh(cs, fs))
    }).catch(e => setErr(e.message))
  })
  const set = (patch: Partial<ChatTriggerForm>) => setForm(f => ({ ...f, ...patch }))
  const conn = conns.find(c => c.id === form.channel_id)
  const missing = conn?.chat?.missing_scopes
  const run = async (f: () => Promise<unknown>) => { setErr(''); try { await f(); await load(); return true } catch (e: any) { setErr(e.message); return false } }
  const save = async () => {
    const body = { ...form, command: normCommand(form.command), place: form.place.trim() || DM,
      event: form.event ? { ...form.event, senders: form.event.senders.map(s => s.trim()).filter(Boolean) } : null }
    const ok = await run(() => editing ? api(`/api/workflows/${wid}/chat-triggers/${editing}`, { method: 'PATCH', json: body })
      : api(`/api/workflows/${wid}/chat-triggers`, { method: 'POST', json: body }))
    if (ok) { setEditing(null); setForm(fresh(conns, fields)) }
  }
  const edit = (c: ChatTrigger) => { setEditing(c.id); setForm({ name: c.name, channel_id: c.channel_id, place: c.place, command: c.event ? '' : c.command, input_field: c.input_field, reply_field: c.reply_field, event: c.event || null }) }
  const toggle = (c: ChatTrigger, on: boolean) => run(() => api(`/api/workflows/${wid}/chat-triggers/${c.id}`, { method: 'PATCH', json: { enabled: on } }))
  const confirmDel = useConfirmDelete()
  const remove = (c: ChatTrigger) => confirmDel.ask({ title: t('chatTriggers.deleteTitle', { name: c.name }), name: c.name, description: t('chatTriggers.deleteBody'),
    onConfirm: async () => { await api(`/api/workflows/${wid}/chat-triggers/${c.id}`, { method: 'DELETE' }); if (editing === c.id) setEditing(null); load() } })
  const where = (c: { kind: string | null; place: string }) => c.place === DM ? t('chatTriggers.dm') : t(c.kind === 'telegram' ? 'chatTriggers.inGroup' : 'chatTriggers.inChannel', { place: c.place })
  const validEvent = !!form.event && form.event.senders.some(s => s.trim()) && !!form.event.type.trim() && Object.keys(form.event.mapping).length > 0
  const ready = !!wid && !!conn && (form.event ? validEvent : validCommand(form.command) && !!form.input_field && !!form.reply_field) && (form.place === DM || !!form.place.trim())
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-2xl max-h-[90dvh] flex flex-col overflow-hidden" id="chat-triggers-dialog">
      <DialogHeader className="shrink-0"><DialogTitle>{t('chatTriggers.title')}</DialogTitle><DialogDescription>{t(form.event ? 'eventBinding.description' : 'chatTriggers.desc')}</DialogDescription></DialogHeader>
      <div className="-mx-1 min-h-0 flex-1 space-y-4 overflow-y-auto px-1">
        {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
        <div className="space-y-2" id="chat-trigger-list">
          {items.map(c => <div key={c.id} data-testid="chat-trigger-row" data-name={c.name} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm">
            <Switch checked={c.enabled} onCheckedChange={v => toggle(c, v)} aria-label={t('chatTriggers.enabledFor', { name: c.name })} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><span className="truncate font-medium">{c.name}</span><code className="font-mono text-xs text-muted-foreground">{c.event ? c.event.type : c.command}</code></div>
              <div className="flex flex-wrap items-center gap-x-1 text-xs text-muted-foreground" data-testid="chat-trigger-where">
                {c.kind && <ChannelLogo kind={c.kind} className="size-3.5" />}{c.channel_name || (c.kind ? t(`approvals.kind.${c.kind}`) : t('chatTriggers.noConnection'))} · {where(c)}
                {!c.enabled && c.note ? <span className="text-warning"> · {t(`chatTriggers.notes.${c.note}`)}</span>
                  : c.last_message && <> · {t('chatTriggers.last', { when: fmtDate(c.last_message) })}{c.last_run_id && <span className="font-mono"> ({c.last_run_id})</span>}</>}
              </div>
            </div>
            {!c.enabled && c.note && <Badge variant="outline" className="border-warning text-warning">{t('chatTriggers.stopped')}</Badge>}
            <Button variant="ghost" size="icon-sm" aria-label={t('chatTriggers.editFor', { name: c.name })} onClick={() => edit(c)}><Pencil /></Button>
            <Button variant="ghost" size="icon-sm" aria-label={t('chatTriggers.deleteFor', { name: c.name })} onClick={() => remove(c)}><Trash2 /></Button>
          </div>)}
          {!items.length && <p className="text-xs text-muted-foreground">{t('chatTriggers.empty')}</p>}
        </div>
        <div className="space-y-3 rounded-md border p-3" id="chat-trigger-form">
          <div className="text-xs font-semibold uppercase text-muted-foreground">{t(editing ? 'chatTriggers.edit' : 'chatTriggers.add')}</div>
          {!conns.length ? <p className="text-sm text-muted-foreground" id="chat-trigger-no-connection">{t('chatTriggers.needConnection')} <Link className="underline" to="/settings/channels">{t('chatTriggers.openChannels')}</Link></p> : <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5"><Label htmlFor="chat-trigger-name" className="text-xs text-muted-foreground">{t('chatTriggers.name')}</Label>
              <Input id="chat-trigger-name" value={form.name} placeholder={normCommand(form.command) || t('chatTriggers.namePh')} onChange={e => set({ name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label htmlFor="chat-trigger-channel" className="text-xs text-muted-foreground">{t('chatTriggers.connection')}</Label>
              <Select value={form.channel_id} onValueChange={v => {
                const kind = conns.find(c => c.id === v)?.kind
                set({ channel_id: v, event: kind === 'webhook' ? (form.event || newEventPolicy(fields[0])) : kind === 'telegram' ? form.event : null })
              }}>
                <SelectTrigger id="chat-trigger-channel" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{conns.map(c => <SelectItem key={c.id} value={c.id}><ChannelLogo kind={c.kind} className="size-3.5" />{channelLabel(t, c)}</SelectItem>)}</SelectContent></Select></div>
            {conn?.kind !== 'webhook' && <div className="space-y-1.5"><Label htmlFor="chat-trigger-where" className="text-xs text-muted-foreground">{t('chatTriggers.where')}</Label>
              <Select value={form.place === DM ? DM : 'chat'} onValueChange={v => set({ place: v === DM ? DM : '' })}>
                <SelectTrigger id="chat-trigger-where" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value={DM}>{t('chatTriggers.dm')}</SelectItem>
                  <SelectItem value="chat">{t(conn?.kind === 'telegram' ? 'chatTriggers.aGroup' : 'chatTriggers.aChannel')}</SelectItem></SelectContent></Select></div>}
            {(form.place !== DM || conn?.kind === 'webhook') && <div className="space-y-1.5"><Label htmlFor="chat-trigger-place" className="text-xs text-muted-foreground">{t(conn?.kind === 'webhook' ? 'eventBinding.place' : conn?.kind === 'telegram' ? 'chatTriggers.groupId' : 'chatTriggers.channelId')}</Label>
              <Input id="chat-trigger-place" className="font-mono text-xs" value={form.place} placeholder={conn?.kind === 'telegram' ? '-1001234567890' : 'C0123ABCD'} onChange={e => set({ place: e.target.value })} /></div>}
            {(conn?.kind === 'telegram' || conn?.kind === 'webhook') && <div className="space-y-1.5"><Label htmlFor="chat-trigger-mode">{t('eventBinding.mode')}</Label>
              <Select value={form.event ? 'event' : 'command'} onValueChange={v => set({ event: v === 'event' ? newEventPolicy(form.input_field) : null })}>
                <SelectTrigger id="chat-trigger-mode" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{conn.kind !== 'webhook' && <SelectItem value="command">{t('eventBinding.command')}</SelectItem>}
                  <SelectItem value="event">{t('eventBinding.event')}</SelectItem></SelectContent></Select></div>}
            {!form.event && <><div className="space-y-1.5"><Label htmlFor="chat-trigger-command" className="text-xs text-muted-foreground">{t('chatTriggers.command')}</Label>
              <Input id="chat-trigger-command" className="font-mono text-xs" value={form.command} placeholder="leave" onChange={e => set({ command: e.target.value })}
                aria-invalid={!!form.command && !validCommand(form.command)} /></div>
            <div className="space-y-1.5"><Label htmlFor="chat-trigger-input" className="text-xs text-muted-foreground">{t('chatTriggers.inputField')}</Label>
              <Select value={form.input_field} onValueChange={v => set({ input_field: v })}>
                <SelectTrigger id="chat-trigger-input" className="w-full font-mono text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>{fields.map(f => <SelectItem key={f} value={f} className="font-mono text-xs">{f}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-1.5"><Label htmlFor="chat-trigger-reply" className="text-xs text-muted-foreground">{t('chatTriggers.replyField')}</Label>
              <Select value={form.reply_field} onValueChange={v => set({ reply_field: v })}>
                <SelectTrigger id="chat-trigger-reply" className="w-full font-mono text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>{fields.map(f => <SelectItem key={f} value={f} className="font-mono text-xs">{f}</SelectItem>)}</SelectContent></Select></div></>}
          </div>
          {form.event && <EventBindingSettings value={form.event} fields={fields} onChange={event => set({ event })} />}
          {!form.event && <p className="text-xs text-muted-foreground" id="chat-trigger-sample"><MessageSquare className="mr-1 inline size-3.5 align-[-2px]" />
            {t('chatTriggers.sample', { where: form.place === DM ? t('chatTriggers.dm') : form.place || '…' })}{' '}
            <code className="font-mono">{sampleMessage(conn?.kind ?? null, form.place, form.command, t('chatTriggers.bot'), t('chatTriggers.sampleText'))}</code></p>}
          {!form.event && !!form.command && !validCommand(form.command) && <p className="text-xs text-destructive" id="chat-trigger-command-hint">{t('chatTriggers.commandHint')}</p>}
          {missing && missing.length > 0 && <Alert variant="warning" id="chat-trigger-scopes"><TriangleAlert /><AlertDescription>
            {t('chatTriggers.missingScopes', { scopes: missing.join(', ') })} <Link className="underline" to="/settings/channels">{t('chatTriggers.openChannels')}</Link></AlertDescription></Alert>}
          <div className="flex justify-end gap-2">
            {editing && <Button variant="ghost" onClick={() => { setEditing(null); setForm(fresh(conns, fields)) }}>{t('common.cancel')}</Button>}
            <Button id="chat-trigger-save" onClick={save} disabled={!ready}>{editing ? <Save /> : <Plus />}{t(editing ? 'chatTriggers.save' : 'chatTriggers.create')}</Button>
          </div></>}
        </div>
        <p className="text-xs text-muted-foreground">{t(form.event ? 'eventBinding.replyHelp' : 'chatTriggers.help')}</p>
      </div>
    </DialogContent>
    {confirmDel.dialog}
  </Dialog>
}
