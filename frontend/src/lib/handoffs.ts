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

/** Canvas links (TASK-0182): one dashed edge per hand-off, derived from the targets and never saved as a workflow edge.
 *  Its id is `handoff:<source>><target>`; the Agent node's `handoff` handle starts a new one. */
export const HANDOFF_HANDLE = 'handoff'
const PREFIX = 'handoff:'
export const isHandoffEdge = (id: string) => id.startsWith(PREFIX)
const edgeId = (source: string, target: string) => `${PREFIX}${source}>${target}`
const parse = (id: string) => { const [source, target] = id.slice(PREFIX.length).split('>'); return { source, target } }

export type HandoffEdge = { id: string; source: string; target: string; sourceHandle: string; className: string
  style: Record<string, string | number>; data: { handoff: true } }

export function handoffEdges(nodes: NodeLike[]): HandoffEdge[] {
  const agents = new Set(nodes.filter(n => n.type === 'agent').map(n => n.id))
  return nodes.filter(n => n.type === 'agent').flatMap(n => handoffsOf(n.data).filter(h => agents.has(h.target) && h.target !== n.id)
    .map(h => ({ id: edgeId(n.id, h.target), source: n.id, target: h.target, sourceHandle: HANDOFF_HANDLE, className: 'handoff-edge',
      style: { strokeDasharray: '6 4' }, data: { handoff: true as const } })))
}

/** Adds `target` to `source`'s hand-offs when both are distinct Agent nodes and it is not there yet. */
export function addHandoff<N extends NodeLike>(nodes: N[], source: string, target: string): N[] {
  const isAgent = (id: string) => nodes.some(n => n.id === id && n.type === 'agent')
  if (source === target || !isAgent(source) || !isAgent(target)) return nodes
  const src = nodes.find(n => n.id === source)!
  if (handoffsOf(src.data).some(h => h.target === target)) return nodes
  return nodes.map(n => n.id === source ? { ...n, data: { ...n.data, handoffs: [...handoffsOf(n.data), { target, description: '' }] } } : n)
}

/** Removes the hand-offs behind these canvas link ids. */
export function removeHandoffs<N extends NodeLike>(nodes: N[], ids: string[]): N[] {
  const gone = ids.filter(isHandoffEdge).map(parse)
  if (!gone.length) return nodes
  return nodes.map(n => {
    const drop = gone.filter(g => g.source === n.id).map(g => g.target)
    return drop.length ? { ...n, data: { ...n.data, handoffs: handoffsOf(n.data).filter(h => !drop.includes(h.target)) } } : n
  })
}
