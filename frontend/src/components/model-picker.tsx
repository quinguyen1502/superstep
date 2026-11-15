import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { ListRestart, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { credentialModels } from '@/lib/providers'
import { useOnChange } from '@/lib/use-when'

/** Model field (; LLM node and knowledge-base embedding model): free text (manual entry always works) + models fetched from the chosen credential. */
export function ModelPicker({ credentialId, value, onChange, placeholder, idp = 'llm-model' }: { credentialId?: string; value: string; onChange: (v: string) => void; placeholder?: string; idp?: string }) {
  const { t } = useTranslation()
  const [models, setModels] = useState<string[] | null>(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  useOnChange(credentialId, () => { setModels(null); setErr('') })
  const load = async () => {
    if (!credentialId) return
    setBusy(true); setErr('')
    try { setModels((await credentialModels(credentialId)).models) } catch (e: any) { setModels(null); setErr(e.message) } finally { setBusy(false) }
  }
  return <div className="space-y-2">
    <div className="flex gap-2">
      <Input id={idp} className="font-mono text-xs" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
      <Tooltip><TooltipTrigger asChild><span><Button type="button" variant="outline" size="icon" id={`${idp}-load`} disabled={!credentialId || busy}
        aria-label={t('models.load')} onClick={load}><ListRestart /></Button></span></TooltipTrigger>
        <TooltipContent>{credentialId ? t('models.load') : t('models.needCredential')}</TooltipContent></Tooltip>
    </div>
    {models && (models.length
      ? <Select value={models.includes(value) ? value : ''} onValueChange={onChange}>
          <SelectTrigger className="w-full" id={`${idp}-select`}><SelectValue placeholder={t('models.choose', { count: models.length })} /></SelectTrigger>
          <SelectContent>{models.map(m => <SelectItem key={m} value={m} className="font-mono text-xs">{m}</SelectItem>)}</SelectContent></Select>
      : <p className="text-xs text-muted-foreground">{t('models.none')}</p>)}
    {err && <Alert variant="warning" id={`${idp}-error`}><TriangleAlert /><AlertDescription>{t('models.failed', { error: err })}</AlertDescription></Alert>}
  </div>
}
