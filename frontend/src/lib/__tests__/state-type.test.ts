import { describe, expect, it } from 'vitest'
import { stateCompletions, stateFields, stateType, tsType } from '@/lib/state-type'
import { EditorState } from '@codemirror/state'
import { CompletionContext } from '@codemirror/autocomplete'

describe('State type for TypeScript Code nodes', () => {
  it('maps every schema type and quotes names that are not identifiers', () => {
    expect(stateType([{ name: 'message', type: 'string' }, { name: 'count', type: 'integer' }, { name: 'score', type: 'number' },
      { name: 'ok', type: 'boolean' }, { name: 'data', type: 'object' }, { name: 'items', type: 'list' }, { name: 'my-field', type: 'string' }]))
      .toBe('type State = {\n  message?: string\n  count?: number\n  score?: number\n  ok?: boolean\n  data?: Record<string, unknown>\n  items?: unknown[]\n  "my-field"?: string\n}')
    expect(tsType('weird')).toBe('unknown')
  })
  it('has a fallback for an empty schema', () => {
    expect(stateType([])).toBe('type State = Record<string, unknown>')
    expect(stateType([{ name: '' }])).toBe('type State = Record<string, unknown>')
  })
  it('offers state fields with the type of the language', () => {
    const f = [{ name: 'message', type: 'string' }, { name: 'n', type: 'integer' }]
    expect(stateFields(f, 'typescript')).toEqual([{ name: 'message', detail: 'string' }, { name: 'n', detail: 'number' }])
    expect(stateFields(f, 'python')[1]).toEqual({ name: 'n', detail: 'integer' })
  })
  it('completes after state. and state["', () => {
    const src = stateCompletions([{ name: 'message' }, { name: 'out' }])
    const at = (doc: string) => src(new CompletionContext(EditorState.create({ doc }), doc.length, false))
    expect(at('return state.me')).toMatchObject({ from: 13, options: [{ label: 'message' }, { label: 'out' }] })
    expect(at('return state["')?.from).toBe(14)
    expect(at('return other.me')).toBeNull()
  })
})
