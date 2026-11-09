/** Pure graph edits shared by keyboard shortcuts, buttons and (later) the history/clipboard (+). */
import type { Edge, Node } from '@xyflow/react'

/** Start and End anchor every workflow: a delete always keeps at least one of each (extra copies can go). */
export const PROTECTED = new Set(['start', 'end'])

/** The ids in `nodeIds` that may be removed: all but the last remaining Start and the last remaining End. */
export function removable(nodes: Node[], nodeIds: Iterable<string>): Set<string> {
  const want = new Set(nodeIds)
  const out = new Set([...want].filter(id => !PROTECTED.has(nodes.find(n => n.id === id)?.type ?? '')))
  for (const type of PROTECTED) {
    const all = nodes.filter(n => n.type === type)
    const keep = all.find(n => !want.has(n.id)) ?? all[0]  // one stays: an unselected one if there is, else the first
    for (const n of all) if (want.has(n.id) && n !== keep) out.add(n.id)
  }
  return out
}

/** Remove nodes and edges by id (see `removable`), plus every edge touching a removed node. */
export function removeElements(nodes: Node[], edges: Edge[], nodeIds: Iterable<string>, edgeIds: Iterable<string> = []) {
  const gone = removable(nodes, nodeIds)
  const drop = new Set(edgeIds)
  return {
    nodes: nodes.filter(n => !gone.has(n.id)),
    edges: edges.filter(e => !drop.has(e.id) && !gone.has(e.source) && !gone.has(e.target)),
    removed: gone.size + edges.filter(e => drop.has(e.id)).length,
  }
}

const edgeId = () => `e${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`

function spot(from: { x: number; y: number } | null, to: { x: number; y: number }, fallback: { x: number; y: number }) {
  if (!from) return fallback
  const dx = to.x - from.x, dy = to.y - from.y
  if (Math.hypot(dx, dy) < 48) return { x: from.x + 200, y: from.y }
  return { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 }
}

function centroid(points: { x: number; y: number }[]) {
  if (!points.length) return null
  return { x: points.reduce((s, p) => s + p.x, 0) / points.length, y: points.reduce((s, p) => s + p.y, 0) / points.length }
}

/** Place `node` on the flow and rewire edges so it sits before, after, or on top of an existing connection.
 *  Branch labels stay on the edges that already had them. One call is one history step. */
export function spliceNode(nodes: Node[], edges: Edge[], node: Node, where: { dir: 'before' | 'after'; anchor: string } | { dir: 'edge'; edgeId: string }) {
  const rest = nodes.map(n => n.selected ? { ...n, selected: false } : n)
  if (where.dir === 'edge') {
    const edge = edges.find(e => e.id === where.edgeId)
    const source = rest.find(n => n.id === edge?.source), target = rest.find(n => n.id === edge?.target)
    if (!edge || !source || !target) return { nodes, edges }
    const placed = { ...node, position: spot(source.position, target.position, source.position) }
    return {
      nodes: [...rest, placed],
      edges: [...edges.filter(e => e.id !== edge.id), { ...edge, id: edgeId(), target: placed.id }, { id: edgeId(), source: placed.id, target: edge.target }],
    }
  }
  const anchor = rest.find(n => n.id === where.anchor)
  if (!anchor) return { nodes, edges }
  const toward = where.dir === 'before'
  const linked = edges.filter(e => toward ? e.target === anchor.id : e.source === anchor.id)
  const neighbors = linked.map(e => rest.find(n => n.id === (toward ? e.source : e.target))?.position).filter((p): p is { x: number; y: number } => !!p)
  const placed = { ...node, position: spot(centroid(neighbors), anchor.position, { x: anchor.position.x + (toward ? -220 : 220), y: anchor.position.y }) }
  const bridge = toward ? { id: edgeId(), source: placed.id, target: anchor.id } : { id: edgeId(), source: anchor.id, target: placed.id }
  const rewired = linked.length
    ? edges.map(e => toward && e.target === anchor.id ? { ...e, target: placed.id } : !toward && e.source === anchor.id ? { ...e, source: placed.id } : e)
    : edges
  return { nodes: [...rest, placed], edges: [...rewired, bridge] }
}

/** What a Delete press removes: the React Flow selection, falling back to the inspector's selected item. */
export function selectionIds(nodes: Node[], edges: Edge[], fallback?: { kind: 'node' | 'edge'; id: string } | null) {
  const n = nodes.filter(x => x.selected).map(x => x.id); const e = edges.filter(x => x.selected).map(x => x.id)
  if (!n.length && !e.length && fallback) (fallback.kind === 'node' ? n : e).push(fallback.id)
  return { nodeIds: n, edgeIds: e }
}
