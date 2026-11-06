import { describe, expect, it } from 'vitest'
import { buildTrace } from '../trace'
import { liveSteps } from '../chat'

describe('browser trace facts', () => {
  it('keeps standalone and Agent facts through replay and chat presentation', () => {
    const trace = buildTrace([
      { type: 'node_started', node: 'open', node_type: 'mcp', ts: 1 },
      { type: 'node_finished', node: 'open', node_type: 'mcp', ts: 2, browser: { operation: 'navigate', status: 'confirmed', sequence: 0 } },
      { type: 'node_started', node: 'ag/__tool/1', node_type: 'agent_tool', ts: 2 },
      { type: 'node_finished', node: 'ag/__tool/1', node_type: 'agent_tool', ts: 3, agent: { kind: 'tool', round: 1, tool: 'click', status: 'error', browser: { operation: 'click', status: 'unknown' } } },
    ])
    expect(trace.spans[0].browser?.status).toBe('confirmed')
    expect(liveSteps(trace.spans, 'full').map(step => step.browser?.status)).toEqual(['confirmed', 'unknown'])
    expect(liveSteps(trace.spans, 'labels').every(step => step.browser === undefined && step.input === undefined)).toBe(true)
  })
  it('retains stop status on an errored recipe action', () => {
    const trace = buildTrace([{ type: 'node_started', node: 'fill', node_type: 'mcp' }, { type: 'error', node: 'fill', errors: ['Stopped'], browser: { operation: 'fill', status: 'expired', approval: 'expired' } }])
    expect(trace.spans[0].browser?.status).toBe('expired')
  })
})
