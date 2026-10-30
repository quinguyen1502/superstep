/** "Include attachments" for an LLM or Agent node (TASK-0177, REQ-0077): a switch, and the list field that holds the
 *  chat's files (default `files`). Documents reach the model as text, images as images when the model can see them. */
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { TemplateField } from '@/components/template-editor'

const DEFAULT_FIELD = 'files'

export function IncludeAttachments({ idp, data: d, fields, readOnly, onChange }: { idp: string; data: Record<string, any>; fields: TemplateField[]
  readOnly?: boolean; onChange: (p: Record<string, unknown>) => void }) {
  const { t } = useTranslation()
  const field = d.attachments_field || DEFAULT_FIELD
  const lists = [...new Set([field, ...fields.filter(f => f.type === 'list').map(f => f.name)])]
  return <div className="grid gap-2" id={`${idp}-attachments`}>
    <div className="flex items-center gap-2">
      <Switch id={`${idp}-include-attachments`} size="sm" checked={!!d.include_attachments} disabled={readOnly}
        onCheckedChange={c => onChange({ include_attachments: c === true || undefined })} />
      <Label htmlFor={`${idp}-include-attachments`} className="text-xs font-normal">{t('chat.files.include')}</Label>
    </div>
    <p className="text-[11px] text-muted-foreground">{t('chat.files.includeHint')}</p>
    {d.include_attachments && <div className="grid gap-1.5"><Label htmlFor={`${idp}-attachments-field`} className="text-xs">{t('chat.files.includeField')}</Label>
      <Select value={field} disabled={readOnly} onValueChange={v => onChange({ attachments_field: v === DEFAULT_FIELD ? undefined : v })}>
        <SelectTrigger className="w-full" id={`${idp}-attachments-field`}><SelectValue /></SelectTrigger>
        <SelectContent>{lists.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent></Select></div>}
  </div>
}
