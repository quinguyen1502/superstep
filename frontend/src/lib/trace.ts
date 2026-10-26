import i18n, { eventErrors, type ApiErrorBody } from '@/lib/i18n'
// Turns the run event stream into one span per node execution (LangSmith/Langfuse-style trace).
export type RunEvent = { type: string; node?: string; label?: string; node_type?: string; iteration?: number; duration_ms?: number
  input?: any; delta?: any; state?: any; errors?: string[]; error?: ApiErrorBody; ts?: number; tokens?: number; usage?: Usage & { total_tokens?: number }; run_id?: string; status?: string; reason?: string
  metrics?: RunMetrics | null; trace_id?: string | null; trace_url?: string | null; prompt?: string; response?: string
  code_output?: CodeOutput; agent?: AgentStep
  wait?: { kind: 'child'; run_id: string }; tool?: string; workflow_id?: string }  // a run waiting for a workflow tool's child run (TASK-0134)
/** What one step of an Agent node did (TASK-0116, DEC-0063): a model call (`model`) or one tool call (`tool`). */
export type AgentStep = { kind: 'model' | 'tool'; round: number; text?: string; limit_hit?: boolean; tool_calls?: { name: string; args: any }[]
  tool?: string; args?: any; result?: string; status?: 'ok' | 'error' | 'refused' | 'rejected'; ms?: number
  approval?: 'approved' | 'rejected' }  // a tool that needed approval (TASK-0117)
/** An Agent node `ag` runs as the steps `ag/__model`, `ag/__tool` and `ag/__exit`: the Agent node's id, else undefined. */
export const agentOf = (node: string) => /^(.+)\/__(model|tool|exit)$/.exec(node)?.[1]
/** State without the agents' conversations (`agent:<id>`), which the engine keeps for time travel only. */
export const hideAgents = (state: any) => state && typeof state === 'object' && !Array.isArray(state) && !state._truncated
  ? Object.fromEntries(Object.entries(state).filter(([k]) => !k.startsWith('agent:'))) : state
/** What a Tool node in Code mode printed, its traceback and where it ran (TASK-0053/0055). */
export type CodeOutput = { stdout?: string; traceback?: string; runtime?: string; duration_ms?: number }
// TASK-0010: token usage on node_finished, per-run metrics on the final run_summary event (and in run history)
export type Usage = { provider?: string; model?: string; tokens?: number; tokens_in?: number; tokens_out?: number; cost_usd?: number | null; estimated?: boolean }
export type RunMetrics = { duration_ms: number; tokens: number; tokens_in: number; tokens_out: number; cost_usd: number | null; error_count: number }
export type Span = { key: string; node: string; label: string; type: string; iter: number; status: 'running' | 'done' | 'error' | 'cancelled' | 'waiting'
  start: number; end?: number; duration?: number; input?: any; output?: any; error?: string; tokens?: number; cost?: number | null; usage?: Usage; events: RunEvent[]
  live?: string; code?: CodeOutput; agent?: AgentStep }  // TASK-0030: LLM text streamed so far (node_token deltas; not stored in run history)
export type Trace = { runId?: string; spans: Span[]; status: 'idle' | 'running' | 'ok' | 'error' | 'cancelled' | 'timeout' | 'waiting' | 'expired' | 'paused'; start?: number; end?: number; total?: number
  tokens?: number; errors: string[]; final?: any; metrics?: RunMetrics; traceUrl?: string
  waiting?: { runId?: string; node?: string; label?: string; prompt?: string; child?: { runId: string; workflowId?: string; tool?: string } }
  paused?: { runId?: string } }  // TASK-0036: one-step pause, not a human approval

export function buildTrace(events: RunEvent[], meta: (id: string) => { label?: string; type?: string } = () => ({})): Trace {
  const spans: Span[] = []; const counts: Record<string, number> = {}; const errors: string[] = []; let summary: RunEvent | undefined
  let runId: string | undefined; let waitingEv: RunEvent | undefined; let resumed: string | undefined
  const st = { v: (events.length ? 'running' : 'idle') as Trace['status'] }; let final: any
  const open = (n: string) => [...spans].reverse().find(s => s.node === n && s.status === 'running')
  const t = (e: RunEvent, i: number) => e.ts ?? i / 1000
  events.forEach((e, i) => {
    const n = e.node
    if ((e.type === 'run_started' || e.type === 'run_resumed') && e.run_id) runId = e.run_id
    if (e.type === 'node_started' && n && n === resumed) {
      resumed = undefined
      if ([...spans].reverse().some(s => s.node === n && s.status === 'running')) return // resumed Human node keeps its span
    }
    if (e.type === 'node_started' && n) {
      const it = (counts[n] = (counts[n] || 0) + 1); const m = meta(n)
      spans.push({ key: `${n}#${it}`, node: n, label: e.label || m.label || n, type: e.node_type || m.type || 'code', iter: it, status: 'running', start: t(e, i), events: [e] })
    } else if (e.type === 'node_token' && n) { const s = open(n); if (s) s.live = (s.live || '') + (typeof e.delta === 'string' ? e.delta : '')
    } else if (e.type === 'node_finished' && n) {
      let s = open(n)
      if (!s) { const it = (counts[n] = (counts[n] || 0) + 1); s = { key: `${n}#${it}`, node: n, label: e.label || meta(n).label || n, type: e.node_type || meta(n).type || 'code', iter: it, status: 'running', start: t(e, i) - (e.duration_ms || 0) / 1000, events: [] }; spans.push(s) }
      Object.assign(s, { status: 'done', end: t(e, i), duration: e.duration_ms, input: hideAgents(e.input), output: e.delta, agent: e.agent, tokens: e.tokens ?? e.usage?.tokens ?? e.usage?.total_tokens, cost: e.usage?.cost_usd, usage: e.usage, code: e.code_output })
      s.events.push(e)
    } else if (e.type === 'error') {
      st.v = e.status === 'timeout' ? 'timeout' : 'error'; const msg = eventErrors(e).join('; ') || i18n.t('trace.error'); errors.push(msg)
      const s = (n ? open(n) ?? [...spans].reverse().find(x => x.node === n) : undefined) ?? (e.status === 'timeout' ? undefined : [...spans].reverse().find(x => x.status === 'running'))
      if (s) { Object.assign(s, { status: 'error', end: t(e, i), duration: e.duration_ms ?? s.duration, error: msg, input: hideAgents(e.input) ?? s.input, code: e.code_output ?? s.code }); s.events.push(e) }
    } else if (e.type === 'run_cancelled') { st.v = 'cancelled'
    } else if (e.type === 'run_expired') { st.v = 'expired'; waitingEv = undefined; spans.forEach(s => { if (s.status === 'waiting') s.status = 'cancelled' })
    } else if (e.type === 'run_finished') { if (st.v !== 'error') st.v = 'ok'; final = e.state
    } else if (e.type === 'run_summary') { summary = e
    } else if (e.type === 'run_waiting') { st.v = 'waiting'; waitingEv = e; const s = n ? open(n) : undefined; if (s) { s.status = 'waiting'; s.events.push(e) }
    } else if (e.type === 'run_paused') { st.v = 'paused'; waitingEv = undefined
    } else if (e.type === 'run_resumed' || e.type === 'run_recovered') { st.v = 'running'; waitingEv = undefined; resumed = n
      const s = n ? [...spans].reverse().find(x => x.node === n && x.status === 'waiting') : undefined; if (s) { s.status = 'running'; s.events.push(e) } }
  })
  // Speculative "started" rows (predicted next nodes) that never ran are dropped once the run ends.
  const status = st.v; const done = status !== 'running' && status !== 'idle'
  // Rows still running when a run is cancelled / times out are shown as cancelled; speculative
  // "started" rows (predicted next nodes) are dropped once a run finishes normally.
  if (status === 'cancelled' || status === 'timeout') spans.forEach(s => { if (s.status === 'running') s.status = 'cancelled' })
  const kept = done ? spans.filter(s => s.status !== 'running') : spans
  const stamped = events.filter(e => e.ts != null && e.type !== 'run_summary')
  const start = stamped.length ? stamped[0].ts : kept[0]?.start
  const end = stamped.length ? stamped[stamped.length - 1].ts : kept[kept.length - 1]?.end
  const tokens = kept.reduce((a, s) => a + (s.tokens || 0), 0)
  const metrics = summary?.metrics ?? undefined
  return { runId, spans: kept, status, start, end, total: metrics?.duration_ms ?? (start != null && end != null ? (end - start) * 1000 : undefined),
    tokens: metrics?.tokens ?? (tokens || undefined), errors, final, metrics, traceUrl: summary?.trace_url ?? undefined,
    waiting: status === 'waiting' && waitingEv ? { runId, node: waitingEv.node, label: waitingEv.label, prompt: waitingEv.prompt,
      ...(waitingEv.wait ? { child: { runId: waitingEv.wait.run_id, workflowId: waitingEv.workflow_id, tool: waitingEv.tool } } : {}) } : undefined,
    paused: status === 'paused' ? { runId } : undefined }
}

export type DiffRow = { key: string; kind: 'added' | 'changed' | 'removed' | 'same'; before?: any; after?: any }
export function stateDiff(before: any = {}, output: any = {}): DiffRow[] {
  const b = before && typeof before === 'object' && !before._truncated ? before : {}
  const o = output && typeof output === 'object' && !output._truncated ? output : {}
  const after = { ...b, ...o }; const keys = [...new Set([...Object.keys(b), ...Object.keys(after)])]
  const eq = (x: any, y: any) => JSON.stringify(x) === JSON.stringify(y)
  return keys.map(k => !(k in b) ? { key: k, kind: 'added' as const, after: after[k] }
    : !(k in after) ? { key: k, kind: 'removed' as const, before: b[k] }
    : eq(b[k], after[k]) ? { key: k, kind: 'same' as const, before: b[k], after: after[k] }
    : { key: k, kind: 'changed' as const, before: b[k], after: after[k] })
    .sort((x, y) => (x.kind === 'same' ? 1 : 0) - (y.kind === 'same' ? 1 : 0))
}
/** USD cost: '—' when unknown (model without a price), '$0' for mock runs, small values with 2 significant digits. */
export const fmtCost = (c?: number | null) => c == null ? '—' : c === 0 ? '$0' : c < 0.01 ? `$${c.toPrecision(2)}` : `$${c.toFixed(2)}`
/** History rows carry metrics/trace_url; replaying them appends the same run_summary event the socket sends live. */
export const withSummary = (h: { id: string; status: string; events: RunEvent[]; metrics?: RunMetrics | null; trace_id?: string | null; trace_url?: string | null }): RunEvent[] =>
  h.metrics ? [...h.events, { type: 'run_summary', run_id: h.id, status: h.status, metrics: h.metrics, trace_id: h.trace_id, trace_url: h.trace_url }] : h.events
export const fmtMs = (ms?: number) => ms == null ? '—' : ms < 1 ? `${ms.toFixed(2)} ms` : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`
