import { useCallback, useEffect, useEffectEvent, useMemo, useRef, useState } from 'react'
import { addEdge, useNodesState, useEdgesState, useReactFlow, type Node, type Edge, type Connection } from '@xyflow/react'
import { Trash2, Braces, ArrowRight, ArrowDown, History, LayoutTemplate, Share2, Webhook, CalendarClock, MessageSquare, MessagesSquare, Search, FileCode2 } from 'lucide-react'
import { useLocation, useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { freeSpot, openPalette, registerCommands, type PaletteCommand } from '@/lib/palette'
import { useDeleteWorkflow } from '@/components/delete-workflow'
import { SHORTCUTS } from '@/lib/shortcuts'
import { chatStore } from '@/lib/panel-sizes'
import { layoutGraph, type Direction } from '@/lib/layout'
import { clipStore, copySelection, pasteClip, type Clip } from '@/lib/clipboard'
import { canEdit, type Access } from '@/lib/rbac'
import { useDemoMode } from '@/lib/demo'
import { api, wsUrl, sessionExpired, signedIn } from '@/lib/api'
import i18n, { eventErrors, issueTexts, uiLocale, type Issue } from '@/lib/i18n'
import { useTranslation } from 'react-i18next'
import { useTheme } from '@/lib/theme'
import type { Channels } from '@/lib/approvals'
import { type Credential } from '@/components/credentials-dialog'
import { useProviders } from '@/lib/providers'
import { buildTrace, withSummary } from '@/lib/trace'
import type { BuiltinTool } from '@/lib/agent'
import { useShortcuts } from '@/lib/use-shortcuts'
import { useGraphHistory } from '@/lib/use-graph-history'
import { removeElements, selectionIds, spliceNode } from '@/lib/graph-ops'
import { META, INSERTABLE, DEFAULTS, samplePrompt, MENU_OF, MENU_IDS, ACTION_ICONS, canvasId, styleEdges, defaultInput, LOOP_LABELS, type Field, type LogItem } from './meta'

/** Editor state and actions (TASK-0040: moved out of pages/Editor.tsx). Panels read it through StudioContext. */
export function useStudio() {
  const { t } = useTranslation(); const { id } = useParams(); const [params] = useSearchParams(); const loc = useLocation()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [state, setState] = useState<Field[]>([])
  const [name, setName] = useState('Untitled')
  const [wid, setWid] = useState<string | undefined>()
  const [sel, setSel] = useState<{ kind: 'node' | 'edge'; id: string } | null>(null)
  const [input, setInput] = useState(() => i18n.t('samples.input'))
  const [log, setLog] = useState<LogItem[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [tools, setTools] = useState<BuiltinTool[]>([])  // name, doc and the parameters an Agent node's model fills
  const [mode, setMode] = useState('')
  const [source, setSource] = useState<any>(null)
  const [creds, setCreds] = useState<Credential[]>([])
  const providers = useProviders()
  const [channels, setChannels] = useState<Channels | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [tab, setTab] = useState('input')
  const [saves, setSaves] = useState(0)  // successful saves: the Code tab reloads the code after each (TASK-0071)
  const [running, setRunning] = useState(false)
  const [traceSel, setTraceSel] = useState<string | null>(null); const [replay, setReplay] = useState<string | null>(null)
  const [loadErr, setLoadErr] = useState<{ status: number; msg: string } | null>(null)
  const [access, setAccess] = useState<Access>('owner'); const [ownerEmail, setOwnerEmail] = useState<string | null>(null)
  const canSave = canEdit(access)  // viewers (share or global role) get a read-only editor; they can still run (TASK-0014)
  const demo = useDemoMode()
  const edit = canSave || !!demo  // the public demo: visitors edit locally and run, but never save
  const { dark } = useTheme()
  const rf = useReactFlow(); const idc = useRef(1); const wsRef = useRef<WebSocket | null>(null)

  // unsaved-changes tracking (TASK-0019): snapshot of the saved graph, taken after load/save
  const savedSnap = useRef<string | null>(null); const takeBaseline = useRef(false)
  const snap = () => { const { id: _id, ...rest } = toJSON(); return JSON.stringify(rest) }
  // undo/redo (TASK-0024): snapshots of nodes, edges and the state schema; reset whenever a workflow is (re)loaded
  const hist = useGraphHistory(nodes, edges, state, h => { setNodes(h.nodes.map(n => ({ ...n }))); setEdges(styleEdges(h.edges)); setState(h.state) })
  // after a load, the first graph that renders becomes the saved snapshot and the start of the undo history
  const takeSnapshot = useEffectEvent(() => { if (takeBaseline.current) { takeBaseline.current = false; savedSnap.current = snap(); hist.reset(nodes, edges, state) } })
  useEffect(() => { takeSnapshot() }, [nodes, edges, name, state])
  const load = (wf: any) => {
    takeBaseline.current = true
    setName(wf.name); setWid(wf.id); setState(wf.state || [])
    setSource(wf.source || null)
    if (wf.access) { setAccess(wf.access); setOwnerEmail(wf.mine ? null : wf.owner_email ?? null) }
    setNodes(wf.needs_layout ? layoutGraph(wf.nodes, wf.edges, 'LR', false) : wf.nodes); setEdges(styleEdges(wf.edges))
    if (wf.source) setInput(defaultInput(wf.state || []))
  }
  const loadHistory = (id?: string) => id ? api<any[]>(`/api/workflows/${id}/runs`).then(hs => { setHistory(hs); return hs }) : undefined
  const openRun = (h: any) => { setLog(withSummary(h)); setReplay(h.id); setTraceSel(null); setTab('logs') }
  // each workflow id loads the graph, its run history (?run=<id> opens that run), and the editor's lookups
  const openWorkflow = useEffectEvent(() => {
    api(`/api/workflows/${id}`).then(wf => { setLoadErr(null); load(wf)
      // a workflow just made from a template: what it still needs (a knowledge base, a server...), as a save shows it
      const st = loc.state as { errors?: unknown; issues?: Issue[] } | null; const pending = st?.errors
      if (Array.isArray(pending) && pending.length) {
        setErrors(issueTexts(pending.map(String), st?.issues)); setTab('input')
        nav(`${loc.pathname}${loc.search}`, { replace: true, state: null })  // once: a reload must not bring them back
      }
      // ?run=<id> (from the pending list) opens that run with its Human panel
      loadHistory(wf.id)?.then((hs: any[]) => { const h = hs?.find(x => x.id === params.get('run')); if (h) openRun(h) }) })
      .catch(e => setLoadErr({ status: e.status ?? 0, msg: e.message }))
    api('/api/tools').then(setTools).catch(() => {})
    api<Credential[]>('/api/credentials').then(setCreds).catch(() => {})
    api<Channels>('/api/approvals/channels').then(setChannels).catch(() => {})
    api('/api/health').then(h => setMode(h.llm_mode)).catch(() => {})
  })
  useEffect(() => { openWorkflow() }, [id])

  const toJSON = () => ({
    id: wid, name, state,
    nodes: nodes.map(n => ({ id: n.id, type: n.type, position: n.position, data: Object.fromEntries(Object.entries(n.data).filter(([k]) => !k.startsWith('_'))) })),
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, ...(e.label ? { label: String(e.label) } : {}), ...((e as any).conditional ? { conditional: true } : {}) })),
  })
  const save = async () => {
    try {
      const r = await api('/api/workflows', { method: 'POST', json: toJSON() })
      setWid(r.id); setErrors(issueTexts(r.errors, r.issues)); savedSnap.current = snap(); setSaves(n => n + 1); if (r.errors.length) setTab('input')
    } catch (e: any) { setErrors([t('editor.saveFailed', { error: e.message })]); setTab('input') }
  }
  const mark = (id: string, patch: any) => setNodes(ns => ns.map(n => n.id === id ? { ...n, data: { ...n.data, ...patch } } : n))
  /** One socket path for new runs and for resuming a waiting run (the resumed events append to the same log). */
  const stream = (msg: any, resume = false) => {
    if (!signedIn()) { setErrors([t('editor.expiredRedirect')]); setTab('logs'); setTimeout(sessionExpired, 1500); return }
    setErrors([]); setTab('logs'); setRunning(true); setTraceSel(null)
    if (resume) setLog(l => l.filter(e => e.type !== 'run_summary'))
    else { setLog([]); setReplay(null); setNodes(ns => ns.map(n => ({ ...n, data: { ...n.data, _status: '', _dur: null } }))) }
    const ws = new WebSocket(wsUrl('/ws/run')); wsRef.current = ws
    ws.onopen = () => ws.send(JSON.stringify({ ...msg, locale: uiLocale() }))  // the mock model answers in the UI language
    ws.onmessage = m => {
      const ev: LogItem = JSON.parse(m.data); setLog(l => [...l, ev])
      if (ev.type === 'node_started') mark(canvasId(ev.node!), { _status: 'running' })
      if (ev.type === 'run_waiting') mark(canvasId(ev.node!), { _status: 'waiting' })
      if (ev.type === 'node_finished') mark(canvasId(ev.node!), ev.node!.includes('/') ? { _status: 'done' } : { _status: 'done', _dur: ev.duration_ms })
      if (ev.type === 'error') { setErrors(eventErrors(ev)); if (ev.node) mark(canvasId(ev.node), { _status: 'error' }) }
      if (ev.type === 'run_cancelled' || (ev.type === 'error' && (ev as any).status === 'timeout')) setNodes(ns => ns.map(n => n.data._status === 'running' ? { ...n, data: { ...n.data, _status: 'cancelled' } } : n))
    }
    ws.onerror = () => setErrors(e => e.length ? e : [t('editor.wsLost')])
    ws.onclose = ev => {
      if (ev.code === 4401) { setErrors([t('editor.expiredDuringRun')]); setTimeout(sessionExpired, 1500) }
      setRunning(false); setNodes(ns => ns.map(n => n.data._status === 'running' ? { ...n, data: { ...n.data, _status: 'error' } } : n)); loadHistory(wid) }
  }
  const run = () => {
    let inp: any; try { inp = JSON.parse(input) } catch { setErrors([t('editor.badInput')]); setTab('input'); return }
    stream({ workflow_id: wid, workflow: toJSON(), input: inp })
  }
  const respond = (runId: string, response: string) => stream({ resume_run_id: runId, response }, true)
  /** Time travel: a new run from a checkpoint of `runId`, with its state or an edited one. */
  const fork = (runId: string, checkpoint: number, state?: Record<string, unknown>) => stream({ fork: { run_id: runId, checkpoint, ...(state ? { state } : {}) } })
  const cancelRun = () => wsRef.current?.readyState === WebSocket.OPEN && wsRef.current.send(JSON.stringify({ type: 'cancel' }))
  const removeIds = (nodeIds: string[], edgeIds: string[] = []) => {
    const r = removeElements(nodes, edges, nodeIds, edgeIds); if (!r.removed) return
    setNodes(r.nodes); setEdges(r.edges); if (sel && (nodeIds.includes(sel.id) || edgeIds.includes(sel.id))) setSel(null)
  }
  // clipboard (TASK-0026, DEC-0029): pure copy/paste in lib/clipboard.ts; one paste = one render = one undo step
  const clipMem = useRef<Clip | null>(null); const pasteN = useRef(0)
  const [clipNote, setClipNote] = useState(''); const noteTimer = useRef<number>(0)
  const note = (m: string) => { setClipNote(m); window.clearTimeout(noteTimer.current); noteTimer.current = window.setTimeout(() => setClipNote(''), 2500) }
  const selClip = () => { const s = selectionIds(nodes, edges, sel); return copySelection(nodes, edges, s.nodeIds) }
  const insert = (clip: Clip, n: number) => {
    const sameCanvas = clip.nodes.some(c => nodes.some(x => x.id === c.id))
    const view = rf.screenToFlowPosition({ x: window.innerWidth / 2 - 120, y: window.innerHeight / 2 - 60 })
    const r = pasteClip(clip, { existing: nodes.map(x => x.id), usableCredentials: new Set(creds.map(c => c.id)), offset: 40 * n, at: sameCanvas ? undefined : view })
    setNodes(ns => [...ns.map(x => x.selected ? { ...x, selected: false } : x), ...r.nodes]); setEdges(es => [...es.map(x => x.selected ? { ...x, selected: false } : x), ...styleEdges(r.edges)])
    setSel(r.nodes.length === 1 ? { kind: 'node', id: r.nodes[0].id } : null)
    note(r.clearedCredentials ? t('clipboard.pastedCleared', { count: r.nodes.length, creds: r.clearedCredentials }) : t('clipboard.pasted', { count: r.nodes.length }))
  }
  /** Keep a copied clip (memory + this browser's store) and say so; `cut` also removes the copied nodes. */
  const keep = (c: Clip, cut: boolean) => {
    clipMem.current = c; pasteN.current = 0; clipStore.write(c)
    if (cut) { removeIds(c.nodes.map(n => n.id)); note(t('clipboard.cut', { count: c.nodes.length })) } else note(t('clipboard.copied', { count: c.nodes.length }))
  }
  const copy = (cut = false) => { const c = selClip(); if (!c) return false; keep(c, cut) }
  const copyIds = (ids: string[], cut = false) => { const c = copySelection(nodes, edges, ids); if (c) keep(c, cut) }  // node context menu

  const editable = edit && !source
  // auto-layout (TASK-0027, DEC-0030): one setNodes = one undo step; direction remembered per browser
  const [layoutDir, setLayoutDir] = useState<Direction>(() => (localStorage.getItem('lgs.layoutDir') as Direction) === 'TB' ? 'TB' : 'LR')
  const tidy = (dir: Direction = layoutDir) => {
    if (!editable) return false
    if (dir !== layoutDir) { setLayoutDir(dir); localStorage.setItem('lgs.layoutDir', dir) }
    setNodes(ns => layoutGraph(ns, edges, dir)); window.setTimeout(() => rf.fitView({ duration: 250 }), 30)
  }
    // keyboard shortcuts (TASK-0023): one registry (lib/shortcuts.ts) drives this map and the cheat sheet
  const [cheat, setCheat] = useState(false)
  // the Chat side panel (TASK-0085): open state survives a reload, like its width (lib/panel-sizes.ts)
  const [chatOpen, setChatOpenState] = useState(() => chatStore.read().open)
  const canChat = !!wid && !source
  const setChatOpen = (open: boolean) => { setChatOpenState(open); chatStore.write({ open }) }
  const handlers: Record<string, () => void | boolean> = {
    save: () => { if (canSave) save() },
    run: () => { if (!running) run() },
    stop: () => { if (running) cancelRun() },
    delete: () => { if (!edit || source) return false; const s = selectionIds(nodes, edges, sel); removeIds(s.nodeIds, s.edgeIds) },
    selectAll: () => { setNodes(ns => ns.map(n => ({ ...n, selected: true }))); setEdges(es => es.map(e => ({ ...e, selected: true }))) },
    fitView: () => { rf.fitView({ duration: 200 }) },
    zoomIn: () => { rf.zoomIn({ duration: 150 }) },
    zoomOut: () => { rf.zoomOut({ duration: 150 }) },
    escape: () => { setSel(null); setNodes(ns => ns.map(n => n.selected ? { ...n, selected: false } : n)); setEdges(es => es.map(e => e.selected ? { ...e, selected: false } : e)); return false },
    cheatsheet: () => setCheat(true),
    layout: () => tidy(),
    copy: () => copy(),
    cut: () => editable ? copy(true) : false,
    paste: () => { if (!editable) return false; const c = clipStore.read() ?? clipMem.current; if (!c) return false; insert(c, ++pasteN.current) },
    duplicate: () => { if (!editable) return false; const c = selClip(); if (!c) return; insert(c, 1) },
    undo: () => { if (edit) hist.undo() },
    redo: () => { if (edit) hist.redo() },
    chat: () => { if (!canChat) return false; setChatOpen(!chatOpen) },
  }
  useShortcuts(handlers)
  // command palette (TASK-0028, DEC-0031): registry actions, add node, jump to node — re-registered each render so closures stay fresh
  const freshNode = (type: string) => ({
    id: `${type}_${Date.now().toString(36)}${idc.current++}`, type, position: { x: 0, y: 0 }, selected: true,
    data: { ...DEFAULTS[type], ...samplePrompt(type) },
  })
  const insertAround = (type: string, where: { dir: 'before' | 'after'; anchor: string } | { dir: 'edge'; edgeId: string }) => {
    const r = spliceNode(nodes, edges, freshNode(type), where)
    setNodes(r.nodes); setEdges(styleEdges(r.edges))
    const added = r.nodes.find(n => !nodes.some(x => x.id === n.id))
    if (added) setSel({ kind: 'node', id: added.id })
  }
  const addNode = (type: string, pos: { x: number; y: number }, select = false) => {
    const id = `${type}_${Date.now().toString(36)}${idc.current++}`
    setNodes(ns => [...(select ? ns.map(n => n.selected ? { ...n, selected: false } : n) : ns), { id, type, position: pos, selected: select,
      data: { ...DEFAULTS[type], ...samplePrompt(type) } }])
    if (select) setSel({ kind: 'node', id })
  }
  const addNote = (pos: { x: number; y: number }) => {
    const id = `note_${Date.now().toString(36)}${idc.current++}`
    setNodes(ns => [...ns.map(n => n.selected ? { ...n, selected: false } : n),
      { id, type: 'note', position: pos, selected: true, connectable: false, data: { text: '' } }])
    setSel({ kind: 'node', id })
  }
  const off: Record<string, boolean> = { save: !canSave, run: running, stop: !running, undo: !hist.canUndo, redo: !hist.canRedo,
    ...Object.fromEntries(['delete', 'cut', 'paste', 'duplicate', 'layout'].map(k => [k, !editable])) }
  const paletteRef = useRef<Record<string, () => void>>({})
  // secondary editor actions (TASK-0028 follow-up): one list feeds the ⋯ menu and the command palette
  const [dlg, setDlg] = useState<null | 'share' | 'versions' | 'api' | 'schedules' | 'chat' | 'chatSettings' | 'template' | 'json'>(null)
  const [ctx, setCtx] = useState<null | { kind: 'node' | 'edge'; id: string } | { kind: 'pane'; at: { x: number; y: number } }>(null)
  const nav = useNavigate(); const delWf = useDeleteWorkflow(() => nav('/workflows'))
  const isDirty = () => savedSnap.current !== null && snap() !== savedSnap.current
  const menuExtras: PaletteCommand[] = [
    ...(['LR', 'TB'] as Direction[]).map(d => ({ id: `action:layout${d}`, group: 'actions' as const, label: `${t('layout.button')}: ${t(d === 'LR' ? 'layout.lr' : 'layout.tb')}`, icon: d === 'LR' ? ArrowRight : ArrowDown,
      menu: 'arrange' as const, elementId: `layout-${d.toLowerCase()}`, disabled: !editable, hint: layoutDir === d ? '✓' : undefined, run: () => { tidy(d) } })),
    { id: 'action:versions', group: 'actions', label: t('versions.button'), icon: History, menu: 'workflow', elementId: 'versions-btn', disabled: !wid, run: () => setDlg('versions') },
    { id: 'action:saveTemplate', group: 'actions', label: t('templates.saveAs'), icon: LayoutTemplate, menu: 'workflow', elementId: 'save-template-btn', disabled: !canSave || !wid, run: () => setDlg('template') },
    { id: 'action:share', group: 'actions', label: t('share.button'), icon: Share2, menu: 'workflow', elementId: 'share-btn', disabled: !wid, run: () => setDlg('share') },
    { id: 'action:api', group: 'actions', label: t('api.button'), icon: Webhook, menu: 'workflow', elementId: 'api-btn', disabled: !wid || access !== 'owner', run: () => setDlg('api') },
    { id: 'action:schedules', group: 'actions', label: t('schedules.button'), icon: CalendarClock, menu: 'workflow', elementId: 'schedules-btn', disabled: !wid || access !== 'owner', run: () => setDlg('schedules') },
    { id: 'action:chatTriggers', group: 'actions', label: t('chatTriggers.button'), icon: MessageSquare, menu: 'workflow', elementId: 'chat-triggers-btn', disabled: !wid || access !== 'owner' || !!source, run: () => setDlg('chat') },
    { id: 'action:chatSettings', group: 'actions', label: t('chat.settings.title'), icon: MessagesSquare, menu: 'workflow', elementId: 'chat-settings-menu', disabled: !wid || access !== 'owner' || !!source, run: () => setDlg('chatSettings') },
    { id: 'action:json', group: 'actions', label: t('editor.jsonTitle'), icon: Braces, menu: 'workflow', elementId: 'json-btn', run: () => setDlg('json') },
    { id: 'action:code', group: 'actions', label: t('codeView.button'), icon: FileCode2, menu: 'workflow', elementId: 'code-btn', keywords: ['langgraph', 'python', 'export'],
      disabled: !!source, run: () => setTab('code') },
    { id: 'action:openPalette', group: 'actions', label: t('palette.title'), icon: Search, shortcut: 'palette', menu: 'help', elementId: 'palette-btn', run: openPalette },
    { id: 'action:deleteWorkflow', group: 'actions', label: t('editor.deleteWorkflow'), icon: Trash2, menu: 'danger', destructive: true, elementId: 'delete-wf-btn',
      disabled: !wid || access !== 'owner', run: () => { if (wid) delWf.ask({ id: wid, name }) } },
  ]
  const paletteCmds: PaletteCommand[] = [
    ...SHORTCUTS.filter(x => handlers[x.id] && x.id !== 'escape').map(x => ({ id: `action:${x.id}`, group: 'actions' as const, label: t(`shortcuts.actions.${x.id}`), shortcut: x.id, disabled: off[x.id],
      icon: ACTION_ICONS[x.id], menu: MENU_OF[x.id], elementId: MENU_IDS[x.id], run: () => { handlers[x.id]() } })),
    ...menuExtras,
    ...(editable ? INSERTABLE.map(x => ({ id: `add:${x}`, group: 'add' as const, label: t('palette.addNode', { type: META[x].label }), hint: t(`nodes.${x}`), icon: META[x].icon, keywords: [x],
      run: () => { const c = rf.screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 }); addNode(x, freeSpot(c, nodes.map(n => n.position)), true) } })) : []),
    ...nodes.filter(n => n.type !== 'note').map(n => ({ id: `node:${n.id}`, group: 'nodes' as const, label: String((n.data as any)?.label || n.id), hint: `${META[n.type!]?.label ?? n.type} · ${n.id}`, icon: META[n.type!]?.icon, keywords: [n.id, n.type!],
      run: () => { setNodes(ns => ns.map(x => ({ ...x, selected: x.id === n.id }))); setSel({ kind: 'node', id: n.id }); rf.fitView({ nodes: [{ id: n.id }], duration: 300, maxZoom: 1.2 }) } })),
  ]
  paletteCmds.forEach(c => { paletteRef.current[c.id] = c.run })
  const paletteSig = paletteCmds.map(c => `${c.id}|${c.label}|${c.hint ?? ''}|${c.disabled ? 1 : 0}`).join('\n')
  // re-register only when the visible content changes (runs read the latest closures through paletteRef)
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => registerCommands('editor', paletteCmds.map(c => ({ ...c, run: () => paletteRef.current[c.id]?.() }))), [paletteSig])

  const trace = useMemo(() => buildTrace(log as any, nid => { const n = nodes.find(x => x.id === nid); return { label: (n?.data as any)?.label, type: n?.type } }), [log, nodes])
  const traceMeta = (t: string) => META[t] || META.code
  const step = () => {
    if (trace.paused?.runId) { stream({ resume_run_id: trace.paused.runId, steps: 1 }, true); return }
    let inp: any; try { inp = JSON.parse(input) } catch { setErrors([t('editor.badInput')]); setTab('input'); return }
    stream({ workflow_id: wid, workflow: toJSON(), input: inp, steps: 1 })
  }
  const continueRun = () => { if (trace.paused?.runId) stream({ resume_run_id: trace.paused.runId }, true) }
  const hlSpan = traceSel ? trace.spans.find(x => x.key === traceSel)?.node : undefined
  const hlNode = hlSpan ? canvasId(hlSpan) : undefined
  const nodesView = useMemo(() => nodes.map(n => {
    const base = n.type === 'note' ? { ...n, connectable: false } : n
    return hlNode && base.id === hlNode ? { ...base, data: { ...base.data, _hl: true } } : base
  }), [nodes, hlNode])
  const onNodeClick = (id: string) => {
    setSel({ kind: 'node', id })
    const spans = trace.spans.filter(x => canvasId(x.node) === id)
    if (spans.length) {
      const cur = spans.findIndex(x => x.key === traceSel) // repeated clicks cycle through loop iterations
      setTraceSel(spans[cur >= 0 ? (cur + 1) % spans.length : spans.length - 1].key); setTab('logs')
    }
  }
  const onConnect = useCallback((c: Connection) => setEdges(es => {
    // a For each node's first edge is its loop body, the second leaves the loop (TASK-0049)
    const loop = rf.getNode(c.source)?.type === 'foreach' ? LOOP_LABELS.find(l => !es.some(e => e.source === c.source && e.label === l)) : undefined
    return addEdge({ ...c, id: 'e' + Date.now(), ...(loop ? { label: loop } : {}) }, es)
  }), [setEdges, rf])
  const onDrop = (ev: React.DragEvent) => {
    ev.preventDefault(); if (!edit) return; const t = ev.dataTransfer.getData('nodetype'); if (!t) return
    addNode(t, rf.screenToFlowPosition({ x: ev.clientX, y: ev.clientY }))
  }
  const selNode = sel?.kind === 'node' ? nodes.find(n => n.id === sel.id) : undefined
  const selEdge = sel?.kind === 'edge' ? edges.find(e => e.id === sel.id) : undefined
  const upd = (k: string, v: any) => selNode && mark(selNode.id, { [k]: v })
  const setRuntime = (patch: Record<string, unknown>) => selNode && setNodes(ns => ns.map(n => {
    if (n.id !== selNode.id) return n
    const data = { ...n.data } as Record<string, unknown>
    for (const [k, v] of Object.entries(patch)) { if (v === undefined) delete data[k]; else data[k] = v }
    return { ...n, data }
  }))
  const d: any = selNode?.data || {}
  const runTo = () => {
    if (!selNode) return
    const until = selNode.id
    if (trace.paused?.runId) { stream({ resume_run_id: trace.paused.runId, until }, true); return }
    let inp: any; try { inp = JSON.parse(input) } catch { setErrors([t('editor.badInput')]); setTab('input'); return }
    stream({ workflow_id: wid, workflow: toJSON(), input: inp, until })
  }
  const fieldNames = state.map(f => f.name)
  const [canvasLock, setCanvasLock] = useState(false)
  return {
    id, nodes, setNodes, onNodesChange, edges, setEdges, onEdgesChange, state, setState, name, setName, wid, setSel,
    input, setInput, log, setLog, errors, setErrors, tools, mode, source, creds, setCreds, providers, channels, history,
    tab, setTab, running, traceSel, setTraceSel, replay, setReplay, loadErr, access, ownerEmail, edit, canSave, dark, rf,
    hist, load, openRun, toJSON, save, mark, run, respond, fork, cancelRun, removeIds,
    clipNote, note, insert, editable, layoutDir, cheat, setCheat, insertAround, addNode, addNote, dlg, setDlg, ctx, setCtx,
    delWf, isDirty, saves, paletteCmds, trace, traceMeta, step, continueRun, nodesView, onNodeClick, onConnect, onDrop,
    selNode, selEdge, upd, setRuntime, d, runTo, fieldNames, canvasLock, setCanvasLock, copyIds, chatOpen: chatOpen && canChat, setChatOpen, canChat,
  }
}

export type Studio = ReturnType<typeof useStudio>
