import { useTranslation } from 'react-i18next'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { TemplateEditor, type TemplateField } from './template-editor'
import { StateFieldPicker } from './state-field-action'
import { useConfirmDelete } from './use-confirm-delete'
import type { RecipeTarget } from '@/lib/browser-tools'

type Props = { data: Record<string, any>; fields: TemplateField[]; observations: string[]; recipe: boolean; readOnly?: boolean; onChange: (patch: Record<string, any>) => void }
export function BrowserMcpData({ data, fields, observations, recipe, readOnly, onChange }: Props) {
  const { t } = useTranslation(), confirm = useConfirmDelete(), args = data.arguments || {}, operation = data.tool
  const target: RecipeTarget = data.target || { observation_field: '', role: '', text: '' }, targets: Record<string, RecipeTarget> = data.targets || {}
  const literal = (id: string, label: string, value: string, set: (value: string) => void) => <div className="space-y-1.5"><Label htmlFor={id}>{t(label)}</Label><Input id={id} value={value} onChange={event => set(event.target.value)} /></div>
  const observation = (id: string, value: string, set: (value: string) => void) => <div className="space-y-1.5"><Label htmlFor={id}>{t('browserTools.observation')}</Label><StateFieldPicker id={id} options={observations} value={value} types={[]} onChange={set} /></div>
  const input = (name: string) => <div className="space-y-1.5"><Label htmlFor={`mcp-arg-${name}`}>{name}</Label><TemplateEditor singleLine id={`mcp-arg-${name}`} fields={fields} readOnly={readOnly} value={typeof args[name] === 'string' ? args[name] : args[name] === undefined ? '' : JSON.stringify(args[name])} onChange={value => onChange({ arguments: { ...args, [name]: value } })} /></div>
  return <div className="space-y-3" id="browser-mcp-data">
    <p className="text-xs text-muted-foreground">{t(recipe ? 'browserTools.selectorHelp' : 'browserTools.primitiveHelp')}</p>
    {recipe && ['click', 'fill'].includes(operation) ? <>
      {observation('recipe-observation', target.observation_field, observation_field => onChange({ target: { ...target, observation_field } }))}
      {literal('recipe-role', 'browserTools.role', target.role, role => onChange({ target: { ...target, role } }))}
      {literal('recipe-target-text', 'browserTools.targetText', target.text || '', text => onChange({ target: { ...target, text } }))}
      {operation === 'fill' && input('value')}
    </> : recipe && operation === 'extract' ? <>
      {observation('recipe-observation', Object.values(targets)[0]?.observation_field || '', observation_field => onChange({ targets: Object.fromEntries(Object.entries(targets).map(([name, selected]) => [name, { ...selected, observation_field }])) }))}
      {Object.entries(targets).map(([name, selected], index) => <div className="space-y-2 rounded-md border p-3" key={index} data-testid="recipe-extract-target">
        {literal(`recipe-extract-${index}-name`, 'browserTools.extractName', name, next => onChange({ targets: Object.fromEntries(Object.entries(targets).map(([key, value]) => [key === name ? next : key, value])) }))}
        {literal(`recipe-extract-${index}-role`, 'browserTools.role', selected.role, role => onChange({ targets: { ...targets, [name]: { ...selected, role } } }))}
        {literal(`recipe-extract-${index}-text`, 'browserTools.optionalText', selected.text || '', text => onChange({ targets: { ...targets, [name]: { ...selected, text: text || undefined } } }))}
        <Button variant="outline" type="button" onClick={() => confirm.ask({ name, title: t('browserTools.removeTargetTitle', { name }), onConfirm: () => onChange({ targets: Object.fromEntries(Object.entries(targets).filter(([key]) => key !== name)) }) })}><Trash2 />{t('browserTools.removeTarget')}</Button>
      </div>)}
      <Button variant="outline" disabled={Object.keys(targets).length >= 20} onClick={() => { let number = 1; while (`field${number}` in targets) number++; onChange({ targets: { ...targets, [`field${number}`]: { observation_field: Object.values(targets)[0]?.observation_field || observations.at(-1) || '', role: '' } } }) }}><Plus />{t('browserTools.addTarget')}</Button>
    </> : <>{(operation === 'navigate' ? ['url'] : ['click', 'fill', 'extract'].includes(operation) ? ['observation_id', ...(operation === 'extract' ? ['fields'] : ['element_id']), ...(operation === 'fill' ? ['value'] : [])] : []).map(name => <div key={name}>{input(name)}</div>)}</>}
    {confirm.dialog}
  </div>
}
