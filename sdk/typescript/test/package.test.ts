import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { VERSION } from '../src/index'
import { BY_CODE } from '../src/errors'

const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
const spec = JSON.parse(readFileSync(new URL('../../../docs/api/openapi.public.json', import.meta.url), 'utf8'))

describe('package', () => {
  it('VERSION matches package.json', () => expect(VERSION).toBe(pkg.version))
  it('has no runtime dependencies', () => expect(pkg.dependencies ?? {}).toEqual({}))
  it('maps every error code documented in the public spec', () => {
    const codes = new Set<string>()
    for (const item of Object.values<Record<string, any>>(spec.paths))
      for (const op of Object.values<any>(item))
        for (const r of Object.values<any>(op.responses)) Object.keys(r.content['application/json'].examples ?? {}).forEach((c) => codes.add(c))
    expect(codes.size).toBeGreaterThan(0)
    for (const c of codes) expect(BY_CODE[c], c).toBeDefined()
  })
})
