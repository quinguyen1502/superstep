/** Admin view of where Tool nodes in Code mode run: runtime, image, limits, and the risk of `subprocess`. */
import { Tip } from '@/components/tip'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCodeRuntime } from '@/lib/code-runtime'

export function CodeRuntimeCard() {
  const { t } = useTranslation(); const rt = useCodeRuntime()
  if (!rt) return null
  const variant = rt.code_runtime === 'subprocess' ? 'warning' : (rt.code_runtime === 'docker' || rt.code_runtime === 'remote') && rt.available ? 'success' : 'secondary'
  const row = (label: string, value: React.ReactNode, id?: string) => <div className="flex flex-wrap items-center gap-2 text-sm"><span className="w-32 text-muted-foreground">{label}</span><span id={id}>{value}</span></div>
  return <Card id="code-runtime-card"><CardHeader><CardTitle>{t('code.adminTitle')}</CardTitle><CardDescription>{t('code.adminIntro')}</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      {row(t('code.adminRuntime'), <Tip tip={rt.code_runtime === 'subprocess' ? t('code.notIsolatedTip') : null}><Badge variant={variant} id="code-runtime-value">{t(`code.runtimes.${rt.code_runtime}`)}</Badge></Tip>)}
      {rt.code_runtime === 'docker' && !rt.languages && row(t('code.adminImage'), <span className="font-mono text-xs">{rt.image}</span>)}
      {rt.code_runtime !== 'off' && row(t('code.adminLimits'), t('code.adminLimitsValue', { seconds: rt.limits.seconds, memory: rt.limits.memory, cpus: rt.limits.cpus, pids: rt.limits.pids }))}
      {rt.problem && <p className="text-xs text-muted-foreground" id="code-runtime-problem">{rt.problem}</p>}
      {rt.code_runtime !== 'off' && rt.languages && <div className="space-y-2 pt-2" id="code-runtime-languages">
        <div className="text-sm font-medium">{t('code.adminLanguages')}</div>
        {rt.languages.map(l => <div key={l.id} className="space-y-1 rounded-md border p-2" id={`code-language-row-${l.id}`}>
          <div className="flex flex-wrap items-center gap-2 text-sm"><span className="w-32 font-medium">{t(`code.languages.${l.id}`)}</span>
            <Badge variant={l.available ? 'success' : 'warning'} data-testid="code-language-status">{t(l.available ? 'code.languageReady' : 'code.languageNotReady')}</Badge>
            {rt.code_runtime === 'docker' && <span className="font-mono text-xs text-muted-foreground">{l.image}</span>}</div>
          <p className="text-xs text-muted-foreground">{l.packages.length ? t('code.adminPackages', { packages: l.packages.join(', ') }) : t('code.adminNoPackages')}</p>
          {l.problem && <p className="flex items-start gap-1.5 text-xs text-muted-foreground" data-testid="code-language-problem"><AlertTriangle className="mt-0.5 size-3 shrink-0 text-warning" />{l.problem}</p>}
        </div>)}
      </div>}
      {rt.code_runtime === 'subprocess' && <Alert variant="warning" id="code-runtime-risk"><ShieldAlert /><AlertDescription className="text-xs">{t('code.adminRisk')}</AlertDescription></Alert>}
    </CardContent></Card>
}
