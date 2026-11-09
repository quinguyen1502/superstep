/** Tool node Code mode: the source (Python or TypeScript ), what the server
 * provides for that language, and Test with sample state. */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, FlaskConical, Info, Loader2, Lock, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { HandbookLink } from '@/components/handbook-link'
import { Button } from '@/components/ui/button'
import { JsonView } from '@/components/json-view'
import { CodeEditor, type CodeLanguageId } from '@/components/code-editor'
import { api } from '@/lib/api'
import { errorText } from '@/lib/i18n'
import { codeOffKey, languageInfo, type CodeRuntime, type CodeTestResult } from '@/lib/code-runtime'
import { stateFields, stateType, type StateField } from '@/lib/state-type'

/** stdout and traceback of one call; shared by the test result and the trace detail. */
export function CodeConsole({ stdout, traceback, id }: { stdout?: string; traceback?: string; id?: string }) {
  const { t } = useTranslation()
  if (!stdout && !traceback) return null
  return <div className="space-y-2" id={id}>
    {stdout && <div className="space-y-1"><div className="text-[11px] font-medium text-muted-foreground">{t('code.stdout')}</div>
      <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-2 font-mono text-[11px]" data-testid="code-stdout">{stdout}</pre></div>}
    {traceback && <div className="space-y-1"><div className="text-[11px] font-medium text-muted-foreground">{t('code.traceback')}</div>
      <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-md border border-destructive/40 bg-destructive/5 p-2 font-mono text-[11px]" data-testid="code-traceback">{traceback}</pre></div>}
  </div>
}

function sample(input: string): Record<string, unknown> {
  try { const v = JSON.parse(input); return v && typeof v === 'object' && !Array.isArray(v) ? v : {} } catch { return {} }
}

export function CodeSettings({ value, onChange, runtime, canWrite, editable, input, nodeId, timeout, language = 'python', kept = false, fields = [] }: {
  value: string; onChange: (v: string) => void; runtime: CodeRuntime | null; canWrite: boolean; editable: boolean
  input: string; nodeId: string; timeout?: number
  language?: CodeLanguageId; kept?: boolean; fields?: StateField[]
}) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false); const [result, setResult] = useState<CodeTestResult | null>(null); const [error, setError] = useState('')
  const info = languageInfo(runtime, language)
  const ready = !!runtime?.available && !!info?.available
  const packages = language === 'typescript'
    ? (info?.packages.length ? t('code.tsPackages', { packages: info.packages.join(', ') }) : t('code.tsNoPackages'))
    : t('code.packages', { packages: [t('code.stdlib'), ...(info?.packages ?? [])].join(', ') })
  const test = async () => {
    setBusy(true); setError(''); setResult(null)
    try { setResult(await api<CodeTestResult>('/api/code/test', { method: 'POST', json: { source: value, state: sample(input), node: nodeId, language, ...(timeout ? { timeout } : {}) } })) }
    catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="space-y-2" id="code-settings">
    {runtime?.code_runtime === 'subprocess' && <Alert variant="warning" id="code-not-isolated"><ShieldAlert />
      <AlertDescription className="text-xs">{t('code.notIsolated')}</AlertDescription></Alert>}
    {runtime && !ready && <Alert variant="warning" id="code-runtime-off"><AlertTriangle />
      <AlertDescription className="space-y-1 text-xs"><p>{runtime.code_runtime === 'off' ? t(codeOffKey(runtime))
        : !info ? t('code.languageOff', { language: t(`code.languages.${language}`) })
        : t('code.unavailable', { problem: info.problem || runtime.problem || '' })}</p>
        <p>{t('code.runtimeHelp')}{' '}<HandbookLink id="code-runtime-guide" page="operate/code-runtime" label={t('docs.setupGuide')} ariaLabel={t('docs.codeRuntimeAria')} /></p>
      </AlertDescription></Alert>}
    {kept && <p className="text-[11px] text-muted-foreground" id="code-language-kept">{t('code.languageKept', { language: t(`code.languages.${language}`) })}</p>}
    {language === 'typescript' && <div className="space-y-1" id="code-state-type-box">
      <div className="text-[11px] font-medium text-muted-foreground">{t('code.stateType')}</div>
      <pre className="max-h-32 overflow-auto rounded-md border bg-muted/40 p-2 font-mono text-[11px]" id="code-state-type">{stateType(fields)}</pre>
      <p className="text-[11px] text-muted-foreground">{t('code.stateTypeHint')}</p></div>}
    {!canWrite && <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground" id="code-read-only"><Lock className="mt-0.5 size-3 shrink-0" />{t('code.readOnly')}</p>}
    <CodeEditor id="code-source" className="h-64" language={language} fields={stateFields(fields, language)} value={value} onChange={onChange} readOnly={!editable || !canWrite} />
    {runtime && <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground" id="code-packages"><Info className="mt-0.5 size-3 shrink-0" />
      {packages} {t('code.limits', { seconds: runtime.limits.seconds, memory: runtime.limits.memory })}</p>}
    {canWrite && <Button type="button" variant="outline" size="sm" id="code-test" disabled={busy || !ready || !value.trim()} onClick={test}>
      {busy ? <Loader2 className="animate-spin" /> : <FlaskConical />}{t('code.test')}</Button>}
    {canWrite && <p className="text-[11px] text-muted-foreground">{t('code.testHint')}</p>}
    {error && <Alert variant="destructive" id="code-test-error"><AlertTriangle /><AlertDescription className="text-xs break-words">{error}</AlertDescription></Alert>}
    {result && <div className="space-y-2 rounded-md border p-2" id="code-test-result">
      {result.ok
        ? <div className="space-y-1"><div className="text-[11px] font-medium text-muted-foreground">{t('code.result', { ms: Math.round(result.duration_ms ?? 0) })}</div><JsonView value={result.value} /></div>
        : <Alert variant="destructive"><AlertTriangle /><AlertDescription className="text-xs break-words" id="code-test-failure">{result.error ? errorText(result.error) : t('trace.error')}</AlertDescription></Alert>}
      <CodeConsole stdout={result.stdout} traceback={result.traceback} />
    </div>}
  </div>
}
