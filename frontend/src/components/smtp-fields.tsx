/** SMTP credential settings: host, port, security, user name and sender. The password is the credential's
 * secret field in the dialog. A preset fills the server of a common provider. */
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { SmtpSettings } from '@/lib/smtp'

const SECURITY = ['starttls', 'ssl', 'none'] as const
const PRESETS: Record<string, SmtpSettings> = {
  gmail: { host: 'smtp.gmail.com', port: 587, security: 'starttls' },
  outlook: { host: 'smtp.office365.com', port: 587, security: 'starttls' },
  sendgrid: { host: 'smtp.sendgrid.net', port: 587, security: 'starttls', username: 'apikey' },
  resend: { host: 'smtp.resend.com', port: 465, security: 'ssl', username: 'resend' },
  mailgun: { host: 'smtp.mailgun.org', port: 587, security: 'starttls' },
}

function F({ id, label, children, wide }: { id: string; label: string; children: React.ReactNode; wide?: boolean }) {
  return <div className={wide ? 'col-span-2 space-y-1.5' : 'space-y-1.5'}><Label htmlFor={id}>{label}</Label>{children}</div>
}

export function SmtpFields({ value, onChange }: { value: SmtpSettings; onChange: (v: SmtpSettings) => void }) {
  const { t } = useTranslation()
  const set = (patch: SmtpSettings) => onChange({ ...value, ...patch })
  const preset = Object.entries(PRESETS).find(([, p]) => p.host === value.host)?.[0] ?? 'custom'
  return <>
    <F id="smtp-preset" label={t('creds.smtp.preset')} wide>
      <Select value={preset} onValueChange={v => v !== 'custom' && set({ username: '', ...PRESETS[v] })}>
        <SelectTrigger className="w-full" id="smtp-preset"><SelectValue /></SelectTrigger>
        <SelectContent>{[...Object.keys(PRESETS), 'custom'].map(k => <SelectItem key={k} value={k}>{t(`creds.smtp.presets.${k}`)}</SelectItem>)}</SelectContent></Select>
      {preset !== 'custom' && <p className="text-xs text-muted-foreground" id="smtp-preset-hint">{t(`creds.smtp.presetHint.${preset}`)}</p>}
    </F>
    <F id="smtp-host" label={t('creds.smtp.host')}><Input id="smtp-host" value={value.host ?? ''} placeholder="smtp.example.com" onChange={e => set({ host: e.target.value })} /></F>
    <div className="grid grid-cols-2 gap-3">
      <F id="smtp-port" label={t('creds.smtp.port')}><Input id="smtp-port" type="number" min={1} max={65535} value={value.port ?? ''} onChange={e => set({ port: Number(e.target.value) || undefined })} /></F>
      <F id="smtp-security" label={t('creds.smtp.security')}>
        <Select value={value.security ?? 'starttls'} onValueChange={v => set({ security: v as SmtpSettings['security'], port: v === 'ssl' ? 465 : value.port === 465 ? 587 : value.port })}>
          <SelectTrigger className="w-full" id="smtp-security"><SelectValue /></SelectTrigger>
          <SelectContent>{SECURITY.map(s => <SelectItem key={s} value={s}>{t(`creds.smtp.securityOpts.${s}`)}</SelectItem>)}</SelectContent></Select>
      </F>
    </div>
    <F id="smtp-from" label={t('creds.smtp.fromEmail')}><Input id="smtp-from" type="email" value={value.from_email ?? ''} placeholder="support@example.com" onChange={e => set({ from_email: e.target.value })} /></F>
    <F id="smtp-from-name" label={t('creds.smtp.fromName')}><Input id="smtp-from-name" value={value.from_name ?? ''} placeholder={t('creds.smtp.fromNamePh')} onChange={e => set({ from_name: e.target.value })} /></F>
    <F id="smtp-username" label={t('creds.smtp.username')} wide><Input id="smtp-username" autoComplete="off" value={value.username ?? ''} onChange={e => set({ username: e.target.value })} /></F>
  </>
}
