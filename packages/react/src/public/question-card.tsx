import { useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ChatQuestion } from '@superstep/sdk/chat'
import { Button } from '../ui/button.js'
import { Input } from '../ui/input.js'
import { Textarea } from '../ui/textarea.js'
import { Label } from '../ui/label.js'
import { Checkbox } from '../ui/checkbox.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select.js'
import { Item, ItemContent, ItemTitle, ItemDescription, ItemActions } from '../ui/item.js'
import { useChatController } from './provider.js'
import type { ChatController } from './use-chat.js'

type Field = { name: string; label: string; type: string; required: boolean; placeholder?: string; options?: string[] }
function fieldsOf(value: unknown): Field[] {
  if (!Array.isArray(value)) return []
  return value.slice(0, 32).flatMap(item => {
    if (!item || typeof item !== 'object' || typeof item.name !== 'string' || !/^[\w-]{1,80}$/.test(item.name) || ['__proto__','prototype','constructor'].includes(item.name)) return []
    return [{ name: item.name, label: typeof item.label === 'string' ? item.label : item.name, type: typeof item.type === 'string' ? item.type : 'text', required: item.required === true,
      placeholder: typeof item.placeholder === 'string' ? item.placeholder : undefined, options: Array.isArray(item.options) ? item.options.filter((x: unknown) => typeof x === 'string').slice(0,100) : undefined }]
  })
}
export interface QuestionCardProps { chat?: ChatController; question?: ChatQuestion; showPrompt?: boolean }
export function QuestionCard({ chat: explicit, question: supplied, showPrompt = true }: QuestionCardProps) {
  const chat = useChatController(explicit), question = supplied ?? chat.question, { t } = useTranslation(), id = useId()
  const [values, setValues] = useState<Record<string, string | boolean>>({}), [text, setText] = useState('')
  useEffect(() => { setValues({}); setText('') }, [question])
  if (!question || !chat.waiting) return null
  if (chat.answeredBy === 'reviewer') return <p role="status" className="px-4 py-3 text-sm text-muted-foreground">{t('chat.toolkit.waitReviewer')}</p>
  const fields = fieldsOf(question.fields), kind = question.kind ?? question.input_type ?? 'text'
  const choices = (Array.isArray(question.options) ? question.options : Array.isArray(question.choices) ? question.choices : []).filter((x): x is string => typeof x === 'string').slice(0,100)
  const answer = (value: string | Record<string, unknown>) => { void chat.answer(value).catch(() => {}) }
  const valid = fields.every(f => !f.required || (f.type === 'checkbox' || f.type === 'boolean' ? true : String(values[f.name] ?? '').trim()))
  return <Item variant="outline" size="sm" className="mx-3 mb-2 w-auto" data-testid="question-card">
    <ItemContent><ItemTitle>{question.label || t('chat.needsAnswer')}</ItemTitle>
      {showPrompt && question.prompt && <ItemDescription>{question.prompt}</ItemDescription>}
      {fields.length ? <form className="space-y-3" onSubmit={e => { e.preventDefault(); if (!valid) return
        answer(Object.fromEntries(fields.filter(f => f.type !== 'number' || String(values[f.name] ?? '').trim()).map(f => [f.name, f.type === 'number' ? Number(values[f.name]) : f.type === 'boolean' || f.type === 'checkbox' ? values[f.name] === true : values[f.name] ?? '']))) }}>
        {fields.map(f => <div key={f.name} className="space-y-1.5"><Label htmlFor={`${id}-${f.name}`}>{f.label}</Label>
          {['boolean','checkbox'].includes(f.type) ? <Checkbox id={`${id}-${f.name}`} checked={values[f.name] === true} disabled={chat.busy} onCheckedChange={v => setValues(x => ({ ...x, [f.name]: v === true }))} />
            : f.options?.length ? <Select value={String(values[f.name] ?? '')} disabled={chat.busy} onValueChange={v => setValues(x => ({ ...x, [f.name]: v }))}>
              <SelectTrigger id={`${id}-${f.name}`}><SelectValue placeholder={t('chat.toolkit.choose')} /></SelectTrigger><SelectContent>{f.options.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent></Select>
            : f.type === 'textarea' ? <Textarea id={`${id}-${f.name}`} value={String(values[f.name] ?? '')} maxLength={4000} disabled={chat.busy} required={f.required} placeholder={f.placeholder} onChange={e => setValues(x => ({ ...x, [f.name]: e.target.value }))} />
            : <Input id={`${id}-${f.name}`} type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'} value={String(values[f.name] ?? '')} maxLength={4000} disabled={chat.busy} required={f.required} placeholder={f.placeholder} onChange={e => setValues(x => ({ ...x, [f.name]: e.target.value }))} />}</div>)}
        <Button type="submit" disabled={chat.busy || !valid}>{t('chat.toolkit.answer')}</Button>
      </form> : choices.length ? <ItemActions className="flex-wrap">{choices.map(v => <Button key={v} variant="outline" disabled={chat.busy} onClick={() => answer(v)}>{v}</Button>)}</ItemActions>
        : ['approval','boolean','confirm'].includes(kind) ? <ItemActions><Button variant="outline" disabled={chat.busy} onClick={() => answer('rejected')}>{t('human.reject')}</Button><Button disabled={chat.busy} onClick={() => answer('approved')}>{t('human.approve')}</Button></ItemActions>
        : <form className="flex flex-col gap-2" onSubmit={e => { e.preventDefault(); if (text.trim()) answer(text.trim()) }}>
          <Label htmlFor={`${id}-answer`}>{t('chat.toolkit.answerLabel')}</Label><Textarea id={`${id}-answer`} value={text} maxLength={4000} disabled={chat.busy} placeholder={question.placeholder ?? undefined} onChange={e => setText(e.target.value)} />
          <ItemActions><Button variant="outline" type="button" disabled={chat.busy} onClick={() => answer('rejected')}>{t('human.reject')}</Button><Button variant="outline" type="button" disabled={chat.busy} onClick={() => answer('approved')}>{t('human.approve')}</Button><Button type="submit" disabled={chat.busy || !text.trim()}>{t('chat.toolkit.answer')}</Button></ItemActions>
        </form>}
    </ItemContent>
  </Item>
}
