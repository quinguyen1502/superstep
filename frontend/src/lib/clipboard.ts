/** Copy / cut / paste / duplicate of canvas nodes. Pure functions + a tiny localStorage store, so
 * a selection can be pasted into another workflow in the same browser. Start/End are never copied; only edges whose two
 * ends are both copied come along; pasted elements get fresh ids. */
import type { Edge, Node } from '@xyflow/react'
import { PROTECTED } from '@/lib/graph-ops'

export const CLIP_FORMAT = 'superstep/nodes', CLIP_VERSION = 1, CLIP_KEY = 'lgs.clipboard'
const FORMATS = new Set<string>([CLIP_FORMAT, 'langgraph-studio/nodes'])  // the v0.1.0 name is still pasted
export type ClipNode = { id: string; type: string; position: { x: number; y: number }; data: Record<string, unknown> }
export type ClipEdge = { id: string; source: string; target: string; label?: unknown; sourceHandle?: string | null; data?: unknown }
export type Clip = { format: typeof CLIP_FORMAT; version: number; nodes: ClipNode[]; edges: ClipEdge[] }

const clean = (d: Record<string, unknown> = {}) => Object.fromEntries(Object.entries(d).filter(([k]) => !k.startsWith('_')))  // no run status

/** The copyable part of a selection (null when nothing copyable is selected). */
export function copySelection(nodes: Node[], edges: Edge[], ids: Iterable<string>): Clip | null {
  const pick = new Set(ids)
  const ns = nodes.filter(n => pick.has(n.id) && !PROTECTED.has(n.type ?? ''))
  if (!ns.length) return null
  const keep = new Set(ns.map(n => n.id))
  return {
    format: CLIP_FORMAT, version: CLIP_VERSION,
    nodes: ns.map(n => ({ id: n.id, type: n.type!, position: { x: n.position.x, y: n.position.y }, data: structuredClone(clean(n.data as Record<string, unknown>)) })),
    edges: edges.filter(e => keep.has(e.source) && keep.has(e.target))
      .map(e => ({ id: e.id, source: e.source, target: e.target, ...(e.label != null && e.label !== '' ? { label: e.label } : {}), ...(e.sourceHandle ? { sourceHandle: e.sourceHandle } : {}), ...(e.data ? { data: structuredClone(e.data) } : {}) })),
  }
}

/** Parse a stored / pasted payload; anything else (other apps, older versions) → null. */
export function parseClip(raw: string | null): Clip | null {
  if (!raw) return null
  try {
    const c = JSON.parse(raw)
    return c && FORMATS.has(c.format) && c.version === CLIP_VERSION && Array.isArray(c.nodes) && Array.isArray(c.edges) && c.nodes.length ? c : null
  } catch { return null }
}

type PasteOpts = {
  existing: Iterable<string>        // ids already on the canvas
  usableCredentials?: Set<string>   // credential ids the user can use here; others are cleared
  at?: { x: number; y: number }     // place the group's top-left here; otherwise offset from the originals
  offset?: number
  seed?: () => string               // id suffix generator (deterministic in tests)
}

/** New nodes/edges for a paste: fresh unique ids, internal edges remapped, selected, credential refs filtered. */
export function pasteClip(clip: Clip, o: PasteOpts): { nodes: Node[]; edges: Edge[]; clearedCredentials: number } {
  const taken = new Set(o.existing); let n = 0
  const seed = o.seed ?? (() => Date.now().toString(36))
  const fresh = (base: string) => { const stem = base.replace(/_copy\d*$/, '').replace(/_[a-z0-9]{6,}\d*$/, ''); let id; do id = `${stem}_${seed()}${n++}`; while (taken.has(id)); taken.add(id); return id }
  const map = new Map(clip.nodes.map(c => [c.id, fresh(c.id)]))
  const minX = Math.min(...clip.nodes.map(c => c.position.x)), minY = Math.min(...clip.nodes.map(c => c.position.y))
  const off = o.offset ?? 40
  const dx = o.at ? o.at.x - minX : off, dy = o.at ? o.at.y - minY : off
  let cleared = 0
  const nodes: Node[] = clip.nodes.map(c => {
    const data = structuredClone(c.data)
    if (typeof data.credential_id === 'string' && data.credential_id && o.usableCredentials && !o.usableCredentials.has(data.credential_id)) { data.credential_id = ''; cleared++ }
    return { id: map.get(c.id)!, type: c.type, position: { x: c.position.x + dx, y: c.position.y + dy }, data, selected: true }
  })
  const edges: Edge[] = clip.edges.filter(e => map.has(e.source) && map.has(e.target)).map(e => ({
    ...(e as object), id: fresh(e.id.startsWith('e') ? 'e' : e.id), source: map.get(e.source)!, target: map.get(e.target)!, selected: false,
  }) as Edge)
  return { nodes, edges, clearedCredentials: cleared }
}

export const clipStore = {
  read: (): Clip | null => { try { return parseClip(localStorage.getItem(CLIP_KEY)) } catch { return null } },
  write: (c: Clip) => {
    const s = JSON.stringify(c)
    try { localStorage.setItem(CLIP_KEY, s) } catch { /* storage full / disabled: in-memory paste still works via the caller */ }
    try { void navigator.clipboard?.writeText(s).catch(() => {}) } catch { /* best effort, for pasting into a text editor */ }
  },
}
