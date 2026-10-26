/** Send email node settings (TASK-0051): an SMTP credential (none = dry run), recipients, subject and body templates. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TemplateEditor } from '@/components/template-editor'
import type { Field } from '@/components/editor/meta'
import type { Credential } from '@/components/credentials-dialog'
import type { ProviderInfo } from '@/lib/providers'

type Data = { credential_id?: string; to?: string; cc?: string; bcc?: string; reply_to?: string; subject?: string; body?: string; format?: 'text' | 'html'; output_field?: string }
type Props = { data: Data; fields: Field[]; creds: Credential[]; providers: ProviderInfo[]; readOnly?: boolean; onChange: (patch: Partial<Data>) => void }

function Row({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={htmlFor}>{label}</Label>{children}</div>
}

export function EmailSettings({ data, fields, creds, providers, readOnly, onChange }: Props) {
  const { t } = useTranslation()
  const usable = creds.filter(c => providers.find(p => p.id === c.provider)?.kind === 'email')
  const [more, setMore] = useState(!!(data.cc || data.bcc || data.reply_to))
  const tpl = (key: 'to' | 'cc' | 'bcc' | 'reply_to' | 'subject' | 'body', rows = 1, placeholder?: string) =>
    <TemplateEditor id={`email-${key.replace('_', '-')}`} rows={rows} singleLine={rows === 1} fields={fields} readOnly={readOnly} value={data[key] || ''} placeholder={placeholder} onChange={v => onChange({ [key]: v })} />
  return <div className="space-y-3" id="email-settings">
    <Row label={t('email.credential')} htmlFor="email-credential">
      <Select value={data.credential_id || 'none'} onValueChange={v => onChange({ credential_id: v === 'none' ? '' : v })}>
        <SelectTrigger className="w-full" id="email-credential"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('email.dryRun')}</SelectItem>
          {usable.map(c => <SelectItem key={c.id} value={c.id}>{c.name}{c.settings?.from_email ? ` · ${c.settings.from_email}` : ''}</SelectItem>)}</SelectContent></Select>
      {!data.credential_id && <p className="text-[11px] text-muted-foreground" id="email-dry-hint">{t('email.dryRunHint')}</p>}
    </Row>
    <Row label={t('email.to')}>{tpl('to', 1, 'customer@example.com, {{state.email}}')}</Row>
    {!more && <Button variant="ghost" size="xs" className="-mt-1" id="email-more" onClick={() => setMore(true)}><ChevronDown />{t('email.more')}</Button>}
    {more && <>
      <Row label={t('email.cc')}>{tpl('cc')}</Row>
      <Row label={t('email.bcc')}>{tpl('bcc')}</Row>
      <Row label={t('email.replyTo')}>{tpl('reply_to')}</Row>
    </>}
    <p className="text-[11px] text-muted-foreground">{t('email.addressHint', { field: '{{state.field}}' })}</p>
    <Row label={t('email.subject')}>{tpl('subject')}</Row>
    <Row label={t('email.format')} htmlFor="email-format">
      <Select value={data.format || 'text'} onValueChange={v => onChange({ format: v as Data['format'] })}>
        <SelectTrigger className="w-full" id="email-format"><SelectValue /></SelectTrigger>
        <SelectContent>{(['text', 'html'] as const).map(f => <SelectItem key={f} value={f}>{t(`email.formats.${f}`)}</SelectItem>)}</SelectContent></Select>
    </Row>
    <Row label={t('email.body')}>{tpl('body', 6)}</Row>
    {data.format === 'html' && <p className="text-[11px] text-muted-foreground" id="email-html-hint">{t('email.htmlHint', { field: '{{state.…}}' })}</p>}
    <p className="text-[11px] text-muted-foreground" id="email-hint">{t('email.hint')}</p>
  </div>
}

/** Data tab (TASK-0121): the optional object field that receives the send result. */
export function EmailData({ data, fields, onChange }: Pick<Props, 'data' | 'fields' | 'onChange'>) {
  const { t } = useTranslation()
  return <Row label={t('email.outputField')} htmlFor="email-output">
    <Select value={data.output_field || 'none'} onValueChange={v => onChange({ output_field: v === 'none' ? '' : v })}>
      <SelectTrigger className="w-full" id="email-output"><SelectValue /></SelectTrigger>
      <SelectContent><SelectItem value="none">{t('email.outputNone')}</SelectItem>
        {fields.filter(f => f.type === 'object' && (!f.reducer || f.reducer === 'replace')).map(f => <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>)}</SelectContent></Select>
  </Row>
}
