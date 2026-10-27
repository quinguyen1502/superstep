/** A run's marks on the canvas (TASK-0147): each node's status badge (`_status`) and duration (`_dur`), from the run's
 *  events. One source for the live socket (one event at a time) and for opening a run from history (all its events),
 *  so the canvas also shows the steps a run took on the server, such as a parent's after its child run (TASK-0134). */
type Ev = { type: string; node?: string; duration_ms?: number; status?: string }
type CanvasNode = { id: string; data: Record<string, any> }

/** Trace events of nodes inside a subgraph or an Agent node carry `outer/inner` ids: the canvas shows them on the outer node. */
export const canvasId = (nid: string) => nid.split('/')[0]

/** The nodes after event `ev`: started → running, waiting, finished → done (with the duration of a canvas node's own
 *  step), an error on its node; a cancel or a timeout leaves the running nodes cancelled. Other events change nothing. */
export function markEvent<N extends CanvasNode>(nodes: N[], ev: Ev): N[] {
  const set = (patch: Record<string, any>, which: (n: N) => boolean) =>
    nodes.some(which) ? nodes.map(n => which(n) ? { ...n, data: { ...n.data, ...patch } } : n) : nodes
  const at = (id: string) => (n: N) => n.id === canvasId(id)
  const running = (n: N) => n.data._status === 'running'
  if (ev.type === 'node_started' && ev.node) return set({ _status: 'running' }, at(ev.node))
  if (ev.type === 'run_waiting' && ev.node) return set({ _status: 'waiting' }, at(ev.node))
  if (ev.type === 'node_finished' && ev.node) return set(ev.node.includes('/') ? { _status: 'done' } : { _status: 'done', _dur: ev.duration_ms }, at(ev.node))
  if (ev.type === 'error') {
    const marked = ev.node ? set({ _status: 'error' }, at(ev.node)) : nodes
    return ev.status === 'timeout' ? markEvent(marked, { type: 'run_cancelled' }) : marked
  }
  if (ev.type === 'run_cancelled') return set({ _status: 'cancelled' }, running)
  return nodes
}

/** The nodes with no run marks. */
export const clearMarks = <N extends CanvasNode>(nodes: N[]): N[] => nodes.map(n => ({ ...n, data: { ...n.data, _status: '', _dur: null } }))

/** The nodes as a whole run left them: its events played over cleared marks. */
export const markRun = <N extends CanvasNode>(nodes: N[], events: Ev[]): N[] => events.reduce(markEvent, clearMarks(nodes))
