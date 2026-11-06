import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TemplateEditor, type TemplateField } from '@/components/template-editor'
import type { UrlBinding } from '@/lib/browser-tools'

/** Builder URLs are rendered once; model-filled URLs have no hidden fallback. */
export function BrowserUrlBinding({ id, value, fields, readOnly, onChange }: { id: string; value?: UrlBinding; fields: TemplateField[]; readOnly?: boolean; onChange: (value: UrlBinding) => void }) {
  const { t } = useTranslation(), source = value?.source || 'model'
  const [drafts, setDrafts] = useState<Partial<Record<UrlBinding['source'], string>>>({})
  const changeSource = (next: UrlBinding['source']) => {
    setDrafts(old => ({ ...old, [source]: value?.value || '' }))
    onChange(next === 'model' ? { source: next } : { source: next, value: drafts[next] || '' })
  }
  return <div className="space-y-2" data-testid="browser-url-binding">
    <Label htmlFor={`${id}-source`}>{t('browserTools.urlSource')}</Label>
    <Select value={source} disabled={readOnly} onValueChange={changeSource}><SelectTrigger id={`${id}-source`} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{(['model', 'fixed', 'state'] as const).map(item => <SelectItem value={item} key={item}>{t(`browserTools.sources.${item}`)}</SelectItem>)}</SelectContent></Select>
    <p className="text-xs text-muted-foreground">{t(`browserTools.sourceHelp.${source}`)}</p>
    {source !== 'model' && <div className="space-y-1.5"><Label htmlFor={`${id}-value`}>{t('field.url')}</Label>
      {source === 'state' ? <TemplateEditor id={`${id}-value`} singleLine fields={fields} readOnly={readOnly} value={value?.value || ''} onChange={next => onChange({ source, value: next })} />
        : <Input id={`${id}-value`} readOnly={readOnly} value={value?.value || ''} onChange={event => onChange({ source, value: event.target.value })} />}
      {!value?.value && <p className="text-xs text-destructive" role="alert">{t('browserTools.urlRequired')}</p>}
    </div>}
  </div>
}
