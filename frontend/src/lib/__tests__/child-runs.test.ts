import { describe, expect, it } from 'vitest'
import { buildTrace } from '@/lib/trace'

/** A run waiting for a workflow tool's child run (TASK-0135): the trace knows which child, and a person's question is not shown. */
describe('child run waits', () => {
  const started = { type: 'run_started', run_id: 'p1', ts: 1 }
  it('carries the child run, tool and workflow', () => {
    const t = buildTrace([started, { type: 'node_started', node: 'ag/__tool', ts: 1 },
      { type: 'run_waiting', node: 'ag/__tool', label: 'Supervisor › desk', prompt: '', tool: 'desk', workflow_id: 'w2', wait: { kind: 'child', run_id: 'c1' }, ts: 2 }])
    expect(t.status).toBe('waiting')
    expect(t.waiting?.child).toEqual({ runId: 'c1', workflowId: 'w2', tool: 'desk' })
  })
  it('leaves a Human node wait as it was', () => {
    const t = buildTrace([started, { type: 'run_waiting', node: 'ask', label: 'Approve', prompt: 'OK?', ts: 2 }])
    expect(t.waiting?.child).toBeUndefined()
    expect(t.waiting?.prompt).toBe('OK?')
  })
  it('a resumed run is no longer waiting for its child', () => {
    const t = buildTrace([started, { type: 'run_waiting', node: 'ag/__tool', wait: { kind: 'child', run_id: 'c1' }, ts: 2 },
      { type: 'run_resumed', node: 'ag/__tool', ts: 3 }])
    expect(t.waiting).toBeUndefined()
  })
})
