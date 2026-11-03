import { describe, expect, it } from 'vitest'
import { createChatStore } from '../src/chat/index'
import { collect, ok, recorded, SID, Wire } from './chat-harness'

const BRANCH = 'edited-session'
const options = { operationId: 'intent-12345678', expectedLastTurnId: 'recorded-answer', recoveryIntervalMs: 0 }
function fixture(wire = new Wire(), action: 'edit' | 'regenerate' = 'edit') {
  wire.override = (url, init) => {
    if (url.pathname.endsWith('/' + SID)) return ok({ ...recorded.session, capabilities: { edit: true, regenerate: true } })
    if (url.pathname.endsWith(action === 'edit' ? '/edits' : '/regenerations')) return ok({ session: { ...recorded.session, id: BRANCH, source_session_id: SID, turns: [] },
      operation_id: options.operationId, run_id: 'recorded-run', message: 'Edited text', attachment_ids: [], state: wire.saved ? 'finished' : 'prepared' })
    if (url.pathname.endsWith('/' + BRANCH)) return ok({ ...recorded.session, id: BRANCH, source_session_id: SID, turns: wire.saved ? recorded.session.turns : [] })
  }
  return wire
}

describe.each(['edit', 'regenerate'] as const)('%s branch recovery', action => {
  const revise = (client: ReturnType<Wire['client']>) => action === 'edit' ? client.edit(SID, 'recorded-user', 'Edited text', options) : client.regenerate(SID, 'recorded-answer', options)
  const prepare = (client: ReturnType<Wire['client']>) => action === 'edit' ? client.prepareEdit(SID, 'recorded-user', 'Edited text', options) : client.prepareRegenerate(SID, 'recorded-answer', options)
  it('prepares an intent, switches the store and reads a repeated intent without another socket write', async () => {
    const wire = fixture(new Wire(), action), store = createChatStore(wire.client())
    await store.load(SID)
    const result = await (action === 'edit' ? store.edit('recorded-user', 'Edited text', options) : store.regenerate('recorded-answer', options))
    expect(result).toMatchObject({ sessionId: BRANCH, runId: 'recorded-run', status: 'ok' })
    expect(store.getSnapshot()).toMatchObject({ sessionId: BRANCH, sourceSessionId: SID })
    expect(store.getSnapshot().turns).toHaveLength(2)
    const frame = wire.sockets[0].sent.find(frame => frame.type === 'message')
    expect(frame).toMatchObject({ chat_session_id: BRANCH, edit_operation_id: options.operationId })
    const repeated = revise(wire.client())
    await collect(repeated)
    expect((await repeated.result).recovered).toBe(true)
    expect(wire.sockets).toHaveLength(1); expect(wire.writes).toBe(1)
    const body = JSON.parse(String(wire.calls.find(call => call.url.endsWith(action === 'edit' ? '/edits' : '/regenerations'))!.init.body))
    expect(body).toMatchObject({ operation_id: options.operationId, expected_last_turn_id: options.expectedLastTurnId })
    if (action === 'regenerate') expect(body).not.toHaveProperty('message')
  })

  it('refuses an older server before making an edit request', async () => {
    const wire = new Wire(), client = wire.client()
    await expect(prepare(client)).rejects.toMatchObject({ code: action === 'edit' ? 'CHAT_EDIT_UNSUPPORTED' : 'CHAT_REGENERATE_UNSUPPORTED' })
    expect(wire.calls.some(call => call.url.endsWith(action === 'edit' ? '/edits' : '/regenerations'))).toBe(false)
    expect(wire.writes).toBe(0)
  })

  it('recovers a lost admission response using the reserved run ID without replaying the frame', async () => {
    const wire = fixture(new Wire([(socket, _frame, wire) => { wire.saved = true; socket.close() }]), action)
    const stream = revise(wire.client())
    await collect(stream)
    expect(await stream.result).toMatchObject({ sessionId: BRANCH, runId: 'recorded-run', status: 'ok', recovered: true })
    expect(wire.writes).toBe(1)
  })
  it('reads an admitted intent even after the branch has later messages, preserving a later Human wait', async () => {
    const wire = fixture(new Wire(), action); wire.saved = true
    const base = wire.override!
    const rows = [...recorded.session.turns,
      { ...recorded.session.turns[0], id: 'later-root', run_id: 'later-run' },
      { ...recorded.session.turns[1], id: 'later-question', run_id: 'later-run', status: 'waiting' }]
    wire.override = (url, init) => {
      if (url.pathname.endsWith('/' + BRANCH)) return ok({ ...recorded.session, id: BRANCH, source_session_id: SID, turns: rows })
      if (url.pathname.endsWith('/turns')) {
        const i = rows.findIndex(turn => turn.id === url.searchParams.get('after'))
        return ok({ turns: rows.slice(i + 1) })
      }
      return base(url, init)
    }
    const store = createChatStore(wire.client()); await store.load(SID)
    const result = await (action === 'edit' ? store.edit('recorded-user', 'Edited text', options) : store.regenerate('recorded-answer', options))
    expect(result).toMatchObject({ runId: 'recorded-run', text: recorded.session.turns[1].text, recovered: true })
    expect(store.getSnapshot()).toMatchObject({ sessionId: BRANCH, status: 'waiting' })
    expect(store.getSnapshot().turns.at(-1)?.id).toBe('later-question')
    expect(wire.sockets).toHaveLength(0); expect(wire.writes).toBe(0)
  })

})
