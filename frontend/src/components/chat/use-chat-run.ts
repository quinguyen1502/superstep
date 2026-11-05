/** One chat's turns and its live run (TASK-0085): a message or a Human answer goes over the run socket like a studio
 *  run, so the steps and the reply stream; public v1 endpoints use their typed handshake/frames, adapted to the same
 *  presentation. When the socket closes the session is read again for the saved answer. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { v1ChatEvent, v1ChatRequest } from '@/lib/chat-v1'
import { api, wsUrl } from '@/lib/api'
import { useOnChange } from '@/lib/use-when'
import { eventErrors, uiLocale } from '@/lib/i18n'
import { buildTrace, type RunEvent } from '@/lib/trace'
import { answers, waitingTurn, type ChatAttachment, type ChatSessionFull } from '@/lib/chat'
import type { ChatEdit } from '@superstep/sdk/chat'

export type ChatView = 'builder' | 'visitor'
/** Where a chat is read and where its messages go: the studio (default), or the public page's API and socket. Callers
 *  memoise it: a new object reloads the chat. */
export type ChatEndpoint = { session: (sid: string) => string; socket: string; headers?: Record<string, string>; v1?: boolean; visitor?: string }
const studio = (view: ChatView): ChatEndpoint => ({ session: sid => `/api/chat/sessions/${sid}?view=${view}`, socket: '/ws/run' })
const POLL_MS = 250, POLL_TRIES = 40   // the answer is written by the worker just after the run ends

export function useChatRun(sid: string | null, view: ChatView, onSettled?: () => void, endpoint?: ChatEndpoint, onSelect?: (id: string) => void,
  onRunEvent?: (event: RunEvent) => void) {
  const fallback = useMemo(() => studio(view), [view]); const ep = endpoint ?? fallback
  const [session, setSession] = useState<ChatSessionFull | null>(null)
  const [events, setEvents] = useState<RunEvent[]>([]); const [pending, setPending] = useState<string | null>(null)
  const [running, setRunning] = useState(false); const [error, setError] = useState('')
  const [queuedEdit, setQueuedEdit] = useState<ChatEdit | null>(null)
  const ws = useRef<WebSocket | null>(null); const alive = useRef(true)
  // TASK-0209: the message being shown. A settle of an older message must not clear a newer one's pending turn.
  const gen = useRef(0)
  const settled = useRef(onSettled); useEffect(() => { settled.current = onSettled })
  const select = useRef(onSelect); useEffect(() => { select.current = onSelect })
  const observer = useRef(onRunEvent); useEffect(() => { observer.current = onRunEvent })
  const load = useCallback((id = sid) => id ? api<ChatSessionFull>(ep.session(id), { headers: ep.headers }) : Promise.resolve(null), [sid, ep])

  useOnChange(`${sid}|${view}`, () => { gen.current++; setSession(null); setEvents([]); setPending(null); setRunning(false); setError(''); if (queuedEdit && sid !== queuedEdit.session.id) setQueuedEdit(null) })   // another chat or view: start clean
  useEffect(() => { alive.current = true
    load().then(s => alive.current && setSession(s)).catch(e => alive.current && setError(e.message))
    return () => { alive.current = false; ws.current?.close() } }, [load])

  /** Read the session again until the run's answer count grows (or give up and show what is there). */
  const settle = useCallback(async (id: string, runId: string | undefined, before: number, mine: number) => {
    const current = () => alive.current && gen.current === mine
    for (let i = 0; i < POLL_TRIES && current(); i++) {
      const s = await load(id).catch(() => null)
      if (s && (answers(s.turns, runId) > before || !runId || i === POLL_TRIES - 1)) {
        if (current()) { setSession(s); setEvents([]); setPending(null); setRunning(false); settled.current?.() } return }
      await new Promise(r => setTimeout(r, POLL_MS))
    }
    if (current()) setRunning(false)
  }, [load])

  const stream = useCallback((msg: Record<string, unknown>, shown: string | null, before: number, resumeOf?: string) => {
    if (!sid) return
    setError(''); setEvents([]); setPending(shown); setRunning(true); const mine = ++gen.current
    const sock = new WebSocket(wsUrl(ep.socket)); ws.current = sock; let runId = resumeOf
    let sent = false, sequence = -1
    sock.onopen = () => { if (!ep.v1) sock.send(JSON.stringify({ chat_session_id: sid, ...msg, locale: uiLocale() })) }
    sock.onmessage = m => {
      if (!alive.current || gen.current !== mine) return
      let frame: RunEvent & { v?: number; seq?: number; protocol?: string }
      try { frame = JSON.parse(m.data) } catch { return }
      if (!frame || typeof frame !== 'object') return
      if (ep.v1) {
        if (frame.v !== 1 || !Number.isSafeInteger(frame.seq) || frame.seq! <= sequence) return
        sequence = frame.seq!
        if (frame.type === 'ready' && frame.protocol === 'superstep-chat' && !sent) {
          sock.send(JSON.stringify({ type: 'auth', ...(ep.visitor ? { visitor: ep.visitor } : {}) }))
          sock.send(JSON.stringify(v1ChatRequest(sid, msg, uiLocale()))); sent = true; return
        }
      }
      const ev = ep.v1 ? v1ChatEvent(frame) : frame
      if (!ev) return
      if (ev.run_id) runId = ev.run_id
      if (runId) observer.current?.({ ...ev, run_id: runId })
      if (ev.type === 'error' && !ev.node && !runId) setError(eventErrors(ev).join('; '))
      setEvents(l => [...l, ev]) }
    // still running until the saved answer is read: until then the session on screen is the one from before this
    // message (its question still looks open), so the composer must not send the next message as an answer to it
    sock.onclose = () => { if (gen.current !== mine) return
      if (runId) settle(sid, runId, resumeOf ? before : 0, mine); else { setRunning(false); setPending(null) } }
  }, [sid, settle, ep])

  /** Sends a message, with the files already uploaded for it (TASK-0177): shown on the pending turn until the answer. */
  const [pendingFiles, setPendingFiles] = useState<ChatAttachment[]>([])
  const send = useCallback((text: string, files: ChatAttachment[] = []) => { setPendingFiles(files)
    stream(files.length ? { message: text, attachment_ids: files.map(f => f.id) } : { message: text }, text, 0) }, [stream])
  const revise = async (action: 'edit' | 'regenerate', turn: string, text: string | undefined, operationId: string) => {
    const tip = session?.turns[session.turns.length - 1]?.id
    if (!sid || !tip || running || !select.current) return
    const mine = gen.current; setRunning(true); setError('')
    try {
      const intent = await api<ChatEdit>(ep.session(sid).split('?')[0] + (action === 'edit' ? '/edits' : '/regenerations'), { method: 'POST', headers: ep.headers,
        json: { turn_id: turn, ...(action === 'edit' ? { message: text } : {}), operation_id: operationId, expected_last_turn_id: tip } })
      if (!alive.current || gen.current !== mine) return
      setQueuedEdit(intent); select.current(intent.session.id)
    } catch (e) { if (alive.current && gen.current === mine) setRunning(false); throw e }
  }
  useEffect(() => {
    if (!queuedEdit || queuedEdit.session.id !== sid || session?.id !== sid) return
    const intent = queuedEdit; setQueuedEdit(null); setPendingFiles([])
    if (intent.state !== 'prepared') {
      setRunning(true); void settle(sid, intent.run_id, 0, ++gen.current)
    } else stream({ message: intent.message, attachment_ids: intent.attachment_ids, edit_operation_id: intent.operation_id }, intent.message, 0)
  }, [queuedEdit, session?.id, sid, stream, settle])
  const answer = (runId: string, response: string) => { setPendingFiles([])
    const node = buildTrace(events).waiting?.node || waitingTurn(session?.turns ?? [])?.node || undefined
    stream({ resume_run_id: runId, response, ...(node ? { node } : {}) }, response, answers(session?.turns ?? [], runId), runId)
  }
  const cancel = () => ws.current?.readyState === WebSocket.OPEN && ws.current.send(JSON.stringify({ type: 'cancel' }))
  return { session, events, trace: buildTrace(events), pending, pendingFiles, running, error, send,
    edit: (turn: string, text: string, operationId: string) => revise('edit', turn, text, operationId),
    regenerate: (turn: string, operationId: string) => revise('regenerate', turn, undefined, operationId),
    answer, cancel, reload: () => load().then(setSession) }
}
