import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck, Settings } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { api, wsUrl } from '@/lib/api'
import { NotificationSettingsDialog } from '@/components/notification-settings-dialog'
import i18n from '@/lib/i18n'
import { cn } from '@/lib/utils'

type Note = { id: string; kind: 'run_waiting' | 'run_expired' | 'run_reminder' | 'run_escalated' | 'run_auto_answered'; title: string; link: string | null; created: number; read: boolean
  params: { workflow_name?: string | null; label?: string | null; prompt?: string | null } }
const POLL_MS = 30_000

/** Live push (TASK-0021): WebSocket /ws/notifications; reconnects with backoff. Returns whether it is connected. */
function useLivePush(onPush: (n: Note, unread: number) => void) {
  const [live, setLive] = useState(false); const cb = useRef(onPush)
  useEffect(() => { cb.current = onPush })
  useEffect(() => {
    let ws: WebSocket | null = null; let timer: ReturnType<typeof setTimeout> | undefined; let delay = 2_000; let stopped = false
    const connect = () => {
      ws = new WebSocket(wsUrl('/ws/notifications'))
      ws.onmessage = e => {
        const m = JSON.parse(e.data)
        if (m.type === 'ready') { setLive(true); delay = 2_000 }
        if (m.type === 'notification') cb.current(m.notification, m.unread)
      }
      ws.onclose = () => { setLive(false); if (!stopped) { timer = setTimeout(connect, delay); delay = Math.min(delay * 2, 60_000) } }
    }
    connect()
    return () => { stopped = true; clearTimeout(timer); ws?.close() }
  }, [])
  return live
}

/** In-app notifications (TASK-0020): bell with unread count, list, mark read. Live push with polling as the fallback,
 *  and a settings dialog for the user's channels (TASK-0021). */
export function NotificationBell() {
  const { t } = useTranslation(); const nav = useNavigate()
  const [items, setItems] = useState<Note[]>([]); const [unread, setUnread] = useState(0); const [settings, setSettings] = useState(false)
  const load = () => api<{ items: Note[]; unread: number }>('/api/notifications').then(d => { setItems(d.items); setUnread(d.unread) }).catch(() => {})
  const live = useLivePush((n, u) => { setItems(xs => [n, ...xs.filter(x => x.id !== n.id)].slice(0, 30)); setUnread(u) })
  useEffect(() => { load(); window.addEventListener('focus', load); return () => window.removeEventListener('focus', load) }, [])
  useEffect(() => { if (live) return; const id = setInterval(load, POLL_MS); return () => clearInterval(id) }, [live])  // polling only as the fallback
  const open = async (n: Note) => {
    if (!n.read) { try { const r = await api<{ unread: number }>(`/api/notifications/${n.id}/read`, { method: 'POST' }); setUnread(r.unread) } catch { /* ignore */ } }
    setItems(xs => xs.map(x => x.id === n.id ? { ...x, read: true } : x))
    if (n.link) nav(n.link)
  }
  const readAll = async () => { try { await api('/api/notifications/read-all', { method: 'POST' }); setUnread(0); setItems(xs => xs.map(x => ({ ...x, read: true }))) } catch { /* ignore */ } }
  const text = (n: Note) => t(`notify.${n.kind}`, { workflow: n.params.workflow_name || t('notify.unknownWorkflow'), label: n.params.label || '' })
  return <><DropdownMenu onOpenChange={o => o && load()}>
    <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" id="notify-bell" className="relative" data-live={live} aria-label={t('notify.unread', { count: unread })}>
      <Bell />{unread > 0 && <Badge size="sm" className="absolute -top-1 -right-1 min-w-4" data-testid="notify-count">{unread}</Badge>}</Button></DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-80">
      <DropdownMenuLabel className="flex items-center justify-between">{t('notify.title')}
        {unread > 0 && <Button variant="ghost" size="xs" id="notify-read-all" onClick={e => { e.preventDefault(); readAll() }}><CheckCheck />{t('notify.markAll')}</Button>}</DropdownMenuLabel>
      <DropdownMenuSeparator />
      {!items.length && <div className="px-2 py-3 text-xs text-muted-foreground">{t('notify.empty')}</div>}
      {items.map(n => <DropdownMenuItem key={n.id} data-testid="notify-item" data-read={n.read} onClick={() => open(n)} className="flex items-start gap-2">
        <span className={cn('mt-1.5 size-2 shrink-0 rounded-full', n.read ? 'bg-transparent' : 'bg-primary')} />
        <span className="min-w-0 space-y-0.5"><span className={cn('block text-sm', !n.read && 'font-medium')}>{text(n)}</span>
          {n.params.prompt && <span className="block truncate text-xs text-muted-foreground">{n.params.prompt}</span>}
          <span className="block text-xs text-muted-foreground">{new Date(n.created * 1000).toLocaleString(i18n.resolvedLanguage)}</span></span>
      </DropdownMenuItem>)}
      <DropdownMenuSeparator />
      <DropdownMenuItem id="notify-settings" onClick={() => setSettings(true)}><Settings />{t('notifyPrefs.open')}</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
  <NotificationSettingsDialog open={settings} onOpenChange={setSettings} /></>
}
