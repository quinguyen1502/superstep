import { describe, expect, it } from 'vitest'
import { agentOf, buildTrace, hideAgents, type RunEvent } from '@/lib/trace'
import { liveReply, liveSteps } from '@/lib/chat'
import { newTool, toolName } from '@/lib/agent'

const conv = { 'agent:ag': { messages: [{ role: 'user', content: 'B200?' }] } }
/** An Agent node `ag` (label Helper) as the engine streams it (TASK-0116): one tool round, then the answer. */
const EVENTS: RunEvent[] = [
  { type: 'node_started', node: 'ag', node_type: 'agent', label: 'Helper', iteration: 1 },
  { type: 'node_finished', node: 'ag', node_type: 'agent', label: 'Helper', iteration: 1, input: { message: 'B200?' }, delta: {} },
  { type: 'node_started', node: 'ag/__model', node_type: 'agent_model', label: 'Helper › model', iteration: 1 },
  { type: 'node_token', node: 'ag/__model', iteration: 1, delta: 'Let me check', field: 'answer' } as RunEvent,
  { type: 'node_finished', node: 'ag/__model', node_type: 'agent_model', label: 'Helper › model', iteration: 1, input: { message: 'B200?', ...conv }, delta: {},
    agent: { kind: 'model', round: 1, text: 'Let me check', limit_hit: false, tool_calls: [{ name: 'lookup_order', args: { message: 'B200' } }] } },
  { type: 'node_started', node: 'ag/__tool', node_type: 'agent_tool', label: 'Helper › tool', iteration: 1 },
  { type: 'node_finished', node: 'ag/__tool', node_type: 'agent_tool', label: 'Helper › tool', iteration: 1, input: { message: 'B200?', ...conv }, delta: {},
    agent: { kind: 'tool', round: 1, tool: 'lookup_order', args: { message: 'B200' }, result: 'In transit', status: 'ok', ms: 3 } },
  { type: 'node_started', node: 'ag/__model', node_type: 'agent_model', label: 'Helper › model', iteration: 2 },
  { type: 'node_token', node: 'ag/__model', iteration: 2, delta: 'In ', field: 'answer' } as RunEvent,
  { type: 'node_token', node: 'ag/__model', iteration: 2, delta: 'transit', field: 'answer' } as RunEvent,
  { type: 'node_finished', node: 'ag/__model', node_type: 'agent_model', label: 'Helper › model', iteration: 2, input: { message: 'B200?', ...conv }, delta: {},
    agent: { kind: 'model', round: 2, text: 'In transit', limit_hit: true, tool_calls: [] } },
  { type: 'node_started', node: 'ag/__exit', node_type: 'agent_exit', label: 'Helper › end', iteration: 1 },
  { type: 'node_finished', node: 'ag/__exit', node_type: 'agent_exit', label: 'Helper › end', iteration: 1, input: { message: 'B200?', ...conv }, delta: { answer: 'In transit' } },
]

describe('Agent node in traces and chats (TASK-0118)', () => {
  it('knows the Agent node of a step and hides the conversation', () => {
    expect(agentOf('ag/__tool')).toBe('ag'); expect(agentOf('sub/ag/__model')).toBe('sub/ag'); expect(agentOf('ag')).toBeUndefined()
    expect(hideAgents({ a: 1, 'agent:x': {} })).toEqual({ a: 1 }); expect(hideAgents({ _truncated: true })).toEqual({ _truncated: true })
  })
  it('spans carry what each step did, without the conversation', () => {
    const spans = buildTrace(EVENTS).spans
    const tool = spans.find(s => s.node === 'ag/__tool')!
    expect(tool.agent).toMatchObject({ kind: 'tool', tool: 'lookup_order', result: 'In transit' })
    expect(tool.input).toEqual({ message: 'B200?' })
    expect(spans.filter(s => s.node === 'ag/__model').map(s => s.agent?.round)).toEqual([1, 2])
  })
  it('chat steps: tool calls by name, model calls only in full, the entry and exit hidden', () => {
    const spans = buildTrace(EVENTS).spans
    expect(liveSteps(spans, 'labels')).toEqual([{ node: 'ag/__tool', label: 'Helper › lookup_order', type: 'agent_tool', status: 'ok' }])
    const full = liveSteps(spans, 'full')
    expect(full.map(s => s.type)).toEqual(['agent_model', 'agent_tool', 'agent_model'])
    expect(full[1].delta).toMatchObject({ tool: 'lookup_order', result: 'In transit' })
  })
  it('the streamed reply is the last model call, not the text of a tool round', () => {
    expect(liveReply(EVENTS, 'answer')).toBe('In transit')
  })
  it('new tools get provider-safe, unique names', () => {
    expect(toolName('get weather!', [])).toBe('get_weather'); expect(toolName('add', ['add', 'add_2'])).toBe('add_3')
    expect(newTool('http', ['http_request'])).toMatchObject({ name: 'http_request_2', source: 'http', method: 'GET' })
    expect(newTool('knowledge', [])).toMatchObject({ name: 'search_knowledge', top_k: 4 })
  })
})
