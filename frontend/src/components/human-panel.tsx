import { useTranslation } from 'react-i18next'
import { UserCheck } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { HumanAnswer } from '@/components/human-answer'
import type { Trace } from '@/lib/trace'

/** Shown above the run timeline while a run waits at a Human node. */
export function HumanPanel({ waiting, onRespond }: { waiting: NonNullable<Trace['waiting']>; onRespond: (response: string) => void }) {
  const { t } = useTranslation()
  return <Alert id="human-panel" className="m-3 w-auto border-node-human/40 bg-node-human-muted">
    <UserCheck className="text-node-human" />
    <AlertTitle>{t('human.title')}</AlertTitle>
    <AlertDescription className="space-y-2">
      <div className="text-xs text-muted-foreground">{t('human.node', { label: waiting.label || waiting.node })}</div>
      {waiting.prompt && <p id="human-question" className="text-sm text-foreground whitespace-pre-wrap">{waiting.prompt}</p>}
      <HumanAnswer ids onRespond={onRespond} />
    </AlertDescription>
  </Alert>
}
