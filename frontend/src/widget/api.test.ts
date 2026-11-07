import { afterEach, describe, expect, it, vi } from 'vitest'
import { createWidget, installWidget } from './widget'
import { createFrameBridge } from './frame-bridge'
import { MSG, storageKey, type WidgetAPI } from './protocol'
const STUDIO = 'https://studio.example', HOST = 'https://shop.example'
const JWT = 'header.payload.signature', VISITOR = '0123456789abcdef.0123456789abcdef0123456789abcdef'
const cleanups: (() => void)[] = []
afterEach(async () => { for (const cleanup of cleanups.splice(0)) cleanup(); await Promise.resolve(); document.body.replaceChildren(); localStorage.clear(); delete window.Superstep; vi.restoreAllMocks() })
const flush = async () => { for (let n = 0; n < 8; n++) await Promise.resolve() }
function host() {
  const widget = createWidget(window, STUDIO); cleanups.push(widget.dispose)
  widget.api.init({ slug: 'help' })
  const frame = [...document.querySelectorAll('iframe')].at(-1)!, post = vi.spyOn(frame.contentWindow!, 'postMessage').mockImplementation(() => {})
  const receive = (data: object, origin = STUDIO, source: MessageEventSource | null = frame.contentWindow) => window.dispatchEvent(new MessageEvent('message', { source, origin, data }))
  receive({ type: MSG.ready, v: 1, channel: 'document-1' })
  const reply = (data: object) => receive({ v: 1, channel: 'document-1', epoch: 0, ...data })
  return { ...widget, frame, post, receive, reply }
}
function iframe() {
  const node = document.createElement('iframe'); document.body.append(node)
  const win = node.contentWindow!, original = { q: [] }
  win.Superstep = original
  const post = vi.spyOn(win.parent, 'postMessage').mockImplementation(() => {})
  const bridge = createFrameBridge(win, 'help', true, () => [HOST])
  const stop = bridge.start(); cleanups.push(stop)
  const receive = (data: object, origin = HOST, source: MessageEventSource | null = win.parent) => win.dispatchEvent(new MessageEvent('message', { source, origin, data: { v: 1, channel: bridge.channel, epoch: 0, ...data } }))
  return { bridge, win, post, receive, stop, original }
}
describe('widget host API boundary', () => {
  it('rejects foreign windows/origins and stale documents; resolves identity only after history acknowledges', async () => {
    const h = host(), ready = vi.fn(); h.api.on('ready', ready)
    const pending = h.api.identify(JWT); await flush()
    expect(h.post).toHaveBeenLastCalledWith(expect.objectContaining({ type: MSG.identity, token: JWT, epoch: 1 }), STUDIO)
    expect(h.frame.src).not.toContain(JWT); expect(localStorage.length).toBe(0)
    let settled = false; void pending.then(() => { settled = true })
    h.receive({ type: MSG.ack, v: 1, channel: 'document-1', epoch: 1 }, HOST)
    h.receive({ type: MSG.ack, v: 1, channel: 'document-1', epoch: 1 }, STUDIO, window)
    h.receive({ type: MSG.ack, v: 1, channel: 'old', epoch: 1 }); await flush(); expect(settled).toBe(false)
    h.receive({ type: MSG.ack, v: 1, channel: 'document-1', epoch: 1 }); await pending
    h.receive({ type: MSG.event, v: 1, channel: 'document-1', epoch: 1, event: 'ready', data: { slug: 'fake', token: JWT, user: { email: 'private' } } })
    expect(ready).toHaveBeenCalledExactlyOnceWith({ slug: 'help' })
  })
  it('cancels a slow provider on logout and never overwrites the anonymous token with a JWT', async () => {
    localStorage.setItem(storageKey('help'), VISITOR)
    const h = host(); let resolve!: (token: string) => void
    const old = h.api.identify(() => new Promise<string>(r => { resolve = r })).catch(e => e)
    await flush(); const loggedOut = h.api.logout(); resolve(JWT); await flush()
    expect(await old).toMatchObject({ code: 'HTTP_ERROR' })
    expect(h.post.mock.calls.some(([data]) => data.token === JWT)).toBe(false)
    expect(h.post).toHaveBeenLastCalledWith(expect.objectContaining({ epoch: 2, type: MSG.identity, visitor: VISITOR }), STUDIO)
    h.receive({ type: MSG.save, v: 1, channel: 'document-1', epoch: 2, token: JWT })
    expect(localStorage.getItem(storageKey('help'))).toBe(VISITOR)
    h.receive({ type: MSG.ack, v: 1, channel: 'document-1', epoch: 2 }); await loggedOut
  })
  it('refreshes a provider per request and supports queue, unsubscribe, theme and locale without remounting', async () => {
    const event = vi.fn(), script = document.createElement('script'); script.src = `${STUDIO}/c/widget.js`
    window.Superstep = { q: [['init', { slug: 'help', language: 'vi', color: 'red', position: 'left' }], ['on', 'open', event], ['open']] }
    const api = installWidget(window, script), frame = document.querySelector('iframe')!, before = frame.contentWindow
    expect(event).toHaveBeenCalledTimes(1); api.off('open', event); api.close(); api.open(); expect(event).toHaveBeenCalledTimes(1)
    expect(document.querySelector('button')?.getAttribute('aria-label')).toBe('Đóng chat')
    expect(document.querySelector('#superstep-chat-widget')?.getAttribute('data-position')).toBe('left')
    api.init({ slug: 'help', color: '', logo: '' }); expect(frame.contentWindow).toBe(before)
    expect(installWidget(window, script)).toBe(api)
    // Dispose this install through identity-free DOM cleanup; no pending request remains.
    const h = host(), provider = vi.fn(async () => JWT), pending = h.api.identify(provider); await flush()
    h.receive({ type: MSG.request, v: 1, channel: 'document-1', epoch: 1, id: 'refresh-1' }); await flush()
    expect(provider).toHaveBeenCalledTimes(2)
    expect(h.post).toHaveBeenLastCalledWith(expect.objectContaining({ type: MSG.response, id: 'refresh-1', token: JWT }), STUDIO)
    h.receive({ type: MSG.ack, v: 1, channel: 'document-1', epoch: 1 }); await pending
  })
})
describe('iframe identity boundary', () => {
  it('ignores a foreign parent origin/window, validates document nonce, and clears old identity before a provider resolves', async () => {
    const f = iframe()
    f.receive({ type: MSG.identity, token: JWT, epoch: 1 }, 'https://evil.example')
    f.receive({ type: MSG.identity, token: JWT, epoch: 1 }, HOST, f.win)
    f.receive({ type: MSG.identity, token: JWT, epoch: 1, channel: 'stale' })
    expect(f.bridge.getSnapshot().kind).toBe('pending')
    f.receive({ type: MSG.identity, token: JWT, epoch: 1 }); expect(f.bridge.getSnapshot().kind).toBe('app')
    expect(JSON.stringify(f.bridge.getSnapshot())).not.toContain(JWT)
    const token = f.bridge.getToken(1); const request = f.post.mock.calls.at(-1)![0]
    expect(f.post).toHaveBeenLastCalledWith(expect.objectContaining({ type: MSG.request, epoch: 1 }), HOST)
    f.receive({ type: MSG.response, id: request.id, token: JWT, epoch: 1 }); expect(await token).toBe(JWT)
    const stale = f.bridge.getToken(1).catch(e => e)
    f.receive({ type: MSG.configure, epoch: 2, options: { language: 'vi' } })
    expect(f.bridge.getSnapshot()).toMatchObject({ kind: 'pending', epoch: 2, options: { language: 'vi' } })
    expect(await stale).toMatchObject({ code: 'HTTP_ERROR' })
    f.receive({ type: MSG.identity, epoch: 2, visitor: VISITOR }); expect(f.bridge.getSnapshot().kind).toBe('guest')
    f.bridge.keep(JWT); expect(f.post.mock.calls.some(([d]) => d.type === MSG.save)).toBe(false)
    f.bridge.keep(VISITOR); expect(f.post).toHaveBeenLastCalledWith(expect.objectContaining({ type: MSG.save, token: VISITOR }), HOST)
  })
  it('survives StrictMode replay and exposes a memory-only native API with history acknowledgements', async () => {
    const f = iframe(); f.stop(); const stop = f.bridge.start(); cleanups.push(stop); await flush()
    expect(f.win.Superstep).toBe(f.bridge.api)
    const api = f.win.Superstep as WidgetAPI, ready = vi.fn(); api.on('ready', ready)
    const pending = api.identify(() => JWT), epoch = f.bridge.getSnapshot().epoch
    expect(await f.bridge.getToken(epoch)).toBe(JWT)
    f.bridge.complete(epoch); await pending; expect(ready).toHaveBeenCalledTimes(1)
    const logout = api.logout(); f.bridge.complete(epoch + 1); await logout
    expect(f.bridge.getSnapshot().kind).toBe('guest'); expect(f.win.localStorage.length).toBe(0)
    stop(); await flush(); expect(f.win.Superstep).toBe(f.original)
  })
})
describe('native WebView bridge (TASK-0228)', () => {
  const JWT2 = 'header.payload.fresh'
  function native(kind: 'ios' | 'android' | 'rn') {
    const sent: Record<string, unknown>[] = [], postMessage = (message: string) => { sent.push(JSON.parse(message)) }
    const w = window as unknown as Record<string, unknown>
    if (kind === 'ios') w.webkit = { messageHandlers: { superstep: { postMessage } } }
    else if (kind === 'android') w.superstep = { postMessage }
    else w.ReactNativeWebView = { postMessage }
    cleanups.push(() => { delete w.webkit; delete w.superstep; delete w.ReactNativeWebView })
    const bridge = createFrameBridge(window, 'help', false, () => [HOST]); cleanups.push(bridge.start())
    return { bridge, sent }
  }
  it.each(['ios', 'android', 'rn'] as const)('announces to the %s host and asks it for a fresh token after the first one is used', async kind => {
    const { bridge, sent } = native(kind)
    expect(bridge.native).toBe(true)
    bridge.announce(); expect(sent).toEqual([{ v: 1, type: MSG.ready, slug: 'help' }])
    void (window.Superstep as WidgetAPI).identify(JWT).catch(() => {})
    const epoch = bridge.getSnapshot().epoch; expect(bridge.getSnapshot().kind).toBe('app')
    expect(await bridge.getToken(epoch)).toBe(JWT)
    const next = bridge.getToken(epoch), again = bridge.getToken(epoch); await flush()
    expect(sent.filter(m => m.type === MSG.request)).toHaveLength(1)
    expect(sent.at(-1)).toMatchObject({ v: 1, type: MSG.request, slug: 'help' }); expect(JSON.stringify(sent)).not.toContain(JWT)
    await (window.Superstep as WidgetAPI).identify(JWT2)
    expect(await next).toBe(JWT2); expect(await again).toBe(JWT2); expect(bridge.getSnapshot().epoch).toBe(epoch)
  })
  it('stays a plain page without a native channel or inside a frame, and refuses a bad token', async () => {
    const plain = createFrameBridge(window, 'help', false, () => [HOST]); cleanups.push(plain.start())
    expect(plain.native).toBe(false)
    await expect((window.Superstep as WidgetAPI).identify('not a token')).rejects.toMatchObject({ code: 'CHAT_TOKEN_INVALID' })
    const node = document.createElement('iframe'); document.body.append(node)
    ;(node.contentWindow as unknown as Record<string, unknown>).ReactNativeWebView = { postMessage: () => {} }
    expect(createFrameBridge(node.contentWindow!, 'help', false, () => [HOST]).native).toBe(false)
  })
  it('times out when the app never answers', async () => {
    vi.useFakeTimers(); cleanups.push(() => vi.useRealTimers())
    const { bridge } = native('rn')
    void (window.Superstep as WidgetAPI).identify(JWT).catch(() => {})
    const epoch = bridge.getSnapshot().epoch; await bridge.getToken(epoch)
    const next = bridge.getToken(epoch).catch(e => e); await vi.advanceTimersByTimeAsync(10001)
    expect(await next).toMatchObject({ code: 'HTTP_ERROR' })
  })
})
