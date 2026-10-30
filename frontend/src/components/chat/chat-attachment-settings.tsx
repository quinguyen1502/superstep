/** Chat settings, Attachments section (TASK-0177, REQ-0077): on or off, the kinds, files per message and size (within
 *  the operator's ceiling from the settings response) and the state field that receives the file records. */
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ATTACHMENT_KINDS, type AttachmentSettings } from '@/lib/chat'

const CEILING = { max_files: 5, max_mb: 10 }   // the server's defaults, until the settings say otherwise

export function ChatAttachmentSettings({ value, ceiling, lists, bad, onChange }: { value: AttachmentSettings; ceiling?: { max_files: number; max_mb: number }
  lists: string[]; bad: string; onChange: (p: Partial<AttachmentSettings>) => void }) {
  const { t } = useTranslation(); const limit = ceiling ?? CEILING
  const row = (id: string, label: string, hint: string | null, control: React.ReactNode) => <div className="grid gap-1.5">
    <Label htmlFor={`chat-${id}`}>{label}</Label>{control}{hint && <p className="text-xs text-muted-foreground">{hint}</p>}</div>
  return <>
        <div className="grid gap-4 rounded-lg border p-3" id="chat-attachments">
          <div className="flex items-center justify-between gap-3">
            <div className="grid gap-0.5"><Label htmlFor="chat-attachments-enabled">{t('chat.files.settings.enabled')}</Label>
              <p className="text-xs text-muted-foreground">{t('chat.files.settings.enabledHint')}</p></div>
            <Switch id="chat-attachments-enabled" checked={value.enabled} onCheckedChange={enabled => onChange({ enabled })} /></div>
          {value.enabled && <>
            <div className="grid gap-1.5"><Label>{t('chat.files.settings.kinds')}</Label>
              <div className="flex flex-wrap gap-4">{ATTACHMENT_KINDS.map(k => <div key={k} className="flex items-center gap-2">
                <Switch id={`chat-attachments-kind-${k}`} aria-invalid={bad === 'attachments.kinds' || undefined} checked={value.kinds.includes(k)}
                  onCheckedChange={on => onChange({ kinds: on ? ATTACHMENT_KINDS.filter(x => x === k || value.kinds.includes(x)) : value.kinds.filter(x => x !== k) })} />
                <Label htmlFor={`chat-attachments-kind-${k}`} className="font-normal">{t(`chat.files.kinds.${k}`)}</Label></div>)}</div>
              <p className="text-xs text-muted-foreground">{t('chat.files.settings.kindsHint')}</p></div>
            <div className="grid grid-cols-2 gap-3">
              {row('attachments.max_files', t('chat.files.settings.maxFiles'), t('chat.files.settings.ceiling', { max: limit.max_files }), <Input id="chat-attachments.max_files" type="number" min={1} max={limit.max_files}
                aria-invalid={bad === 'attachments.max_files' || undefined} value={value.max_files} onChange={e => onChange({ max_files: Number(e.target.value) })} />)}
              {row('attachments.max_mb', t('chat.files.settings.maxMb'), t('chat.files.settings.ceiling', { max: limit.max_mb }), <Input id="chat-attachments.max_mb" type="number" min={1} max={limit.max_mb}
                aria-invalid={bad === 'attachments.max_mb' || undefined} value={value.max_mb} onChange={e => onChange({ max_mb: Number(e.target.value) })} />)}
            </div>
            {row('attachments.field', t('chat.files.settings.field'), t('chat.files.settings.fieldHint'), <Select value={value.field} onValueChange={field => onChange({ field })}>
              <SelectTrigger className="w-full" id="chat-attachments.field" aria-invalid={bad === 'attachments.field' || undefined}><SelectValue placeholder={t('chat.settings.pickField')} /></SelectTrigger>
              <SelectContent>{[...new Set([value.field, ...lists])].filter(Boolean).map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent></Select>)}
          </>}
        </div>
  </>
}
