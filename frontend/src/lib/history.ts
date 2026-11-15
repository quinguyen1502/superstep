/** Editor undo/redo: a pure, capped history of graph snapshots.
 * Consecutive changes with the same `key` inside `COALESCE_MS` merge into one step (typing in one field, one drag). */
export type Snap = { nodes: any[]; edges: any[]; state: any[] }
export type History = { past: Snap[]; present: Snap; future: Snap[]; key: string | null; at: number }

export const LIMIT = 100
export const COALESCE_MS = 1000

const same = (a: Snap, b: Snap) => JSON.stringify(a) === JSON.stringify(b)

export const init = (present: Snap): History => ({ past: [], present, future: [], key: null, at: 0 })

export function push(h: History, next: Snap, key: string | null = null, now = Date.now()): History {
  if (same(h.present, next)) return h
  if (key && key === h.key && now - h.at < COALESCE_MS) return { ...h, present: next, future: [], at: now }
  return { past: [...h.past, h.present].slice(-LIMIT), present: next, future: [], key, at: now }
}
export function undo(h: History): History {
  if (!h.past.length) return h
  return { past: h.past.slice(0, -1), present: h.past[h.past.length - 1], future: [h.present, ...h.future], key: null, at: 0 }
}
export function redo(h: History): History {
  if (!h.future.length) return h
  return { past: [...h.past, h.present], present: h.future[0], future: h.future.slice(1), key: null, at: 0 }
}

/** Graph content only: no runtime fields (`_status`, `_dur`, …), no selection/measurement, edges reduced to their meaning. */
export function snapshot(nodes: any[], edges: any[], state: any[]): Snap {
  return {
    nodes: nodes.map(n => ({ id: n.id, type: n.type, position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      data: Object.fromEntries(Object.entries(n.data || {}).filter(([k]) => !k.startsWith('_'))) })),
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, ...(e.sourceHandle ? { sourceHandle: e.sourceHandle } : {}),
      ...(e.label ? { label: String(e.label) } : {}), ...(e.conditional ? { conditional: true } : {}) })),
    state: state.map(f => ({ ...f })),
  }
}

/** Coalescing key for a change: edits to one node's settings, or to the state schema, merge; structure changes never do. */
export function changeKey(prev: Snap, next: Snap): string | null {
  if (JSON.stringify(prev.edges) !== JSON.stringify(next.edges) || prev.nodes.length !== next.nodes.length) return null
  if (JSON.stringify(prev.state) !== JSON.stringify(next.state)) return JSON.stringify(prev.nodes) === JSON.stringify(next.nodes) ? 'state' : null
  const changed = next.nodes.filter((n, i) => JSON.stringify(n.data) !== JSON.stringify(prev.nodes[i]?.data) || n.id !== prev.nodes[i]?.id)
  return changed.length === 1 && JSON.stringify(next.nodes.map(n => n.position)) === JSON.stringify(prev.nodes.map(n => n.position)) ? `data:${changed[0].id}` : null
}
