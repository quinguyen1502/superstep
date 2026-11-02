import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APIConnectionError, AuthenticationError, ConfigError, PermissionDeniedError, Superstep } from '../src/index'
import { ChatClient } from '../src/chat/index'
import { Wire, SID, collect, recorded, failure, holding, ok } from './chat-harness'

export function chatContract(runtime: 'node' | 'dom' | 'native') {
  describe(`v1 chat contract: ${runtime}`, () => {
    beforeEach(() => {
      if (runtime === 'native') for (const name of ['window', 'document', 'Blob', 'File', 'FormData', 'Buffer']) vi.stubGlobal(name, undefined)
    })
    afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

    it('replays recorded backend frames, yields a final result and reads persisted history', async () => {
      const wire = new Wire(), stream = wire.client().send(SID, 'Hello', { recoveryIntervalMs: 0 })
      const events = await collect(stream), result = await stream.result
      expect(events.filter(event => 'v' in event).map(event => event.type)).toEqual(recorded.frames.map((event: any) => event.type))
      expect(events[events.length - 1]).toMatchObject({ type: 'result', result: { status: 'ok', turnId: 'recorded-answer', recovered: false } })
      expect(result.text).toBe(recorded.session.turns[1].text)
      expect(wire.writes).toBe(1); expect(wire.sockets[0].listenerCount()).toBe(0)
      expect(wire.sockets[0].sent[0]).toEqual({ type: 'auth', visitor: 'fixture-visitor-token' })
    })

    it('ignores additive events and duplicate sequence numbers', async () => {
      const wire = new Wire([(socket, _frame, wire) => {
        wire.saved = true
        socket.frame({ type: 'future_capability', v: 1, seq: 0, extra: true })
        for (const frame of recorded.frames.slice(1)) { socket.frame(frame); socket.frame(frame) }
      }])
      const stream = wire.client().send(SID, 'Hello', { recoveryIntervalMs: 0 }), events = await collect(stream)
      expect(events.filter(event => event.type === 'token')).toHaveLength(recorded.frames.filter((event: any) => event.type === 'token').length)
      expect((await stream.result).text).toBe(recorded.session.turns[1].text)
    })

    it('refreshes an expired HTTP token once and never uses the workflow token for chat', async () => {
      const wire = new Wire(); let calls = 0
      wire.override = () => ++calls === 1 ? failure('CHAT_TOKEN_EXPIRED') : undefined
      const getToken = vi.fn(() => 'short-lived-token')
      const client = new Superstep({ baseUrl: 'https://superstep.test', workflowId: 'wf', token: 'wft-private', fetch: wire.fetch })
      await client.chat('sdk-fixture', { getToken }).info()
      expect(getToken).toHaveBeenCalledTimes(2)
      for (const request of wire.calls) {
        expect(request.init.headers).toMatchObject({ Authorization: 'Bearer short-lived-token' })
        expect(JSON.stringify(request)).not.toContain('wft-private')
      }
      const chatOnly = new Superstep({ baseUrl: 'https://superstep.test', fetch: wire.fetch })
      expect(() => chatOnly.run()).toThrow(ConfigError)
    })

    it('does not refresh a revoked or origin-forbidden token', async () => {
      for (const [code, status, ErrorClass] of [['CHAT_APP_KEY_REVOKED', 401, AuthenticationError], ['CHAT_ORIGIN_FORBIDDEN', 403, PermissionDeniedError]] as const) {
        const wire = new Wire(); wire.override = () => failure(code, status)
        const token = vi.fn(() => 'short-token')
        await expect(wire.client({ getToken: token, visitorToken: undefined }).info()).rejects.toBeInstanceOf(ErrorClass)
        expect(token).toHaveBeenCalledTimes(1)
      }
    })

    it('bounds repeated HTTP expiry to one refresh', async () => {
      const wire = new Wire(); wire.override = () => failure('CHAT_TOKEN_EXPIRED')
      const token = vi.fn(() => 'expired-token')
      await expect(wire.client({ getToken: token, visitorToken: undefined }).start()).rejects.toMatchObject({ code: 'CHAT_TOKEN_EXPIRED' })
      expect(wire.calls).toHaveLength(2); expect(token).toHaveBeenCalledTimes(2)
    })

    it('preserves the host abort reason while consuming a response body', async () => {
      const wire = new Wire(), abort = new AbortController(), reason = new Error('host stopped body read')
      wire.override = () => ({ ok: true, status: 200, json: async () => { abort.abort(reason); throw reason } }) as unknown as Response
      await expect(wire.client().info({ signal: abort.signal })).rejects.toBe(reason)
      expect(wire.calls).toHaveLength(1)
    })

    it('binds the default platform fetch receiver for browser Web IDL implementations', async () => {
      const wire = new Wire()
      vi.stubGlobal('fetch', function (this: unknown, ...args: Parameters<typeof fetch>) {
        expect(this).toBe(globalThis)
        return wire.fetch(...args)
      })
      await new Superstep({ baseUrl: 'https://superstep.test' }).chat('sdk-fixture', { visitorToken: 'fixture-visitor' }).info()
      await new ChatClient('sdk-fixture', { baseUrl: 'https://superstep.test', visitorToken: 'fixture-visitor' }).info()
      await new Superstep({ baseUrl: 'https://superstep.test', fetch: globalThis.fetch }).chat('sdk-fixture', { visitorToken: 'fixture-visitor' }).info()
      await new ChatClient('sdk-fixture', { baseUrl: 'https://superstep.test', fetch: globalThis.fetch, visitorToken: 'fixture-visitor' }).info()
      wire.override = () => ok({ run_id: 'fixture-run', status: 'ok' })
      await expect(new Superstep({ baseUrl: 'https://superstep.test', workflowId: 'wf', token: 'wft-private' }).run()).resolves.toMatchObject({ run_id: 'fixture-run' })
    })

    it('retries only explicit socket auth expiry before a run starts; tokens never enter URLs', async () => {
      const wire = new Wire([socket => socket.frame({ type: 'error', v: 1, seq: 1, error: { code: 'CHAT_TOKEN_EXPIRED', message: 'expired' } })])
      const token = vi.fn(() => 'app-short-token')
      const stream = wire.client({ getToken: token, visitorToken: undefined }).send(SID, 'Hello', { recoveryIntervalMs: 0 })
      await collect(stream)
      expect((await stream.result).status).toBe('ok'); expect(wire.sockets).toHaveLength(2)
      for (const socket of wire.sockets) { expect(socket.url).toBe('wss://superstep.test/ws/public/v1/chat/sdk-fixture'); expect(socket.sent[0]).toEqual({ type: 'auth', token: 'app-short-token' }) }
    })

    it('does not resend after a run has started, even if an expiry frame is received', async () => {
      const wire = new Wire([socket => {
        holding(socket, {} as never, {} as never)
        socket.frame({ type: 'error', v: 1, seq: 2, error: { code: 'CHAT_TOKEN_EXPIRED', message: 'expired' } })
      }])
      const stream = wire.client({ getToken: () => 'token', visitorToken: undefined }).send(SID, 'Hello')
      await expect(collect(stream)).rejects.toMatchObject({ code: 'CHAT_TOKEN_EXPIRED' })
      expect(wire.writes).toBe(1)
    })

    it('recovers a dropped socket through turns?after without another write', async () => {
      const wire = new Wire([(socket, _request, wire) => { wire.saved = true; holding(socket, _request, wire); socket.close() }])
      const stream = wire.client().send(SID, 'Hello', { after: 'last-seen', recoveryIntervalMs: 0 })
      const events = await collect(stream)
      expect((await stream.result)).toMatchObject({ status: 'ok', recovered: true, turnId: 'recorded-answer' })
      expect(events.some(event => event.type === 'history')).toBe(true)
      expect(wire.calls.some(call => call.url.endsWith('/turns?after=last-seen'))).toBe(true)
      expect(wire.writes).toBe(1); expect(wire.sockets).toHaveLength(1)
    })

    it('a missing result stays interrupted without blind replay', async () => {
      const wire = new Wire([(socket, request, wire) => { holding(socket, request, wire); socket.close() }])
      const stream = wire.client().send(SID, 'Hello', { recoveryAttempts: 2, recoveryIntervalMs: 0 })
      await expect(collect(stream)).rejects.toBeInstanceOf(APIConnectionError)
      await expect(stream.result).rejects.toMatchObject({ code: 'CHAT_STREAM_INTERRUPTED' })
      expect(wire.writes).toBe(1)
    })

    it('a lost run_started frame does not falsely confirm a later history entry', async () => {
      const wire = new Wire([(socket, _request, wire) => { wire.saved = true; socket.close() }])
      const stream = wire.client().send(SID, 'Hello', { recoveryIntervalMs: 0 })
      await expect(collect(stream)).rejects.toMatchObject({ code: 'CHAT_STREAM_INTERRUPTED' })
      expect(wire.writes).toBe(1)
    })

    it('answers a Human form with the actual node field and preserves question metadata', async () => {
      const wire = new Wire([(socket, _request, wire) => {
        wire.saved = true; wire.status = 'waiting'
        socket.frame({ type: 'run_started', v: 1, seq: 1, run_id: 'recorded-run' })
        socket.frame({ type: 'question', v: 1, seq: 2, node: 'approve', kind: 'form', fields: [{ name: 'ok', type: 'boolean' }] })
        socket.frame({ type: 'done', v: 1, seq: 3, status: 'waiting', run_id: 'recorded-run' })
      }])
      const client = wire.client(), first = client.send(SID, 'Question', { recoveryIntervalMs: 0 })
      await collect(first); expect((await first.result).question).toMatchObject({ node: 'approve', kind: 'form' })
      wire.saved = false; wire.status = 'ok'
      const answer = client.answer(SID, { ok: true }, { node: 'approve', recoveryIntervalMs: 0 })
      await collect(answer)
      expect(wire.sockets[1].sent[1]).toMatchObject({ type: 'answer', node: 'approve', response: { ok: true } })
    })

    it('cancel sends the cancellation frame and cleans socket listeners', async () => {
      const wire = new Wire([holding]), client = wire.client(), stream = client.send(SID, 'Hold', { recoveryIntervalMs: 0 })
      for await (const event of stream) if (event.type === 'run_started') client.cancel(SID)
      expect((await stream.result).status).toBe('cancelled'); expect(wire.cancels).toBe(1)
      expect(wire.sockets[0].listenerCount()).toBe(0)
    })

    it('abort stops a stream and does not reconnect', async () => {
      const wire = new Wire([holding]), abort = new AbortController(), stream = wire.client().send(SID, 'Hold', { signal: abort.signal })
      await expect((async () => { for await (const event of stream) if (event.type === 'run_started') abort.abort(new Error('host abort')) })()).rejects.toThrow('host abort')
      expect(wire.writes).toBe(1); expect(wire.sockets[0].listenerCount()).toBe(0)
    })

    it('rejects invalid protocol frames without replaying', async () => {
      const wire = new Wire([socket => socket.frame({ type: 'token', v: 2, seq: 1, delta: 'bad' })])
      const stream = wire.client().send(SID, 'Hello')
      await expect(collect(stream)).rejects.toMatchObject({ code: 'BAD_RESPONSE' }); expect(wire.writes).toBe(1)
    })

    it('bootstraps one anonymous identity for concurrent initial calls', async () => {
      const wire = new Wire(), changed = vi.fn(), client = wire.client({ visitorToken: undefined, onVisitorToken: changed })
      await Promise.all([client.start(), client.list()])
      expect(wire.calls.filter(call => (call.init.headers as any)['X-Chat-Visitor'] === 'new')).toHaveLength(1)
      expect(client.visitorToken).toBe('fixture-visitor-token'); expect(changed).toHaveBeenCalledOnce()
    })

    it('uploads bytes, downloads content, deletes an unsent file and manages ratings', async () => {
      const wire = new Wire(), client = wire.client()
      const file = await client.attachments.upload(SID, new Uint8Array([97, 98, 99]), { name: 'file.txt', type: 'text/plain' })
      expect(file.id).toBe('file-fixture')
      const upload = wire.calls.find(call => call.init.method === 'POST')!
      expect((upload.init.headers as any)['Content-Type']).toBeUndefined()
      expect((upload.init.body as FormData).get('file')).toMatchObject({ name: 'file.txt', size: 3 })
      expect(await (await client.attachments.download(SID, file.id)).text()).toBe('abc')
      expect(await client.attachments.delete(SID, file.id)).toEqual({ ok: true })
      expect(await client.ratings.put(SID, 'recorded-answer', 'down', { comment: 'Needs context' })).toMatchObject({ value: 'down', comment: 'Needs context' })
      expect(await client.ratings.delete(SID, 'recorded-answer')).toEqual({ ok: true })
    })

    it('passes native URI descriptors to native FormData without reading their URI', async () => {
      class NativeForm { values: unknown[] = []; append(...args: unknown[]) { this.values.push(args) } }
      const wire = new Wire(), client = wire.client({ FormData: NativeForm as unknown as typeof FormData })
      const file = { uri: 'content://local/receipt', name: 'receipt.txt', type: 'text/plain' }
      await client.attachments.upload(SID, file)
      expect((wire.calls[0].init.body as unknown as NativeForm).values).toEqual([['file', file]])
      expect(wire.calls).toHaveLength(1)
    })

    it('refuses URLs with credentials or query, mixed identities and traversal resource IDs', () => {
      for (const baseUrl of ['https://secret@superstep.test', 'https://superstep.test?token=secret', 'file:///tmp/api']) {
        expect(() => new ChatClient('sdk-fixture', { baseUrl })).toThrow(ConfigError)
      }
      const wire = new Wire()
      expect(() => wire.client({ getToken: () => 'token' })).toThrow(ConfigError)
      expect(() => wire.client().send('..', 'Hello')).toThrow(ConfigError)
    })
  })
}
