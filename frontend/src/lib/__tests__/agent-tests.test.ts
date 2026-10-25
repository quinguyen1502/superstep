import { describe, expect, it } from 'vitest'
import { needsApproval, toolNames } from '@/lib/agent'

describe('Agent nodes in the Tests panel (TASK-0119)', () => {
  const data = { tools: [{ name: 'lookup_order', source: 'builtin' }, { name: 'request_refund', source: 'builtin', approval: true }, { name: '', source: 'http' }] }
  it('lists the tools a "tool called" check can name', () => {
    expect(toolNames(data)).toEqual(['lookup_order', 'request_refund'])
    expect(toolNames(undefined)).toEqual([]); expect(toolNames({})).toEqual([])
  })
  it('answers an Agent node only when a tool needs approval', () => {
    expect(needsApproval(data)).toBe(true)
    expect(needsApproval({ tools: [{ name: 'a', source: 'mcp' }] })).toBe(false); expect(needsApproval(null)).toBe(false)
  })
})
