// TASK-0179: a deleted Agent node leaves no hand-off pointing at it.
import { describe, expect, it } from 'vitest'
import { handoffsOf, pruneHandoffs } from '@/lib/handoffs'

const agent = (id: string, handoffs?: unknown) => ({ id, type: 'agent', data: handoffs === undefined ? {} : { handoffs } })

describe('hand-offs', () => {
  it('keeps the same array when nothing points at a missing node', () => {
    const ns = [agent('a', [{ target: 'b' }]), agent('b')]
    expect(pruneHandoffs(ns)).toBe(ns)
  })
  it('drops targets that are gone, not agents, or the node itself', () => {
    const ns = [agent('a', [{ target: 'b' }, { target: 'gone' }, { target: 'a' }, { target: 's' }]), agent('b'), { id: 's', type: 'start', data: {} }]
    expect(handoffsOf(pruneHandoffs(ns)[0].data)).toEqual([{ target: 'b' }])
  })
})
