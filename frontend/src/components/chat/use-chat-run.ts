/** One chat's turns and its live run (TASK-0085): a message or a Human answer goes over the run socket like a studio
 *  run, so the steps and the reply stream; when the socket closes the session is read again for the saved answer. */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, wsUrl } from '@/lib/api'
import { useOnChange } from '@/lib/use-when'
import { eventErrors, uiLocale } from '@/lib/i18n'
import { buildTrace, type RunEvent } from '@/lib/trace'
import { answers, type ChatSessionFull } from '@/lib/chat'

export type ChatView = 'builder' | 'visitor'
const POLL_MS = 250, POLL_TRIES = 40   // the answer is written by the worker just after the run ends

export function useChatRun(sid: string | null, view: ChatView, onSettled?: () => void) {
  const [session, setSession] = useState<ChatSessionFull | null>(null)
  const [events, setEvents] = useState<RunEvent[]>([]); const [pending, setPending] = useState<string | null>(null)
  const [running, setRunning] = useState(false); const [error, setError] = useState('')
  const ws = useRef<WebSocket | null>(null); const alive = useRef(true)
  const settled = useRef(onSettled); useEffect(() => { settled.current = onSettled })
  const load = useCallback((id = sid) => id ? api<ChatSessionFull>(`/api/chat/sessions/${id}?view=${view}`) : Promise.resolve(null), [sid, view])

  useOnChange(`${sid}|${view}`, () => { setEvents([]); setPending(null); setError('') })   // another chat or view: start clean
  useEffect(() => { alive.current = true
    load().then(s => alive.current && setSession(s)).catch(e => alive.current && setError(e.message))
    return () => { alive.current = false; ws.current?.close() } }, [load])

  /** Read the session again until the run's answer count grows (or give up and show what is there). */
  const settle = useCallback(async (id: string, runId: string | undefined, before: number) => {
    for (let i = 0; i < POLL_TRIES && alive.current; i++) {
      const s = await load(id).catch(() => null)
      if (s && (answers(s.turns, runId) > before || !runId || i === POLL_TRIES - 1)) { if (alive.current) { setSession(s); setEvents([]); setPending(null); settled.current?.() } return }
      await new Promise(r => setTimeout(r, POLL_MS))
    }
  }, [load])

  const stream = useCallback((msg: Record<string, unknown>, shown: string | null, before: number, resumeOf?: string) => {
    if (!sid) return
    setError(''); setEvents([]); setPending(shown); setRunning(true)
    const sock = new WebSocket(wsUrl('/ws/run')); ws.current = sock; let runId = resumeOf
    sock.onopen = () => sock.send(JSON.stringify({ chat_session_id: sid, ...msg, locale: uiLocale() }))
    sock.onmessage = m => { const ev: RunEvent = JSON.parse(m.data); if (ev.run_id) runId = ev.run_id
      if (ev.type === 'error' && !ev.node && !runId) setError(eventErrors(ev).join('; '))
      setEvents(l => [...l, ev]) }
    sock.onclose = () => { setRunning(false); if (runId) settle(sid, runId, resumeOf ? before : 0); else setPending(null) }
  }, [sid, settle])

  const send = useCallback((text: string) => stream({ message: text }, text, 0), [stream])
  const answer = (runId: string, response: string) => stream({ resume_run_id: runId, response }, response, answers(session?.turns ?? [], runId), runId)
  const cancel = () => ws.current?.readyState === WebSocket.OPEN && ws.current.send(JSON.stringify({ type: 'cancel' }))
  return { session, events, trace: buildTrace(events), pending, running, error, send, answer, cancel, reload: () => load().then(setSession) }
}
