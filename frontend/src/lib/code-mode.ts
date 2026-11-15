/** The Tool node Mode select: one option per Code language, "code:python" / "code:typescript". The stored
 * model is unchanged: `mode: "code"` plus `data.language`; this maps between the two. */
import { languageInfo, type CodeRuntime } from '@/lib/code-runtime'

export type CodeLanguageId = 'python' | 'typescript'
export type ToolModeValue = 'function' | 'http' | `code:${CodeLanguageId}`
type ToolData = { mode?: string; language?: string; code?: string }

export const nodeLanguage = (d: ToolData): CodeLanguageId => (d.language === 'typescript' ? 'typescript' : 'python')

export function modeValue(d: ToolData): ToolModeValue {
  return d.mode === 'code' ? `code:${nodeLanguage(d)}` : d.mode === 'http' ? 'http' : 'function'
}

/** The Code languages to offer: those the server reports as available, plus the node's own (so it still shows). */
export function codeChoices(rt: CodeRuntime | null, d: ToolData): CodeLanguageId[] {
  const offered = rt?.languages ? rt.languages.filter(l => l.available).map(l => l.id) : ['python' as const]
  return d.mode === 'code' && !offered.includes(nodeLanguage(d)) ? [nodeLanguage(d), ...offered] : offered
}

/** The node data change for picking `value`, and whether edited code was kept (show the rewrite hint).
 * Untouched code (empty or the current language's starter) is swapped for the new language's starter. */
export function applyMode(d: ToolData, value: ToolModeValue, rt: CodeRuntime | null): { patch: ToolData; kept: boolean } {
  if (!value.startsWith('code:')) return { patch: { mode: value }, kept: false }
  const to = value.slice(5) as CodeLanguageId
  const code = d.code ?? ''
  const from = nodeLanguage(d)
  const untouched = !code.trim() || code === languageInfo(rt, from)?.starter
  const starter = languageInfo(rt, to)?.starter
  if (d.mode === 'code' && to === from) return { patch: {}, kept: false }
  if (untouched && starter !== undefined) return { patch: { mode: 'code', language: to, code: starter }, kept: false }
  return { patch: { mode: 'code', language: to }, kept: !untouched && to !== from }
}
