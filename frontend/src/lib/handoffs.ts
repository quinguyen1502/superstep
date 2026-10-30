/** Agent hand-offs (REQ-0078, DEC-0073): each Agent node lists the agents it may hand the conversation to in
 *  `data.handoffs` [{target, description}]; the workflow's `max_handoffs` (default 5, 0 to 20) bounds a run. */
export type Handoff = { target: string; description?: string }
export const DEFAULT_MAX_HANDOFFS = 5, MAX_HANDOFFS = 20

type NodeLike = { id: string; type?: string; data: Record<string, any> }

export const handoffsOf = (data: Record<string, any> | undefined): Handoff[] =>
  Array.isArray(data?.handoffs) ? data.handoffs.filter((h: any) => h && typeof h.target === 'string') : []

/** The nodes with every hand-off to a node that is gone (or no longer an Agent node) removed. Returns the same array
 *  when nothing changes, so it can run after every change without a new render. */
export function pruneHandoffs<N extends NodeLike>(nodes: N[]): N[] {
  const agents = new Set(nodes.filter(n => n.type === 'agent').map(n => n.id)); let changed = false
  const out = nodes.map(n => {
    if (n.type !== 'agent' || !Array.isArray(n.data?.handoffs)) return n
    const kept = handoffsOf(n.data).filter(h => h.target !== n.id && agents.has(h.target))
    if (kept.length === n.data.handoffs.length) return n
    changed = true; return { ...n, data: { ...n.data, handoffs: kept } }
  })
  return changed ? out : nodes
}
