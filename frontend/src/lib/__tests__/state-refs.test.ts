import { describe, expect, it } from 'vitest'
import cases from '../../../../backend/tests/fixtures/template_refs.json'
import { badFilter, closeLen, openFilter, openRef, parseRef, refLabel, stateRef, stateRefRe } from '../state-refs'

// Shared with backend/tests/test_template_refs.py, so the two patterns agree
type Case = { text: string; refs: { field: string; path: string[]; filters: [string, string | number | null][] }[] }
const CASES = cases as Case[]
const refs = (s: string) => [...s.matchAll(stateRefRe())].map(parseRef)

describe('state refs', () => {
  it.each(CASES)('parses $text like the backend', ({ text, refs: want }) => {
    expect(refs(text).map(r => ({ field: r.field, path: r.path, filters: r.filters.map(f => [f.name, f.arg === undefined ? null : /^-?\d+$/.test(f.arg) ? Number(f.arg) : f.arg.slice(1, -1)]) }))).toEqual(want)
  })
  it('labels a tag with its path and filters', () => {
    expect(refLabel(refs('{{ state.order.items.0 | upper | default("-") }}')[0])).toBe('order.items.0 | upper | default("-")')
  })
  it('spots bad filters', () => {
    expect(badFilter(refs('{{state.a | upper | trim}}')[0])).toBeUndefined()
    expect(badFilter(refs('{{state.a | shout}}')[0])).toBe('shout')
    expect(badFilter(refs('{{state.a | upper(1)}}')[0])).toBe('upper')
    expect(badFilter(refs("{{state.a | truncate('x')}}")[0])).toBe('truncate')
    expect(badFilter(refs('{{state.a | default}}')[0])).toBe('default')
  })
  it('builds a reference', () => expect(stateRef('message')).toBe('{{state.message}}'))
  it('spots a reference being typed', () => {
    expect(openRef('Hello {{')).toEqual({ start: 6, name: 8 })
    expect(openRef('Hello {{ state.mes')).toEqual({ start: 6, name: 15 })
    expect(openRef('Hello {{mes')).toEqual({ start: 6, name: 8 })
    expect(openRef('Hello {{state.message}} ')).toBeNull()
    expect(openRef('Hello {')).toBeNull()
  })
  it('spots a filter being typed', () => {
    expect(openFilter('{{state.a | up')).toEqual({ name: 12 })
    expect(openFilter('{{ state.a.b | trim | ')).toEqual({ name: 22 })
    expect(openFilter('{{state.a}} | up')).toBeNull()
    expect(openFilter('a | up')).toBeNull()
  })
  it('measures closing braces after the cursor', () => {
    expect(closeLen('}} rest')).toBe(2)
    expect(closeLen(' }}')).toBe(3)
    expect(closeLen(' rest')).toBe(0)
  })
})
