import { describe, expect, it } from 'vitest'
import { createChatStore } from '../src/chat/index'
import { collect, ok, recorded, SID, Wire } from './chat-harness'

const BRANCH = 'edited-session'
const options = { operationId: 'intent-12345678', expectedLastTurnId: 'recorded-answer', recoveryIntervalMs: 0 }
function fixture(wire = new Wire()) {
  wire.override = (url, init) => {
    if (url.pathname.endsWith('/' + SID)) return ok({ ...recorded.session, capabilities: { edit: true } })
    if (url.pathname.endsWith('/edits')) return ok({ session: { ...recorded.session, id: BRANCH, source_session_id: SID, turns: [] },
      operation_id: options.operationId, run_id: 'recorded-run', message: 'Edited text', attachment_ids: [], state: wire.saved ? 'finished' : 'prepared' })
    if (url.pathname.endsWith('/' + BRANCH)) return ok({ ...recorded.session, id: BRANCH, source_session_id: SID, turns: wire.saved ? recorded.session.turns : [] })
  }
  return wire
}

describe('chat editing and branch recovery', () => {
  it('prepares an intent, switches the store and reads a repeated intent without another socket write', async () => {
    const wire = fixture(), store = createChatStore(wire.client())
    await store.load(SID)
    const result = await store.edit('recorded-user', 'Edited text', options)
    expect(result).toMatchObject({ sessionId: BRANCH, runId: 'recorded-run', status: 'ok' })
    expect(store.getSnapshot()).toMatchObject({ sessionId: BRANCH, sourceSessionId: SID })
    expect(store.getSnapshot().turns).toHaveLength(2)
    const frame = wire.sockets[0].sent.find(frame => frame.type === 'message')
    expect(frame).toMatchObject({ chat_session_id: BRANCH, edit_operation_id: options.operationId })
    const repeated = wire.client().edit(SID, 'recorded-user', 'Edited text', options)
    await collect(repeated)
    expect((await repeated.result).recovered).toBe(true)
    expect(wire.sockets).toHaveLength(1); expect(wire.writes).toBe(1)
    const body = JSON.parse(String(wire.calls.find(call => call.url.endsWith('/edits'))!.init.body))
    expect(body).toMatchObject({ operation_id: options.operationId, expected_last_turn_id: options.expectedLastTurnId })
  })

  it('refuses an older server before making an edit request', async () => {
    const wire = new Wire(), client = wire.client()
    await expect(client.prepareEdit(SID, 'recorded-user', 'Edited text', options)).rejects.toMatchObject({ code: 'CHAT_EDIT_UNSUPPORTED' })
    expect(wire.calls.some(call => call.url.endsWith('/edits'))).toBe(false)
    expect(wire.writes).toBe(0)
  })

  it('recovers a lost admission response using the reserved run ID without replaying the frame', async () => {
    const wire = fixture(new Wire([(socket, _frame, wire) => { wire.saved = true; socket.close() }]))
    const stream = wire.client().edit(SID, 'recorded-user', 'Edited text', options)
    await collect(stream)
    expect(await stream.result).toMatchObject({ sessionId: BRANCH, runId: 'recorded-run', status: 'ok', recovered: true })
    expect(wire.writes).toBe(1)
  })
})
