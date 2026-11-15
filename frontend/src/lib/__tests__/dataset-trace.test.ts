import { describe, expect, it } from 'vitest'
import { buildTrace } from '../trace'

describe('Dataset run trace', () => {
  it('retains only the supplied trace facts in the summary', () => {
    const dataset = { id: 'tickets', operation: 'find_rows', count: 1, outcome: 'completed' } as const
    const trace = buildTrace([
      { type: 'node_started', node: 'lookup', node_type: 'dataset', ts: 1 },
      { type: 'node_finished', node: 'lookup', node_type: 'dataset', ts: 2, dataset,
        delta: { result: { items: [{ values: { secret: 'example' } }] } } },
    ])
    expect(trace.spans[0].dataset).toEqual(dataset)
    expect(trace.spans[0].end).toBe(2)
    expect(JSON.stringify(trace.spans[0].dataset)).not.toContain('secret')
  })
})
