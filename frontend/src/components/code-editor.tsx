import { useEffect, useMemo, useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { javascript } from '@codemirror/lang-javascript'
import { autocompletion } from '@codemirror/autocomplete'
import { stateCompletions } from '@/lib/state-type'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { StateEffect, StateField, type EditorState } from '@codemirror/state'
import { Decoration, type DecorationSet, EditorView } from '@codemirror/view'
import { tags } from '@lezer/highlight'
import { cn } from '@/lib/utils'
import { editorTheme } from '@/lib/codemirror-theme'

const highlight = HighlightStyle.define([
  { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword, tags.moduleKeyword, tags.operatorKeyword], color: 'var(--syntax-key)' },
  { tag: [tags.string, tags.special(tags.string)], color: 'var(--syntax-string)' },
  { tag: tags.number, color: 'var(--info)' },
  { tag: [tags.bool, tags.null, tags.self], color: 'var(--warning)' },
  { tag: tags.comment, color: 'var(--muted-foreground)', fontStyle: 'italic' },
  { tag: [tags.function(tags.definition(tags.variableName)), tags.definition(tags.className)], fontWeight: '600' },
])

/** Marked line ranges (1-based, inclusive), e.g. the code of the node selected on the canvas. */
export type LineRange = [number, number]
const setMarks = StateEffect.define<LineRange[]>()
const mark = Decoration.line({ class: 'cm-node-mark' })
const markLines = (state: EditorState, ranges: LineRange[]): DecorationSet => {
  const lines = new Set<number>()
  for (const [a, b] of ranges) for (let i = Math.max(1, a); i <= Math.min(b, state.doc.lines); i++) lines.add(i)
  return Decoration.set([...lines].sort((x, y) => x - y).map(i => mark.range(state.doc.line(i).from)))
}
const marksField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update: (deco, tr) => tr.effects.reduce((d, e) => e.is(setMarks) ? markLines(tr.state, e.value) : d, deco.map(tr.changes)),
  provide: f => EditorView.decorations.from(f),
})
const markTheme = EditorView.theme({ '.cm-node-mark': { backgroundColor: 'color-mix(in oklch, var(--info) 16%, transparent)' } })

export type CodeLanguageId = 'python' | 'typescript'
const LABEL: Record<CodeLanguageId, string> = { python: 'Python', typescript: 'TypeScript' }

/** Source code with highlighting (Tool node Code mode, ; TypeScript ); same look as the JSON
 * editor. `fields` adds `state.` completions. */
export function CodeEditor({ value, onChange, readOnly, id, className, marks, language = 'python', fields }: {
  language?: CodeLanguageId
  fields?: { name: string; detail?: string }[]
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  id?: string
  className?: string
  marks?: LineRange[]  // highlighted and scrolled into view
}) {
  const [view, setView] = useState<EditorView | null>(null)
  const key = JSON.stringify(marks ?? [])
  useEffect(() => {
    if (!view) return
    const ranges: LineRange[] = JSON.parse(key)
    const first = ranges[0] && view.state.doc.lines >= ranges[0][0] ? view.state.doc.line(ranges[0][0]).from : null
    view.dispatch({ effects: [setMarks.of(ranges), ...(first === null ? [] : [EditorView.scrollIntoView(first, { y: 'start', yMargin: 24 })])] })
  }, [view, key, value])
  const fieldKey = JSON.stringify(fields ?? [])
  const extensions = useMemo(() => [
    language === 'typescript' ? javascript({ typescript: true }) : python(),
    ...(fieldKey !== '[]' ? [autocompletion({ override: [stateCompletions(JSON.parse(fieldKey))], icons: false })] : []),
    syntaxHighlighting(highlight),
    editorTheme,
    marksField,
    markTheme,
    EditorView.lineWrapping,  // a long line must not widen the config panel
    ...(id ? [EditorView.contentAttributes.of({ id, 'aria-label': LABEL[language], 'data-language': language })] : []),
  ], [id, language, fieldKey])
  return <div className={cn('min-h-0 min-w-0 overflow-hidden rounded-lg border bg-muted/30', className)}>
    <CodeMirror value={value} height="100%" theme="none" editable={!readOnly} readOnly={!!readOnly}
      basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: !readOnly, indentOnInput: true, tabSize: language === 'typescript' ? 2 : 4 }}
      extensions={extensions} onChange={onChange} onCreateEditor={setView} className="h-full text-xs" />
  </div>
}

/** The Python view of `CodeEditor` (the Code tab's export, ). */
export function PythonEditor(props: Omit<Parameters<typeof CodeEditor>[0], 'language'>) {
  return <CodeEditor {...props} language="python" />
}
