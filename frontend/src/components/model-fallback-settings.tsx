import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ModelPicker } from '@/components/model-picker'
import type { Credential } from '@/components/credentials-dialog'

type Policy = { credential_id: string; model: string }
export function ModelFallbackSettings({ value, creds, readOnly, onChange }: {
  value?: Policy; creds: Credential[]; readOnly?: boolean; onChange: (value: Policy | undefined) => void
}) {
  const { t } = useTranslation()
  return <div className="space-y-3 rounded-md border p-3" id="model-fallback-settings">
    <div className="flex items-center justify-between gap-2">
      <Label htmlFor="model-fallback-enabled">{t('modelFallback.enable')}</Label>
      <Switch id="model-fallback-enabled" checked={value != null} disabled={readOnly}
        onCheckedChange={enabled => onChange(enabled ? { credential_id: '', model: '' } : undefined)} />
    </div>
    {value != null && <>
      <div className="space-y-1.5"><Label htmlFor="model-fallback-credential">{t('modelFallback.credential')}</Label>
        <Select value={value.credential_id} disabled={readOnly} onValueChange={credential_id => onChange({ ...value, credential_id })}>
          <SelectTrigger id="model-fallback-credential" className="w-full"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
          <SelectContent>{creds.map(c => <SelectItem key={c.id} value={c.id}>{c.name} · {c.provider}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5"><Label htmlFor="model-fallback-model">{t('modelFallback.model')}</Label>
        <ModelPicker idp="model-fallback-model" credentialId={value.credential_id || undefined} value={value.model}
          onChange={model => onChange({ ...value, model })} />
      </div>
      <p className="text-xs text-muted-foreground">{t('modelFallback.hint')}</p>
    </>}
  </div>
}
