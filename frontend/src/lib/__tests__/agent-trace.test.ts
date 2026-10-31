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
    expect(agentOf('ag/__tool')).toBe('ag'); expect(agentOf('ag/__tool/2')).toBe('ag'); expect(agentOf('sub/ag/__join')).toBe('sub/ag')
    expect(agentOf('sub/ag/__model')).toBe('sub/ag'); expect(agentOf('ag')).toBeUndefined()
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
  it('tool calls of one superstep share a start and use each call\'s own duration', () => {
    const wave = (node: string, ms: number, ts: number): RunEvent => ({
      type: 'node_finished', node, node_type: 'agent_tool', superstep: 3, ts, duration_ms: 10,
      agent: { kind: 'tool', round: 1, tool: node, status: 'ok', ms },
    })
    const spans = buildTrace([wave('ag/__tool/1', 100, 2), wave('ag/__tool/2', 400, 2.3), wave('ag/__tool/3', 400, 2.1)]).spans
    expect(spans.map(s => s.start)).toEqual([spans[0].start, spans[0].start, spans[0].start])
    expect(spans.map(s => s.duration)).toEqual([100, 400, 400])
    expect(spans[0].duration!).toBeLessThan(spans[1].duration!)
    expect(agentOf('ag/__model')).toBe('ag')
  })
  it('new tools get provider-safe, unique names', () => {
    expect(toolName('get weather!', [])).toBe('get_weather'); expect(toolName('add', ['add', 'add_2'])).toBe('add_3')
    expect(newTool('http', ['http_request'])).toMatchObject({ name: 'http_request_2', source: 'http', method: 'GET' })
    expect(newTool('knowledge', [])).toMatchObject({ name: 'search_knowledge', top_k: 4 })
  })
})

describe('a tool wave that waits in two slots (DEC-0069)', () => {
  it('resumes once and keeps one row per slot', () => {
    const tool = (slot: number, type: string, extra: Partial<RunEvent> = {}) =>
      ({ type, node: `agent/__tool/${slot}`, node_type: 'agent_tool', label: 'Supervisor › tool', iteration: 1, ...extra }) as RunEvent
    const done = (slot: number) => tool(slot, 'node_finished', { superstep: 1, delta: {}, agent: { kind: 'tool', round: 1, tool: `desk_${slot}`, result: 'ok', status: 'ok', ms: 2 } } as Partial<RunEvent>)
    const trace = buildTrace([
      tool(1, 'node_started'), tool(2, 'node_started'),
      { type: 'run_waiting', node: 'agent/__tool/1' }, { type: 'run_waiting', node: 'agent/__tool/2' },
      { type: 'run_resumed', node: 'agent/__tool/1' },
      tool(1, 'node_started'), tool(2, 'node_started'), done(2), done(1),
      { type: 'run_finished', state: {} },
    ] as RunEvent[])
    const slots = trace.spans.filter(s => s.node.startsWith('agent/__tool/'))
    expect(slots.map(s => s.key)).toEqual(['agent/__tool/1#1', 'agent/__tool/2#1'])
    expect(slots.every(s => s.status === 'done')).toBe(true)
  })
})

describe('AI review usage on the waiting step (TASK-0198)', () => {
  it('adds the judge tokens and cost to the Human node row', () => {
    const usage = { provider: 'openai', model: 'gpt-4o-mini', tokens_in: 1000, tokens_out: 200, tokens: 1200, cost_usd: 0.00027 }
    const trace = buildTrace([
      { type: 'node_started', node: 'ask', node_type: 'human', label: 'Approve' },
      { type: 'run_waiting', node: 'ask' },
      { type: 'approval_review', node: 'ask', outcome: 'approved', model: 'gpt-4o-mini', usage },
      { type: 'run_resumed', node: 'ask' },
      { type: 'node_finished', node: 'ask', node_type: 'human', label: 'Approve', delta: {} },
      { type: 'run_finished', state: {} },
    ] as RunEvent[])
    const [ask] = trace.spans
    expect(trace.spans).toHaveLength(1)
    expect(ask.tokens).toBe(1200); expect(ask.cost).toBeCloseTo(0.00027); expect(ask.review?.outcome).toBe('approved')
    expect(trace.tokens).toBe(1200)
  })
})
