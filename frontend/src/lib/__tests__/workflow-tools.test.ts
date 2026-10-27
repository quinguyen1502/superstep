import { describe, expect, it } from 'vitest'
import { SOURCES, defaultFields, newTool } from '@/lib/agent'
import { liveSteps } from '@/lib/chat'
import { buildTrace, type RunEvent } from '@/lib/trace'

/** Workflow tools in the editor and the chat (TASK-0136, REQ-0073). */
describe('workflow tools', () => {
  it('are a tool source with empty settings', () => {
    expect(SOURCES).toContain('workflow')
    expect(newTool('workflow', ['workflow'])).toEqual({ name: 'workflow_2', source: 'workflow', description: '', workflow_id: '', inputs: [], outputs: [] })
  })
  it('pick message in and answer out when the workflow has them', () => {
    expect(defaultFields(['message', 'answer', 'steps'])).toEqual({ inputs: ['message'], outputs: ['answer'] })
    expect(defaultFields(['question', 'reply'])).toEqual({ inputs: ['question'], outputs: ['reply'] })
    expect(defaultFields(['only'])).toEqual({ inputs: ['only'], outputs: ['only'] })
    expect(defaultFields([])).toEqual({ inputs: [], outputs: [] })
  })
  it('a chat in full view keeps the child run of a tool call', () => {
    const evs: RunEvent[] = [{ type: 'run_started', run_id: 'p', ts: 1 },
      { type: 'node_started', node: 'ag/__tool', node_type: 'agent_tool', label: 'Supervisor › tool', ts: 1 },
      { type: 'node_finished', node: 'ag/__tool', node_type: 'agent_tool', label: 'Supervisor › tool', ts: 2, duration_ms: 5,
        agent: { kind: 'tool', round: 1, tool: 'desk', status: 'ok', result: '{}', child_run_id: 'c1', child_workflow_id: 'w2' } }]
    expect(liveSteps(buildTrace(evs).spans, 'full').find(s => s.node === 'ag/__tool')?.child_run_id).toBe('c1')
    expect(liveSteps(buildTrace(evs).spans, 'labels').find(s => s.node === 'ag/__tool')?.child_run_id).toBeUndefined()
  })
})
