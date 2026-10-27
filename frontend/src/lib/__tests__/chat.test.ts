import { describe, expect, it } from 'vitest'
import { buildTrace, type RunEvent } from '@/lib/trace'
import { answers, downShare, liveReply, liveSteps, safeUrl, waitingTurn, type ChatTurn } from '@/lib/chat'

const EVENTS: RunEvent[] = [
  { type: 'run_started', run_id: 'r1' },
  { type: 'node_started', node: 'start', node_type: 'start', label: 'Start' },
  { type: 'node_finished', node: 'start', node_type: 'start', label: 'Start', duration_ms: 1 },
  { type: 'node_started', node: 'bot', node_type: 'llm', label: 'Bot' },
  { type: 'node_token', node: 'bot', delta: 'Hel', field: 'reply' } as RunEvent,
  { type: 'node_token', node: 'bot', delta: 'lo', field: 'reply' } as RunEvent,
  { type: 'node_token', node: 'note', delta: 'scratch', field: 'notes' } as RunEvent,
  { type: 'node_finished', node: 'bot', node_type: 'llm', label: 'Bot', duration_ms: 12, input: { q: 'hi' }, delta: { reply: 'Hello' } },
]

describe('chat (TASK-0085)', () => {
  it('streams only the tokens of the reply field', () => {
    expect(liveReply(EVENTS, 'reply')).toBe('Hello')
    expect(liveReply(EVENTS, 'other')).toBe('')
  })
  it('shows steps by mode and hides start/end', () => {
    const spans = buildTrace(EVENTS).spans
    expect(liveSteps(spans, 'none')).toEqual([])
    expect(liveSteps(spans, 'labels')).toEqual([{ node: 'bot', label: 'Bot', type: 'llm', status: 'ok' }])
    expect(liveSteps(spans, 'full')[0]).toMatchObject({ node: 'bot', duration_ms: 12, input: { q: 'hi' }, delta: { reply: 'Hello' } })
  })
  it('rounds the share of thumbs down', () => {
    expect(downShare({ up: 0, down: 0 })).toBeNull()
    expect(downShare({ up: 1, down: 1 })).toBe(50)
    expect(downShare({ up: 1, down: 2 })).toBe(67)
  })
  it('finds the waiting turn and counts a run’s answers', () => {
    const turns: ChatTurn[] = [{ id: 'a', role: 'user', text: 'refund', created: 1 },
      { id: 'b', role: 'assistant', text: 'OK?', status: 'waiting', run_id: 'r1', answered_by: 'visitor', created: 2 }]
    expect(waitingTurn(turns)?.id).toBe('b')
    expect(waitingTurn([...turns, { id: 'c', role: 'assistant', text: 'done', status: 'ok', run_id: 'r1', created: 3 }])).toBeUndefined()
    expect(answers(turns, 'r1')).toBe(1); expect(answers(turns, undefined)).toBe(0)
  })
  it('keeps only safe links', () => {
    expect(safeUrl('https://example.com/a')).toBe('https://example.com/a')
    expect(safeUrl('mailto:a@b.c')).toBe('mailto:a@b.c')
    expect(safeUrl('javascript:alert(1)')).toBe('')
    expect(safeUrl('data:text/html,x')).toBe('')
  })
})
