/** A run's node steps (TASK-0085, DEC-0053), built as the shadcn Tool pattern on Trace: each node step is a plain
 *  TraceLine while it runs ("Running …"), and once it has output in the full mode a TraceCollapsible that opens to
 *  Code Blocks (input, output, error). Step names only ("labels") stay plain lines; "none" renders nothing. */
import { useTranslation } from 'react-i18next'
import { Trace, TraceCollapsible, TraceCollapsibleContent, TraceCollapsibleTrigger, TraceDescription, TraceIcon, TraceLine, TraceTitle } from '@/components/ui/trace'
import { CodeBlock, CodeBlockContent } from '@/components/ui/code-block'
import { META } from '@/components/editor/meta'
import { fmtMs } from '@/lib/trace'
import type { ChatStep, StepsMode } from '@/lib/chat'
import { Workflow } from 'lucide-react'
import { ChildSteps } from '@/components/run-trace'

const json = (v: unknown) => typeof v === 'string' ? v : JSON.stringify(v, null, 2)

function Line({ s }: { s: ChatStep }) {
  const { t } = useTranslation(); const I = META[s.type ?? '']?.icon ?? Workflow
  return <TraceLine status={s.status === 'error' ? 'error' : s.status === 'running' ? 'running' : undefined} data-testid="chat-step" data-status={s.status}>
    <TraceIcon><I /></TraceIcon><TraceTitle>{t(`chat.step.${s.status}`, { label: s.label })}</TraceTitle>
    {s.handoff_to && <TraceDescription data-testid="chat-step-handoff">{t('chat.step.handoff', { to: s.handoff_to })}</TraceDescription>}
    {s.duration_ms != null && <TraceDescription>{fmtMs(s.duration_ms)}</TraceDescription>}
  </TraceLine>
}

function Output({ label, value }: { label: string; value: unknown }) {
  return <div className="flex flex-col gap-1"><span className="text-xs text-muted-foreground">{label}</span>
    <CodeBlock size="sm"><CodeBlockContent wrap className="max-h-64">{json(value)}</CodeBlockContent></CodeBlock></div>
}

export function ChatSteps({ steps, mode }: { steps: ChatStep[]; mode: StepsMode }) {
  const { t } = useTranslation()
  if (mode === 'none' || !steps.length) return null
  return <Trace data-testid="chat-steps" data-mode={mode}>
    {steps.map((s, i) => mode === 'full' && s.status !== 'running'
      ? <TraceCollapsible key={`${s.node}-${i}`} defaultOpen={s.status === 'error' || undefined}>
          <TraceCollapsibleTrigger><Line s={s} /></TraceCollapsibleTrigger>
          <TraceCollapsibleContent><div className="flex flex-col gap-2 py-1" data-testid="chat-step-detail">
            {s.errors?.length ? <Output label={t('chat.step.errorDetail')} value={s.errors.join('\n')} /> : null}
            {s.input !== undefined && <Output label={t('chat.step.input')} value={s.input} />}
            {s.delta !== undefined && <Output label={t('chat.step.output')} value={s.delta} />}
            {s.child_run_id && <ChildSteps runId={s.child_run_id} name={s.label.split(' › ').pop()} className="ml-0" />}
          </div></TraceCollapsibleContent>
        </TraceCollapsible>
      : <Line key={`${s.node}-${i}`} s={s} />)}
  </Trace>
}
