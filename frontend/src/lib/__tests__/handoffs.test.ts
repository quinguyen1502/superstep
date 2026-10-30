// TASK-0179: a deleted Agent node leaves no hand-off pointing at it.
import { describe, expect, it } from 'vitest'
import { addHandoff, handoffEdges, handoffsOf, HANDOFF_HANDLE, isHandoffEdge, pruneHandoffs, removeHandoffs } from '@/lib/handoffs'

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

describe('hand-off links on the canvas (TASK-0182)', () => {
  const ag = (id: string, handoffs?: any[]) => ({ id, type: 'agent', data: { label: id.toUpperCase(), ...(handoffs ? { handoffs } : {}) } })
  const nodes = () => [ag('tri', [{ target: 'bill', description: 'money' }]), ag('bill'), ag('tech'), { id: 'e', type: 'end', data: {} }]

  it('derives one dashed link per target from the hand-off handle', () => {
    const es = handoffEdges(nodes())
    expect(es.map(e => [e.id, e.source, e.target, e.sourceHandle])).toEqual([['handoff:tri>bill', 'tri', 'bill', HANDOFF_HANDLE]])
    expect(es[0].style.strokeDasharray).toBeTruthy()
    expect(isHandoffEdge(es[0].id)).toBe(true); expect(isHandoffEdge('e1')).toBe(false)
  })

  it('drawing a link adds a target once, only between two different agents', () => {
    const added = addHandoff(nodes(), 'tri', 'tech')
    expect(handoffsOf(added[0].data).map(h => h.target)).toEqual(['bill', 'tech'])
    expect(addHandoff(added, 'tri', 'tech')).toBe(added)
    for (const [s, t] of [['tri', 'tri'], ['tri', 'e'], ['e', 'tri']]) expect(addHandoff(nodes(), s, t)).toEqual(nodes())
  })

  it('deleting a link removes its target and keeps the rest', () => {
    const two = addHandoff(nodes(), 'tri', 'tech')
    const left = removeHandoffs(two, ['handoff:tri>bill', 'e1'])
    expect(handoffsOf(left[0].data)).toEqual([{ target: 'tech', description: '' }])
    expect(handoffEdges(left).map(e => e.id)).toEqual(['handoff:tri>tech'])
    const same = nodes(); expect(removeHandoffs(same, ['e1'])).toBe(same)
  })
})
