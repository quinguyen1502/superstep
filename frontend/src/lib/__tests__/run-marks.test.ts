import { describe, expect, it } from 'vitest'
import { canvasId, clearMarks, markEvent, markRun } from '../run-marks'

const nodes = () => ['start', 'sup', 'end'].map(id => ({ id, data: { label: id } as Record<string, any> }))
const marks = (ns: { id: string; data: Record<string, any> }[]) => Object.fromEntries(ns.map(n => [n.id, [n.data._status, n.data._dur]]))
const statuses = (ns: { id: string; data: Record<string, any> }[]) => Object.fromEntries(ns.map(n => [n.id, n.data._status]))
const started = (node: string) => ({ type: 'node_started', node })
const finished = (node: string, duration_ms = 1) => ({ type: 'node_finished', node, duration_ms })

describe('run marks', () => {
  it('maps inner ids to their canvas node', () => {
    expect(canvasId('sup/__tool')).toBe('sup'); expect(canvasId('end')).toBe('end')
  })
  it('a parent that waited for its child run and finished on the server ends with every node done', () => {
    const events = [started('start'), finished('start', 0.4), started('sup'), finished('sup', 0.5), started('sup/__tool'),
      { type: 'run_waiting', node: 'sup/__tool' },
      // resumed on the server once the child ended
      finished('sup/__tool', 6), started('sup/__exit'), finished('sup/__exit'), started('end'), finished('end', 0.2), { type: 'run_finished' }]
    expect(marks(markRun(nodes(), events))).toEqual({ start: ['done', 0.4], sup: ['done', 0.5], end: ['done', 0.2] })
  })
  it('a run still waiting shows its waiting node', () => {
    const events = [started('start'), finished('start'), started('sup/__tool'), { type: 'run_waiting', node: 'sup/__tool' }]
    expect(statuses(markRun(nodes(), events))).toEqual({ start: 'done', sup: 'waiting', end: '' })
  })
  it('opening another run replaces the marks of the one shown before', () => {
    const shown = markRun(nodes(), [started('start'), finished('start'), started('sup'), finished('sup'), started('end'), finished('end')])
    expect(marks(markRun(shown, [started('start'), finished('start', 2)]))).toEqual({ start: ['done', 2], sup: ['', null], end: ['', null] })
  })
  it('an error marks its node; a timeout or a cancel leaves the running nodes cancelled', () => {
    expect(markEvent(nodes(), { type: 'error', node: 'sup/__model' }).find(n => n.id === 'sup')!.data._status).toBe('error')
    const running = markEvent(markEvent(nodes(), started('start')), started('sup'))
    expect(statuses(markEvent(running, { type: 'error', node: 'sup', status: 'timeout' }))).toEqual({ start: 'cancelled', sup: 'error', end: undefined })
    expect(statuses(markEvent(running, { type: 'run_cancelled' }))).toEqual({ start: 'cancelled', sup: 'cancelled', end: undefined })
  })
  it('leaves the nodes alone for events that mark nothing', () => {
    const ns = nodes()
    expect(markEvent(ns, { type: 'node_token', node: 'sup' })).toBe(ns)
    expect(markEvent(ns, finished('gone'))).toBe(ns)
    expect(clearMarks(ns)[0].data).toEqual({ label: 'start', _status: '', _dur: null })
  })
})
