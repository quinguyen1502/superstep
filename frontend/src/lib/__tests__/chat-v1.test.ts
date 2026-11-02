import { describe, expect, it } from 'vitest'
import { v1ChatEvent, v1ChatRequest } from '../chat-v1'
import { buildTrace } from '../trace'

describe('public chat v1 presentation bridge', () => {
  it('emits strict message/answer frames without legacy run identifiers', () => {
    expect(v1ChatRequest('sid', { message: 'hello', attachment_ids: ['file'] }, 'vi')).toEqual({ type: 'message', chat_session_id: 'sid', text: 'hello', attachments: ['file'], locale: 'vi' })
    expect(v1ChatRequest('sid', { resume_run_id: 'private', response: 'approved', node: 'human' }, 'en')).toEqual({ type: 'answer', chat_session_id: 'sid', response: 'approved', node: 'human', locale: 'en' })
  })
  it('preserves visible live steps, question and terminal state while ignoring additions', () => {
    const frames = [{ type: 'run_started', run_id: 'run' }, { type: 'step', event: 'started', node: 'bot', node_type: 'llm', label: 'Assistant' },
      { type: 'token', node: 'bot', delta: 'Hello' }, { type: 'step', event: 'finished', node: 'bot', duration_ms: 10 }, { type: 'question', node: 'human', prompt: 'Approve?' }, { type: 'done', status: 'waiting' }, { type: 'future' }]
    const events = frames.flatMap(frame => { const ev = v1ChatEvent(frame); return ev ? [ev] : [] })
    const trace = buildTrace(events)
    expect(trace.spans[0].live).toBe('Hello')
    expect(trace.waiting?.node).toBe('human')
    expect(trace.status).toBe('waiting')
    expect(events.some(e => e.type === 'future')).toBe(false)
  })
})
