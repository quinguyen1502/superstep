import { describe, expect, it } from 'vitest'
import { applyMode, codeChoices, modeValue } from '@/lib/code-mode'
import type { CodeRuntime } from '@/lib/code-runtime'

const PY = 'def main(state):\n    return None\n'
const TS = 'export function main(state: State) {\n  return null\n}\n'
const lang = (id: 'python' | 'typescript', available = true, starter = id === 'python' ? PY : TS) =>
  ({ id, available, problem: null, image: '', packages: [], starter })
const rt = (langs = [lang('python'), lang('typescript')]) =>
  ({ code_runtime: 'subprocess', available: true, problem: null, image: '', packages: [], starter: PY, limits: {} as CodeRuntime['limits'], languages: langs }) as CodeRuntime

describe('Tool Mode select: one option per Code language',  => {
  it('maps the stored mode + language to one select value', () => {
    expect(modeValue({ mode: 'function' })).toBe('function'); expect(modeValue({ mode: 'http' })).toBe('http')
    expect(modeValue({ mode: 'code' })).toBe('code:python'); expect(modeValue({ mode: 'code', language: 'typescript' })).toBe('code:typescript')
  })
  it('offers only available languages, but keeps the node\'s own so it still shows', () => {
    expect(codeChoices(rt(), {})).toEqual(['python', 'typescript'])
    expect(codeChoices(rt([lang('python'), lang('typescript', false)]), {})).toEqual(['python'])
    expect(codeChoices(rt([lang('python'), lang('typescript', false)]), { mode: 'code', language: 'typescript' })).toEqual(['typescript', 'python'])
    expect(codeChoices(null, {})).toEqual(['python'])
  })
  it('picks a starter for empty code and swaps an untouched starter', () => {
    expect(applyMode({ mode: 'function' }, 'code:typescript', rt())).toEqual({ patch: { mode: 'code', language: 'typescript', code: TS }, kept: false })
    expect(applyMode({ mode: 'code', language: 'python', code: PY }, 'code:typescript', rt())).toEqual({ patch: { mode: 'code', language: 'typescript', code: TS }, kept: false })
  })
  it('keeps edited code and asks for a rewrite; other modes and the same language change nothing else', () => {
    expect(applyMode({ mode: 'code', language: 'python', code: 'def main(s): return 1' }, 'code:typescript', rt()))
      .toEqual({ patch: { mode: 'code', language: 'typescript' }, kept: true })
    expect(applyMode({ mode: 'function', code: 'def main(s): return 1' }, 'code:python', rt())).toEqual({ patch: { mode: 'code', language: 'python' }, kept: false })
    expect(applyMode({ mode: 'code', language: 'typescript', code: TS }, 'code:typescript', rt())).toEqual({ patch: {}, kept: false })
    expect(applyMode({ mode: 'code', code: PY }, 'http', rt())).toEqual({ patch: { mode: 'http' }, kept: false })
  })
})
