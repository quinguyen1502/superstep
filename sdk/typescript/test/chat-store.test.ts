import { describe, expect, it, vi } from 'vitest'
import { createChatStore } from '../src/chat/index'
import { collect, holding, ok, recorded, SID, Wire } from './chat-harness'

describe('headless chat store', () => {
  it('keeps stable snapshots, merges history and unsubscribes', async () => {
    const wire = new Wire(), store = createChatStore(wire.client()), changed = vi.fn()
    const first = store.getSnapshot(), unsubscribe = store.subscribe(changed)
    expect(store.getSnapshot()).toBe(first)
    const result = await store.send('Hello', { recoveryIntervalMs: 0 })
    expect(store.getSnapshot()).toMatchObject({ sessionId: SID, status: 'idle', text: result.text, turns: recorded.session.turns })
    expect(Object.isFrozen(store.getSnapshot())).toBe(true)
    expect(changed).toHaveBeenCalled()
    unsubscribe(); changed.mockClear(); await store.load(SID)
    expect(changed).not.toHaveBeenCalled(); expect(store.getSnapshot().turns).toHaveLength(2)
    store.dispose(); expect(() => store.subscribe(() => {})).toThrow('disposed')
    await expect(store.send('No')).rejects.toMatchObject({ code: 'CHAT_STORE_DISPOSED' })
  })
  it('allows cancellation while preventing overlapping sends', async () => {
    const wire = new Wire([holding]), store = createChatStore(wire.client())
    await store.load(SID)
    const pending = store.send('Hold', { recoveryIntervalMs: 0 })
    await vi.waitFor(() => expect(wire.writes).toBe(1))
    await expect(store.send('Second')).rejects.toMatchObject({ code: 'CHAT_BUSY' })
    store.cancel(); expect((await pending).status).toBe('cancelled')
    expect(store.getSnapshot()).toMatchObject({ status: 'idle', error: null })
  })
  it('disposal aborts the local stream and releases listeners', async () => {
    const wire = new Wire([holding]), store = createChatStore(wire.client())
    await store.load(SID); const pending = store.send('Hold')
    await vi.waitFor(() => expect(wire.writes).toBe(1))
    store.dispose(); await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    expect(wire.sockets[0].listenerCount()).toBe(0); expect(wire.cancels).toBe(1)
  })
  it('does not send into another session when an implicit start resolves late', async () => {
    const wire = new Wire(); let finish!: (value: Response) => void
    wire.override = (_url, init) => init.method === 'POST' ? new Promise(resolve => { finish = resolve }) : undefined
    const store = createChatStore(wire.client()), pending = store.send('Stale')
    await vi.waitFor(() => expect(finish).toBeTypeOf('function'))
    await store.load(SID); finish(ok(recorded.session))
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    expect(wire.writes).toBe(0); expect(store.getSnapshot()).toMatchObject({ sessionId: SID, status: 'idle' })
  })
  it('ignores stale loads and exposes current failures', async () => {
    const wire = new Wire(); let finish!: (value: Response) => void
    wire.override = url => url.pathname.endsWith('/old-session') ? new Promise(resolve => { finish = resolve }) : undefined
    const store = createChatStore(wire.client()), old = store.load('old-session')
    await vi.waitFor(() => expect(finish).toBeTypeOf('function'))
    await store.load(SID); finish(ok({ ...recorded.session, id: 'old-session' })); await old
    expect(store.getSnapshot().sessionId).toBe(SID)
    wire.override = () => { throw new Error('offline') }
    await expect(store.load(SID)).rejects.toMatchObject({ code: 'CONNECTION_ERROR' })
    expect(store.getSnapshot()).toMatchObject({ status: 'error', error: { code: 'CONNECTION_ERROR' } })
  })
})

describe('stream lifecycle', () => {
  it('times out and cancels without reconnecting', async () => {
    const wire = new Wire([holding]), stream = wire.client().send(SID, 'Hold', { timeoutMs: 10 })
    await expect(collect(stream)).rejects.toMatchObject({ code: 'CHAT_STREAM_TIMEOUT' })
    expect(wire.writes).toBe(1); expect(wire.cancels).toBe(1); expect(wire.sockets[0].listenerCount()).toBe(0)
  })
  it('a pre-aborted operation never sends or opens a socket', async () => {
    const wire = new Wire(), abort = new AbortController(); abort.abort()
    const stream = wire.client().send(SID, 'No', { signal: abort.signal })
    await expect(collect(stream)).rejects.toMatchObject({ name: 'AbortError' })
    expect(wire.calls).toHaveLength(0); expect(wire.sockets).toHaveLength(0)
  })
  it('breaking iteration releases the socket and bounds an undrained stream', async () => {
    const wire = new Wire([holding]), stream = wire.client().send(SID, 'Hold')
    for await (const event of stream) if (event.type === 'run_started') break
    await expect(stream.result).rejects.toMatchObject({ name: 'AbortError' }); expect(wire.sockets[0].listenerCount()).toBe(0)
    const noisy = new Wire([socket => { for (let seq = 1; seq < 1100; seq++) socket.frame({ type: 'token', v: 1, seq, delta: 'x' }) }])
    const undrained = noisy.client().send(SID, 'No consumer')
    await expect(undrained.result).rejects.toMatchObject({ code: 'CHAT_BUFFER_FULL' })
    expect(noisy.sockets[0].listenerCount()).toBe(0)
  })
})
