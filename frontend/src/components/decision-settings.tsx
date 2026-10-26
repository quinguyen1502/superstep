/** Decision node settings (TASK-0050): a TypeSafe credential, the text Jev reads, and typed questions (choice, score, noul).
 * Removing a question, option or level edits the unsaved canvas, so it is undoable (Ctrl+Z) like deleting a node. */
import { useTranslation } from 'react-i18next'
import { Plus, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TemplateEditor } from '@/components/template-editor'
import type { Field } from '@/components/editor/meta'
import type { Credential } from '@/components/credentials-dialog'
import type { ProviderInfo } from '@/lib/providers'

type Option = { label: string; description?: string }
export type Question = { id: string; type: 'choice' | 'score' | 'noul'; instructions: string; options?: Option[]; levels?: string[]; field?: string }
type Data = { credential_id?: string; model?: string; text?: string; questions?: Question[]; output_field?: string }
type Props = { data: Data; fields: Field[]; creds: Credential[]; providers: ProviderInfo[]; readOnly?: boolean; onChange: (patch: Partial<Data>) => void }

const TYPES = ['choice', 'score', 'noul'] as const
/** The state field type that can hold each answer (backend engine/decisions.py FIELD_TYPES). */
const FIELD_TYPE: Record<Question['type'], string> = { choice: 'string', score: 'number', noul: 'number' }
const blank = (type: Question['type'], id: string, instructions = ''): Question =>
  type === 'choice' ? { id, type, instructions, options: [{ label: '', description: '' }, { label: '', description: '' }] }
    : type === 'score' ? { id, type, instructions, levels: ['', ''] } : { id, type, instructions }

function Row({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={htmlFor}>{label}</Label>{children}</div>
}

export function DecisionSettings({ data, fields, creds, providers, readOnly, onChange }: Props) {
  const { t } = useTranslation()
  const qs = data.questions || []
  const setQ = (i: number, patch: Partial<Question>) => onChange({ questions: qs.map((q, k) => k === i ? { ...q, ...patch } : q) })
  const kind = (c: Credential) => providers.find(p => p.id === c.provider)?.kind
  const usable = creds.filter(c => kind(c) === 'decision')
  const nextId = () => { let n = qs.length + 1; while (qs.some(q => q.id === `q${n}`)) n++; return `q${n}` }
  return <div className="space-y-3" id="decision-settings">
    <Row label={t('decision.credential')} htmlFor="decision-credential">
      <Select value={data.credential_id || 'none'} onValueChange={v => onChange({ credential_id: v === 'none' ? '' : v })}>
        <SelectTrigger className="w-full" id="decision-credential"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('decision.credentialNone')}</SelectItem>
          {usable.map(c => <SelectItem key={c.id} value={c.id}>{c.name} · {c.hint}</SelectItem>)}</SelectContent></Select>
      {!data.credential_id && <p className="text-[11px] text-muted-foreground" id="decision-mock-hint">{t('decision.mockHint')}</p>}
    </Row>
    <Row label={t('decision.model')} htmlFor="decision-model"><Input id="decision-model" value={data.model || ''} placeholder="jev-latest" onChange={e => onChange({ model: e.target.value })} /></Row>
    <Row label={t('decision.text', { field: '{{state.field}}' })}>
      <TemplateEditor id="decision-text" rows={3} fields={fields} readOnly={readOnly} value={data.text || ''} onChange={v => onChange({ text: v })} placeholder="{{state.message}}" />
    </Row>
    <div className="space-y-2">
      <p className="text-xs font-medium">{t('decision.questions')}</p>
      {qs.map((q, i) => <div key={i} className="space-y-2 rounded-md border bg-card p-2.5" id={`dq-${i}`}>
        <div className="flex items-end gap-2">
          <Row label={t('decision.id')} htmlFor={`dq-${i}-id`}><Input id={`dq-${i}-id`} className="font-mono text-xs" value={q.id} onChange={e => setQ(i, { id: e.target.value })} /></Row>
          <Row label={t('decision.type')} htmlFor={`dq-${i}-type`}>
            <Select value={q.type} onValueChange={v => setQ(i, { ...blank(v as Question['type'], q.id, q.instructions), field: '' })}>
              <SelectTrigger className="w-28" id={`dq-${i}-type`}><SelectValue /></SelectTrigger>
              <SelectContent>{TYPES.map(x => <SelectItem key={x} value={x}>{t(`decision.types.${x}`)}</SelectItem>)}</SelectContent></Select>
          </Row>
          <Button variant="ghost" size="icon" className="ml-auto shrink-0" id={`dq-${i}-remove`} aria-label={t('decision.removeQuestion', { id: q.id })}
            onClick={() => onChange({ questions: qs.filter((_, k) => k !== i) })}><Trash2 /></Button>
        </div>
        <p className="text-[11px] text-muted-foreground">{t(`decision.typeHint.${q.type}`)}</p>
        <Row label={t('decision.instructions')}>
          <TemplateEditor id={`dq-${i}-instructions`} rows={2} fields={fields} readOnly={readOnly} value={q.instructions || ''} onChange={v => setQ(i, { instructions: v })} />
        </Row>
        {q.type === 'choice' && <Row label={t('decision.options')}>
          {(q.options || []).map((o, j) => <div key={j} className="flex gap-1.5">
            <Input id={`dq-${i}-opt-${j}-label`} className="w-28 shrink-0" placeholder={t('decision.optionLabel')} value={o.label}
              onChange={e => setQ(i, { options: (q.options || []).map((x, k) => k === j ? { ...x, label: e.target.value } : x) })} />
            <Input id={`dq-${i}-opt-${j}-desc`} placeholder={t('decision.optionDesc')} value={o.description || ''}
              onChange={e => setQ(i, { options: (q.options || []).map((x, k) => k === j ? { ...x, description: e.target.value } : x) })} />
            <Button variant="ghost" size="icon" className="shrink-0" aria-label={t('decision.removeItem')} onClick={() => setQ(i, { options: (q.options || []).filter((_, k) => k !== j) })}><X /></Button>
          </div>)}
          <Button variant="outline" size="sm" id={`dq-${i}-add-option`} onClick={() => setQ(i, { options: [...(q.options || []), { label: '', description: '' }] })}><Plus />{t('decision.addOption')}</Button>
        </Row>}
        {q.type === 'score' && <Row label={t('decision.levels')}>
          {(q.levels || []).map((l, j) => <div key={j} className="flex gap-1.5">
            <span className="w-5 shrink-0 pt-2 text-right font-mono text-[11px] text-muted-foreground">{j}</span>
            <Input id={`dq-${i}-level-${j}`} placeholder={t('decision.levelPh')} value={l} onChange={e => setQ(i, { levels: (q.levels || []).map((x, k) => k === j ? e.target.value : x) })} />
            <Button variant="ghost" size="icon" className="shrink-0" aria-label={t('decision.removeItem')} onClick={() => setQ(i, { levels: (q.levels || []).filter((_, k) => k !== j) })}><X /></Button>
          </div>)}
          <Button variant="outline" size="sm" id={`dq-${i}-add-level`} onClick={() => setQ(i, { levels: [...(q.levels || []), ''] })}><Plus />{t('decision.addLevel')}</Button>
        </Row>}
      </div>)}
      <Button variant="outline" size="sm" id="dq-add" onClick={() => onChange({ questions: [...qs, blank('choice', nextId())] })}><Plus />{t('decision.addQuestion')}</Button>
    </div>
    <p className="text-[11px] text-muted-foreground" id="decision-hint">{t('decision.hint')}</p>
  </div>
}

/** Data tab (TASK-0121): the field each question's answer goes to, then the field for the whole result. */
export function DecisionData({ data, fields, onChange }: Pick<Props, 'data' | 'fields' | 'onChange'>) {
  const { t } = useTranslation()
  const qs = data.questions || []
  const plain = fields.filter(f => !f.reducer || f.reducer === 'replace')
  const setQ = (i: number, patch: Partial<Question>) => onChange({ questions: qs.map((q, k) => k === i ? { ...q, ...patch } : q) })
  return <div className="space-y-3" id="decision-data">
    {qs.map((q, i) => <Row key={q.id} label={t('decision.fieldFor', { id: q.id })} htmlFor={`dq-${i}-field`}>
      <Select value={q.field || 'none'} onValueChange={v => setQ(i, { field: v === 'none' ? '' : v })}>
        <SelectTrigger className="w-full" id={`dq-${i}-field`}><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('decision.fieldNone')}</SelectItem>
          {plain.filter(f => f.type === FIELD_TYPE[q.type]).map(f => <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>)}</SelectContent></Select>
    </Row>)}
    <Row label={t('decision.outputField')} htmlFor="decision-output">
      <Select value={data.output_field || 'none'} onValueChange={v => onChange({ output_field: v === 'none' ? '' : v })}>
        <SelectTrigger className="w-full" id="decision-output"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('decision.fieldNone')}</SelectItem>
          {plain.filter(f => f.type === 'object').map(f => <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>)}</SelectContent></Select>
    </Row>
  </div>
}
