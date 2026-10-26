import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

/** Blank field clears the setting. A typed number is stored as a number so the compiler can read it. */
function num(raw: string): number | undefined {
  const text = raw.trim()
  if (!text) return undefined
  const n = Number(text)
  return Number.isFinite(n) ? n : undefined
}

function Field({ id, label, value, onChange, step }: { id: string; label: string; value?: number; onChange: (v: number | undefined) => void; step?: string }) {
  return <div className="space-y-1.5">
    <Label htmlFor={id} className="text-xs text-muted-foreground">{label}</Label>
    <Input id={id} type="number" min={0} step={step ?? '1'} inputMode="decimal" value={value ?? ''} onChange={e => onChange(num(e.target.value))} />
  </div>
}

/** Retry, timeout, and cache for one node. Empty inputs mean the LangGraph default: off. */
export function NodeRuntime({ data, onChange }: { data: any; onChange: (patch: Record<string, unknown>) => void }) {
  const { t } = useTranslation()
  const retry = data.retry || {}
  const setRetry = (key: 'max_attempts' | 'initial_interval', value: number | undefined) => {
    const next = { ...retry, [key]: value }
    if (next.max_attempts === undefined) delete next.max_attempts
    if (next.initial_interval === undefined) delete next.initial_interval
    onChange({ retry: next.max_attempts === undefined && next.initial_interval === undefined ? undefined : next })
  }
  // the Config panel's Execution tab names the section (TASK-0121), so no heading of its own
  return <div className="space-y-3" id="node-runtime">
    <Field id="node-retry-attempts" label={t('editor.retryAttempts')} value={retry.max_attempts} onChange={v => setRetry('max_attempts', v)} />
    <Field id="node-retry-wait" label={t('editor.retryWait')} value={retry.initial_interval} step="0.1" onChange={v => setRetry('initial_interval', v)} />
    <Field id="node-timeout" label={t('editor.nodeTimeout')} value={data.timeout} step="0.1" onChange={v => onChange({ timeout: v })} />
    <Field id="node-cache-ttl" label={t('editor.cacheTtl')} value={data.cache_ttl} onChange={v => onChange({ cache_ttl: v })} />
    <p className="text-[11px] text-muted-foreground">{t('editor.runtimeHint')}</p>
  </div>
}
