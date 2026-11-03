import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import postcss from 'postcss'
import selectors from 'postcss-selector-parser'

const css = postcss.parse(readFileSync(new URL('../dist/styles.css', import.meta.url), 'utf8'))
describe('published CSS boundary', () => {
  it('anchors every outer selector to the chat root, including preflight', () => {
    let count = 0
    css.walkRules(rule => {
      for (let p = rule.parent; p; p = p.parent) {
        if (p.type === 'rule' || (p.type === 'atrule' && /keyframes$/.test(p.name))) return
      }
      const parsed = selectors().astSync(rule.selector)
      for (const selector of parsed.nodes) {
        const first = selector.nodes[0]
        expect(first.type, rule.selector).toBe('class')
        expect(first.value, rule.selector).toBe('superstep-chat')
        count++
      }
    })
    expect(count).toBeGreaterThan(500)
  })
  it('namespaces custom properties and keyframes; leaves host layer order alone', () => {
    css.walkAtRules('keyframes', rule => expect(rule.params).toMatch(/^ss-/))
    css.walkAtRules('property', rule => expect(rule.params).toMatch(/^--ss-/))
    css.walkAtRules('layer', () => { throw new Error('A host cascade layer would be affected') })
    css.walkDecls(decl => {
      if (decl.prop.startsWith('--')) expect(decl.prop).toMatch(/^--(ss-|radix-|shiki-)/)
    })
    expect(css.toString()).toContain('.ss-flex')
    expect(css.toString()).not.toContain('@font-face')
  })
})
