/** Web chat (TASK-0085, REQ-0048): the shapes of /api/workflows/{wid}/chat and /api/chat/sessions, and the pure
 *  helpers the Chat tab uses on a live run's events. The server is the source of truth once a run settles. */
import { defaultUrlTransform } from 'react-markdown'
import type { RunEvent, Span } from '@/lib/trace'

export const ACCESS = ['studio'] as const            // DEC-0053: anonymous / signed_in are reserved for phase 2
export const ACCESS_RESERVED = ['anonymous', 'signed_in'] as const
export const STEPS = ['none', 'labels', 'full'] as const
export const ANSWERED_BY = ['visitor', 'reviewer'] as const
export const MAX_MESSAGE = 4000
export type StepsMode = typeof STEPS[number]
export type AnsweredBy = typeof ANSWERED_BY[number]

export type ChatSettings = { enabled: boolean; slug: string; access: string; input_field: string; reply_field: string
  messages_field: string; max_turns: number; steps: StepsMode; retention_days: number }
export type ChatStep = { node: string; label: string; type?: string; status: 'running' | 'ok' | 'error' | 'waiting'
  duration_ms?: number; input?: any; delta?: any; errors?: string[]; child_run_id?: string }  // child_run_id: a workflow tool's run (TASK-0136)
export type ChatTurn = { id: string; role: 'user' | 'assistant'; text: string; status?: string | null; run_id?: string | null
  node?: string | null; answered_by?: AnsweredBy | null; code?: string | null; created: number; steps?: ChatStep[] }
export type ChatSession = { id: string; workflow_id: string; channel: string; title?: string | null; last_run_id?: string | null
  created: number; updated: number }
export type ChatSessionFull = ChatSession & { steps_mode: StepsMode; turns: ChatTurn[] }

/** The reply streamed so far: the `node_token` deltas of the nodes that write the reply field. A node that streams
 *  again (an Agent's next model call, a loop) replaces its earlier text, as its field is replaced (TASK-0118). */
export function liveReply(events: RunEvent[], replyField: string): string {
  const parts = new Map<string, { it: number; text: string }>()
  for (const e of events) {
    if (e.type !== 'node_token' || (e as any).field !== replyField || typeof e.delta !== 'string' || !e.node) continue
    const it = e.iteration ?? 1; const p = parts.get(e.node)
    parts.set(e.node, p && p.it === it ? { it, text: p.text + e.delta } : p && p.it > it ? p : { it, text: e.delta })
  }
  return [...parts.values()].map(p => p.text).join('')
}

const HIDDEN = new Set(['start', 'end', 'agent', 'agent_exit'])  // an Agent node shows its tool calls (and model calls in full)
/** A step's label in a chat: an Agent's tool step names the tool ("Support › lookup_order"). */
const stepLabel = (s: Span) => s.agent?.kind === 'tool' && s.agent.tool ? `${s.label.replace(/ › [^›]*$/, '')} › ${s.agent.tool}` : s.label
/** A live run's steps as a chat shows them (DEC-0053), from the trace spans: none, labels or full. Same rules as the server. */
export function liveSteps(spans: Span[], mode: StepsMode): ChatStep[] {
  if (mode === 'none') return []
  return spans.filter(s => !HIDDEN.has(s.type) && (mode === 'full' || s.type !== 'agent_model')).map(s => {
    const status: ChatStep['status'] = s.status === 'done' ? 'ok' : s.status === 'error' ? 'error' : s.status === 'waiting' ? 'waiting' : 'running'
    const base: ChatStep = { node: s.node, label: stepLabel(s), type: s.type, status }
    return mode === 'full' ? { ...base, duration_ms: s.duration, input: s.input, delta: s.agent ?? s.output, errors: s.error ? [s.error] : undefined,
      ...(s.agent?.child_run_id ? { child_run_id: s.agent.child_run_id } : {}) } : base
  })
}

/** The assistant turn that still waits for a Human answer, if the chat's last turn is one. */
export function waitingTurn(turns: ChatTurn[]): ChatTurn | undefined {
  const last = turns[turns.length - 1]
  return last?.role === 'assistant' && last.status === 'waiting' ? last : undefined
}

/** How many answers a run has in the chat: the worker writes one each time the run settles (waiting, then done). */
export const answers = (turns: ChatTurn[], runId?: string) => runId ? turns.filter(t => t.role === 'assistant' && t.run_id === runId).length : 0

const SAFE_URL = /^(https?:|mailto:|#|\/)/i
/** Links in a chat answer: http(s), mailto, in-page and same-site paths only (no javascript:, data:, …). */
export const safeUrl = (url: string) => SAFE_URL.test(url.trim()) ? defaultUrlTransform(url) : ''
