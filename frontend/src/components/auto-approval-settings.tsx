import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Sparkles, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ModelPicker } from '@/components/model-picker'
import { api } from '@/lib/api'
import { AUTO_MODES, DEFAULT_CAP, DEFAULT_MIN, MAX_CAP, MAX_RULES, RULE_EFFECTS, RULE_OPS, pct, type AutoPolicy, type AutoRule, type WorkflowAuto } from '@/lib/auto-approval'

type Cred = { id: string; name: string; provider: string; hint?: string }

/** AI review of approvals (TASK-0188, REQ-0081): shared by the Human node and an Agent's tool approval. Only the
 * workflow owner or an admin may choose "auto" (owner decision 3); editors may choose "suggest". The judge is any chat
 * credential (decision 4). The agreement rate comes from suggest mode (decision 1). */
export function AutoApprovalSettings({ idp, value, wid, creds, canAuto, readOnly, onChange }: {
  idp: string; value?: AutoPolicy; wid?: string | null; creds: Cred[]; canAuto: boolean; readOnly?: boolean; onChange: (v: AutoPolicy | undefined) => void }) {
  const { t } = useTranslation(); const v = value || {}; const mode = v.mode || 'off'
  const set = (patch: Partial<AutoPolicy>) => onChange({ ...v, ...patch })
  const judge = v.judge || {}
  const rules = v.rules || []
  const setRule = (i: number, patch: Partial<AutoRule>) => set({ rules: rules.map((r, j) => j === i ? { ...r, ...patch } : r) })
  const [info, setInfo] = useState<WorkflowAuto | null>(null)
  useEffect(() => { if (wid && mode !== 'off') api<WorkflowAuto>(`/api/approvals/auto/workflows/${wid}`).then(setInfo).catch(() => setInfo(null)) }, [wid, mode])
  const lockedAuto = mode === 'auto' && !canAuto
  const choose = (m: string) => onChange(m === 'off' ? (value ? { ...v, mode: 'off' } : undefined)
    : { min_confidence: DEFAULT_MIN, max_per_day: DEFAULT_CAP, notify: true, ...v, mode: m as AutoPolicy['mode'] })
  return <div className="space-y-3" id={`${idp}-auto`}>
    <Separator />
    <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground"><Sparkles className="size-3.5" />{t('aiReview.title')}</div>
    <div className="space-y-1.5"><Label htmlFor={`${idp}-auto-mode`} className="text-xs text-muted-foreground">{t('aiReview.mode')}</Label>
      <Select value={mode} onValueChange={choose} disabled={readOnly || lockedAuto}>
        <SelectTrigger className="w-full" id={`${idp}-auto-mode`}><SelectValue /></SelectTrigger>
        <SelectContent>{AUTO_MODES.map(m => <SelectItem key={m} value={m} id={`${idp}-auto-mode-${m}`} disabled={m === 'auto' && !canAuto}>{t(`aiReview.modes.${m}`)}</SelectItem>)}</SelectContent></Select>
      <p className="text-xs text-muted-foreground" id={`${idp}-auto-mode-help`}>{t(`aiReview.modeHelp.${mode}`)}</p>
      {!canAuto && <p className="text-xs text-muted-foreground" id={`${idp}-auto-owner-only`}>{t('aiReview.autoOwnerOnly')}</p>}</div>
    {mode !== 'off' && <>
      <div className="space-y-1.5"><Label htmlFor={`${idp}-auto-credential`} className="text-xs text-muted-foreground">{t('aiReview.credential')}</Label>
        <Select value={judge.credential_id || 'none'} disabled={readOnly} onValueChange={c => set({ judge: { ...judge, credential_id: c === 'none' ? '' : c } })}>
          <SelectTrigger className="w-full" id={`${idp}-auto-credential`}><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="none" disabled>{t('aiReview.credentialPick')}</SelectItem>
            {creds.map(c => <SelectItem key={c.id} value={c.id}>{c.name} · {c.provider} {c.hint}</SelectItem>)}</SelectContent></Select>
        {!creds.length && <p className="text-xs text-muted-foreground">{t('editor.credentialNone')}</p>}</div>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('field.model')}</Label>
        <ModelPicker idp={`${idp}-auto-model`} credentialId={judge.credential_id || undefined} value={judge.model || ''} onChange={m => set({ judge: { ...judge, model: m } })} /></div>
      <div className="space-y-1.5"><Label htmlFor={`${idp}-auto-instructions`} className="text-xs text-muted-foreground">{t('aiReview.instructions')}</Label>
        <Textarea id={`${idp}-auto-instructions`} rows={3} className="text-xs" readOnly={readOnly} value={judge.instructions || ''} placeholder={t('aiReview.instructionsPh')}
          onChange={e => set({ judge: { ...judge, instructions: e.target.value } })} /></div>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1.5"><Label htmlFor={`${idp}-auto-min`} className="text-xs text-muted-foreground">{t('aiReview.minConfidence')}</Label>
          <Input id={`${idp}-auto-min`} type="number" min={0} max={1} step={0.05} className="text-xs" readOnly={readOnly} value={v.min_confidence ?? DEFAULT_MIN}
            onChange={e => set({ min_confidence: e.target.value === '' ? undefined : Number(e.target.value) })} /></div>
        <div className="space-y-1.5"><Label htmlFor={`${idp}-auto-cap`} className="text-xs text-muted-foreground">{t('aiReview.cap')}</Label>
          <Input id={`${idp}-auto-cap`} type="number" min={1} max={MAX_CAP} inputMode="numeric" className="text-xs" readOnly={readOnly} value={v.max_per_day ?? DEFAULT_CAP}
            onChange={e => set({ max_per_day: e.target.value === '' ? undefined : parseInt(e.target.value, 10) })} /></div>
      </div>
      {mode === 'auto' && <div className="flex items-center gap-2"><Switch id={`${idp}-auto-notify`} size="sm" disabled={readOnly} checked={v.notify !== false} onCheckedChange={c => set({ notify: c })} />
        <Label htmlFor={`${idp}-auto-notify`} className="text-xs font-normal">{t('aiReview.notify')}</Label></div>}
      <div className="space-y-2" id={`${idp}-auto-rules`}>
        <Label className="text-xs text-muted-foreground">{t('aiReview.rules')}</Label>
        <p className="text-xs text-muted-foreground">{t('aiReview.rulesHelp')}</p>
        {rules.map((r, i) => <div key={i} className="space-y-1.5 rounded-md border p-2" data-testid="auto-rule">
          <div className="flex gap-2">
            <Input aria-label={t('aiReview.ruleField')} className="flex-1 font-mono text-xs" readOnly={readOnly} value={r.field} placeholder="args.amount" onChange={e => setRule(i, { field: e.target.value.trim() })} />
            {!readOnly && <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" aria-label={t('aiReview.ruleRemove')} onClick={() => set({ rules: rules.filter((_, j) => j !== i) })}><Trash2 /></Button></TooltipTrigger>
              <TooltipContent>{t('aiReview.ruleRemove')}</TooltipContent></Tooltip>}
          </div>
          <div className="flex gap-2">
            <Select value={r.op} disabled={readOnly} onValueChange={op => setRule(i, { op: op as AutoRule['op'] })}>
              <SelectTrigger className="flex-1" aria-label={t('aiReview.ruleOp')}><SelectValue /></SelectTrigger>
              <SelectContent>{RULE_OPS.map(o => <SelectItem key={o} value={o}>{t(`aiReview.ops.${o}`)}</SelectItem>)}</SelectContent></Select>
            {r.op !== 'empty' && <Input aria-label={t('aiReview.ruleValue')} className="flex-1 text-xs" readOnly={readOnly} value={r.value ?? ''}
              onChange={e => setRule(i, { value: (r.op === 'gt' || r.op === 'lt') && e.target.value !== '' && !isNaN(Number(e.target.value)) ? Number(e.target.value) : e.target.value })} />}
          </div>
          <Select value={r.effect} disabled={readOnly} onValueChange={x => setRule(i, { effect: x as AutoRule['effect'] })}>
            <SelectTrigger className="w-full" aria-label={t('aiReview.ruleEffect')}><SelectValue /></SelectTrigger>
            <SelectContent>{RULE_EFFECTS.map(x => <SelectItem key={x} value={x}>{t(`aiReview.effects.${x}`)}</SelectItem>)}</SelectContent></Select>
        </div>)}
        {!readOnly && rules.length < MAX_RULES && <Button variant="outline" size="sm" id={`${idp}-auto-add-rule`}
          onClick={() => set({ rules: [...rules, { field: 'args.', op: 'gt', value: '', effect: 'human' }] })}><Plus />{t('aiReview.ruleAdd')}</Button>}
      </div>
      {info?.stats && <p className="text-xs text-muted-foreground" id={`${idp}-auto-agreement`}>{info.stats.agreement == null
        ? t('aiReview.agreementNone') : t('aiReview.agreement', { rate: pct(info.stats.agreement), n: info.stats.agreed + info.stats.disagreed, days: info.stats.days })}</p>}
      {(info?.paused || info?.org_paused || info?.enabled === false) && <p className="text-xs text-muted-foreground" id={`${idp}-auto-paused`}>{t('aiReview.pausedHint')}</p>}
    </>}
  </div>
}
