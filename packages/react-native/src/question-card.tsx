import { useEffect, useState } from 'react'
import { Pressable, Switch, Text, TextInput, View } from 'react-native'
import type { ChatQuestion } from '@superstep/sdk/chat'
import { text, type ChatLocale } from './labels.js'
import { themeOf, type ChatTheme } from './theme.js'
import type { ChatController } from './use-chat.js'

type Field = { name: string; label: string; type: string; required: boolean; placeholder?: string; options?: string[] }
type Answer = string | Record<string, unknown> | number | boolean

export interface QuestionCardProps {
  chat: {
    question: ChatController['question']
    waiting: boolean
    busy: boolean
    answeredBy?: string | null
    answer: (response: string | Record<string, unknown> | number | boolean) => Promise<unknown>
  }
  locale?: ChatLocale
  theme?: Partial<ChatTheme>
}

const blocked = new Set(['__proto__', 'prototype', 'constructor'])

export function fieldsOf(value: unknown): Field[] {
  if (!Array.isArray(value)) return []
  return value.slice(0, 32).flatMap(item => {
    if (!item || typeof item !== 'object') return []
    const record = item as Record<string, unknown>
    if (typeof record.name !== 'string' || !/^[\w-]{1,80}$/.test(record.name) || blocked.has(record.name)) return []
    return [{
      name: record.name,
      label: typeof record.label === 'string' ? record.label : record.name,
      type: typeof record.type === 'string' ? record.type : 'text',
      required: record.required === true,
      placeholder: typeof record.placeholder === 'string' ? record.placeholder : undefined,
      options: Array.isArray(record.options) ? record.options.filter((option): option is string => typeof option === 'string').slice(0, 100) : undefined,
    }]
  })
}

function choicesOf(question: ChatQuestion): string[] {
  const raw = Array.isArray(question.options) ? question.options : Array.isArray(question.choices) ? question.choices : []
  return raw.filter((option): option is string => typeof option === 'string').slice(0, 100)
}

function fieldValue(field: Field, raw: string | boolean | undefined): unknown {
  if (field.type === 'boolean' || field.type === 'checkbox') return raw === true
  const value = String(raw ?? '').trim()
  if (field.type === 'number') return value && Number.isFinite(Number(value)) ? Number(value) : undefined
  return value
}

export function QuestionCard({ chat, locale, theme }: QuestionCardProps) {
  const colors = themeOf(theme)
  const question = chat.question
  const [values, setValues] = useState<Record<string, string | boolean>>({})
  const [draft, setDraft] = useState('')
  useEffect(() => { setValues({}); setDraft('') }, [question])
  if (!question || !chat.waiting) return null
  if (chat.answeredBy === 'reviewer') {
    return <Text accessibilityRole="text" style={{ color: colors.muted, padding: 12 }}>{text(locale, 'waitingReviewer')}</Text>
  }
  const fields = fieldsOf(question.fields)
  const kind = question.kind ?? question.input_type ?? 'text'
  const choices = choicesOf(question)
  const answer = (value: Answer) => { void chat.answer(value).catch(() => {}) }
  const valid = fields.every(field => {
    if (!field.required || field.type === 'checkbox' || field.type === 'boolean') return true
    const value = fieldValue(field, values[field.name])
    return value !== undefined && value !== ''
  })
  const button = (label: string, onPress: () => void, filled = false, blocked = false) => (
    <Pressable
      key={label}
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={chat.busy || blocked}
      onPress={onPress}
      style={{ borderWidth: 1, borderColor: colors.border, borderRadius: colors.radius, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: filled ? colors.accent : colors.background }}
    >
      <Text style={{ color: filled ? colors.userText : colors.foreground }}>{label}</Text>
    </Pressable>
  )
  return <View testID="question-card" style={{ margin: 12, padding: 12, borderWidth: 1, borderColor: colors.border, borderRadius: colors.radius, gap: 8 }}>
    <Text style={{ color: colors.foreground, fontWeight: '700' }}>{question.label || text(locale, 'needsAnswer')}</Text>
    {!!question.prompt && <Text style={{ color: colors.muted }}>{question.prompt}</Text>}
    {fields.length ? <View style={{ gap: 8 }}>
      {fields.map(field => {
        const id = `field-${field.name}`
        return <View key={field.name} style={{ gap: 4 }}>
          <Text nativeID={id} style={{ color: colors.foreground }}>{field.label}</Text>
          {field.type === 'boolean' || field.type === 'checkbox'
            ? <Switch
                accessibilityLabel={field.label}
                value={values[field.name] === true}
                disabled={chat.busy}
                onValueChange={value => setValues(current => ({ ...current, [field.name]: value }))}
              />
            : field.options?.length
              ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {field.options.map(option => button(option, () => setValues(current => ({ ...current, [field.name]: option })), values[field.name] === option))}
                </View>
              : <TextInput
                  accessibilityLabel={field.label}
                  accessibilityHint={field.required ? text(locale, 'required') : undefined}
                  value={String(values[field.name] ?? '')}
                  editable={!chat.busy}
                  maxLength={4000}
                  multiline={field.type === 'textarea'}
                  keyboardType={field.type === 'number' ? 'numeric' : 'default'}
                  placeholder={field.placeholder}
                  placeholderTextColor={colors.muted}
                  onChangeText={value => setValues(current => ({ ...current, [field.name]: value }))}
                  style={{ borderWidth: 1, borderColor: colors.border, borderRadius: colors.radius, padding: 8, color: colors.foreground, fontSize: colors.fontSize }}
                />}
        </View>
      })}
      {button(text(locale, 'answer'), () => {
        const body: Record<string, unknown> = {}
        for (const field of fields) {
          const value = fieldValue(field, values[field.name])
          if (field.type === 'number' && value === undefined) continue
          body[field.name] = value ?? ''
        }
        answer(body)
      }, true, !valid)}
    </View> : choices.length ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      {choices.map(choice => button(choice, () => answer(choice)))}
    </View> : ['approval', 'boolean', 'confirm'].includes(kind) ? <View style={{ flexDirection: 'row', gap: 8 }}>
      {button(text(locale, 'reject'), () => answer('rejected'))}
      {button(text(locale, 'approve'), () => answer('approved'), true)}
    </View> : <View style={{ gap: 8 }}>
      <Text style={{ color: colors.foreground }}>{text(locale, 'answerLabel')}</Text>
      <TextInput
        accessibilityLabel={text(locale, 'answerLabel')}
        value={draft}
        editable={!chat.busy}
        maxLength={4000}
        multiline
        placeholder={question.placeholder ?? undefined}
        placeholderTextColor={colors.muted}
        onChangeText={setDraft}
        style={{ borderWidth: 1, borderColor: colors.border, borderRadius: colors.radius, padding: 8, color: colors.foreground, fontSize: colors.fontSize, minHeight: 72 }}
      />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {button(text(locale, 'reject'), () => answer('rejected'))}
        {button(text(locale, 'approve'), () => answer('approved'))}
        {button(text(locale, 'answer'), () => answer(draft.trim()), true, !draft.trim())}
      </View>
    </View>}
  </View>
}
