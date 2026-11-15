/** The workflow's state schema as a TypeScript type: shown above a TypeScript Code node and used for
 * `state.` completions. Deno only strips types, so `State` needs no declaration in the node's code. */
import type { CompletionContext } from '@codemirror/autocomplete'
export type StateField = { name: string; type?: string }

const TS_TYPES: Record<string, string> = {
  string: 'string', number: 'number', integer: 'number', boolean: 'boolean', object: 'Record<string, unknown>', list: 'unknown[]',
}
const IDENT = /^[A-Za-z_$][\w$]*$/

export const tsType = (type?: string) => TS_TYPES[type ?? ''] ?? 'unknown'

/** `type State = { … }` with one optional property per field (a field may still be empty when the node runs). */
export function stateType(fields: StateField[]): string {
  const rows = fields.filter(f => f.name).map(f => `  ${IDENT.test(f.name) ? f.name : JSON.stringify(f.name)}?: ${tsType(f.type)}`)
  return rows.length ? `type State = {\n${rows.join('\n')}\n}` : 'type State = Record<string, unknown>'
}

/** Completion entries for `state.` (name plus its TypeScript or schema type). */
export const stateFields = (fields: StateField[], language: 'python' | 'typescript') =>
  fields.filter(f => f.name).map(f => ({ name: f.name, detail: language === 'typescript' ? tsType(f.type) : f.type }))

/** `state.` completions with the workflow's state fields. */
export const stateCompletions = (fields: { name: string; detail?: string }[]) => (ctx: CompletionContext) => {
  const m = ctx.matchBefore(/\bstate(?:\.|\[["'])\w*$/)
  if (!m) return null
  const from = m.from + m.text.search(/[.[]/) + (m.text.includes('[') ? 2 : 1)
  return { from, options: fields.map(f => ({ label: f.name, type: 'property', detail: f.detail })), validFor: /^\w*$/ }
}

