import { ShieldAlert, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import { useMe } from '@/lib/rbac'

type Prefs = { in_app: boolean; email: boolean; email_configured: boolean }

/** Per-user notification preferences (TASK-0021): in-app bell and e-mail channels. */
export function NotificationSettingsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { t } = useTranslation()
  const [prefs, setPrefs] = useState<Prefs | null>(null); const [err, setErr] = useState(''); const readOnly = !!useMe()?.read_only  // the demo visitor
  useEffect(() => { if (open) api<Prefs>('/api/notifications/preferences').then(p => { setPrefs(p); setErr('') }).catch(e => setErr(e.message)) }, [open])
  const save = async (k: 'in_app' | 'email', v: boolean) => {
    setErr(''); setPrefs(p => p && { ...p, [k]: v })
    try { setPrefs(await api<Prefs>('/api/notifications/preferences', { method: 'PUT', json: { [k]: v } })) }
    catch (e: any) { setErr(e.message); setPrefs(p => p && { ...p, [k]: !v }) }
  }
  const row = (k: 'in_app' | 'email', disabled = false) => <div className="flex items-start justify-between gap-4 rounded-lg border p-3">
    <div className="space-y-0.5"><Label htmlFor={`notify-pref-${k}`}>{t(`notifyPrefs.${k}`)}</Label>
      <p className="text-xs text-muted-foreground">{t(`notifyPrefs.${k}Help`)}</p></div>
    <Switch id={`notify-pref-${k}`} checked={!!prefs?.[k]} disabled={!prefs || disabled || readOnly} onCheckedChange={v => save(k, v)} />
  </div>
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-md" id="notify-settings-dialog">
      <DialogHeader><DialogTitle>{t('notifyPrefs.title')}</DialogTitle><DialogDescription>{t('notifyPrefs.description')}</DialogDescription></DialogHeader>
      <div className="space-y-3">
        {readOnly && <Alert variant="warning" id="notify-read-only"><ShieldAlert /><AlertDescription>{t('demo.readOnly')}</AlertDescription></Alert>}
        {row('in_app')}
        {row('email')}
        {prefs && !prefs.email_configured && <Alert variant="warning" id="notify-email-off"><TriangleAlert /><AlertDescription>{t('notifyPrefs.emailNotConfigured')}</AlertDescription></Alert>}
        {err && <Alert variant="destructive"><AlertDescription>{err}</AlertDescription></Alert>}
      </div>
    </DialogContent>
  </Dialog>
}
