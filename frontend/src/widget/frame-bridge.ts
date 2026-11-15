/** One iframe identity boundary. Strict origin + WindowProxy + document nonce + identity epoch checks. */
import { MSG, appearance, bridgeError, channelId, epochId, errorCode, eventHub, failureCode, resolveToken, storageKey, userToken, visitorToken,
  type Appearance, type Command, type TokenProvider, type WidgetAPI, type WidgetEvent, type WidgetPayload } from './protocol'
export type FrameState = { epoch: number; kind: 'pending' | 'guest' | 'app' | 'error'; options: Appearance; visitor?: string; code?: string }
const WAIT = 10000
/** Native host channels: iOS WKScriptMessageHandler, Android WebMessageListener, React Native WebView. Top-level page only. */
export type NativeHost = (message: string) => void
export function nativeHost(win: Window): NativeHost | null {
  if (win.parent !== win) return null
  const w = win as unknown as { webkit?: { messageHandlers?: { superstep?: { postMessage?: unknown } } }; superstep?: { postMessage?: unknown }; ReactNativeWebView?: { postMessage?: unknown } }
  for (const target of [w.webkit?.messageHandlers?.superstep, w.superstep, w.ReactNativeWebView]) {
    if (target && typeof target.postMessage === 'function') { const send = target.postMessage as (message: string) => void; return message => { try { send.call(target, message) } catch { /* host went away */ } } }
  }
  return null
}
export function createFrameBridge(win: Window, slug: string, widget: boolean, allowed: () => readonly string[]) {
  const channel = [...win.crypto.getRandomValues(new Uint32Array(4))].join('-'), hub = eventHub(), listeners = new Set<() => void>()
  let host = '', localProvider: TokenProvider | undefined, saved: string | null = null, sequence = 0, completed = -1, active = false, replayed = false
  try { const value = win.localStorage.getItem(storageKey(slug)); if (visitorToken(value)) saved = value } catch { /* blocked storage */ }
  let state: FrameState = { epoch: 0, kind: widget ? 'pending' : 'guest', visitor: saved ?? 'new', options: {} }
  let fallback: ReturnType<typeof setTimeout> | undefined, previous: Window['Superstep'], opened = true
  // A native app answers a token request by calling Superstep.identify(token) again; that call refreshes, it does not switch identity.
  const native = widget ? null : nativeHost(win)
  // Concurrent token reads share one request to the app; one identify(token) answers all of them.
  let issued = false, nativeWait: { waiters: { resolve: (value: string) => void; reject: (error: Error) => void }[]; timer: ReturnType<typeof setTimeout> } | null = null
  const dropNative = () => { const wait = nativeWait; nativeWait = null; if (wait) { clearTimeout(wait.timer); for (const w of wait.waiters) w.reject(bridgeError()) } }
  const requests = new Map<string, { resolve: (value: string) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>()
  const acknowledgements = new Map<number, { resolve: () => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>()
  const publish = (next: FrameState) => { state = next; for (const listener of [...listeners]) listener() }
  const post = (data: object) => { if (host && win.parent !== win) win.parent.postMessage({ v: 1, channel, epoch: state.epoch, ...data }, host) }
  const emit = (event: WidgetEvent, data: WidgetPayload = { slug }) => { hub.emit(event, data); post({ type: MSG.event, event, data }) }
  const rejectRequests = () => { dropNative(); for (const r of requests.values()) { clearTimeout(r.timer); r.reject(bridgeError()) } requests.clear() }
  const finish = (epoch: number, code?: string) => {
    if (epoch !== state.epoch || completed === epoch) return
    completed = epoch; post({ type: MSG.ack, ...(code ? { error: errorCode(code) } : {}) })
    const wait = acknowledgements.get(epoch); if (wait) { clearTimeout(wait.timer); acknowledgements.delete(epoch); if (code) wait.reject(bridgeError(errorCode(code))); else wait.resolve() }
    emit(code ? 'error' : 'ready', code ? { slug, code: errorCode(code) } : { slug })
  }
  const change = (next: FrameState) => { rejectRequests(); completed = -1; clearTimeout(fallback); publish(next) }
  const listen = (event: MessageEvent) => {
    if (win.parent === win || event.source !== win.parent || !allowed().includes(event.origin) || (host && event.origin !== host) || !event.data || typeof event.data !== 'object') return
    const d = event.data
    // Old widget.js only carries a visitor token; it must never establish app identity.
    if (d.type === MSG.token && state.kind === 'pending' && d.v === undefined) {
      host = event.origin; change({ ...state, kind: 'guest', visitor: visitorToken(d.token) ? d.token : 'new' }); return
    }
    if (d.v !== 1 || d.channel !== channel || !epochId(d.epoch) || d.epoch < state.epoch) return
    if (![MSG.configure, MSG.identity, MSG.response].includes(d.type)) return
    host = event.origin
    if (d.type === MSG.configure) { const options = { ...state.options, ...appearance(d.options, win.document) }; if (d.epoch > state.epoch) change({ epoch: d.epoch, kind: 'pending', options }); else publish({ ...state, options }); return }
    if (d.type === MSG.response) {
      if (d.epoch !== state.epoch || !channelId(d.id)) return
      const r = requests.get(d.id); if (!r) return
      clearTimeout(r.timer); requests.delete(d.id)
      if (userToken(d.token)) r.resolve(d.token); else r.reject(bridgeError(d.error ? errorCode(d.error) : 'CHAT_TOKEN_INVALID'))
      return
    }
    if (d.epoch === state.epoch && state.kind === 'app' && d.pending) return
    localProvider = undefined
    if (d.error) { change({ epoch: d.epoch, kind: 'error', options: state.options, code: errorCode(d.error) }); finish(d.epoch, errorCode(d.error)) }
    else if (d.pending) change({ epoch: d.epoch, kind: 'pending', options: state.options })
    else if (userToken(d.token)) change({ epoch: d.epoch, kind: 'app', options: state.options })
    else if (d.token !== undefined) { change({ epoch: d.epoch, kind: 'error', options: state.options, code: 'CHAT_TOKEN_INVALID' }); finish(d.epoch, 'CHAT_TOKEN_INVALID') }
    else { const value = visitorToken(d.visitor) ? d.visitor : saved ?? 'new'; change({ epoch: d.epoch, kind: 'guest', options: state.options, visitor: value }) }
  }
  const identify = (provider?: TokenProvider) => {
    if (provider !== undefined && typeof provider !== 'function' && !userToken(provider)) return Promise.reject(bridgeError('CHAT_TOKEN_INVALID'))
    if (nativeWait && typeof provider === 'string') { const wait = nativeWait; nativeWait = null; clearTimeout(wait.timer); localProvider = provider; for (const w of wait.waiters) w.resolve(provider); return Promise.resolve() }
    issued = false
    for (const w of acknowledgements.values()) { clearTimeout(w.timer); w.reject(bridgeError()) } acknowledgements.clear()
    localProvider = provider
    const epoch = state.epoch + 1
    const promise = new Promise<void>((resolve, reject) => { acknowledgements.set(epoch, { resolve, reject, timer: setTimeout(() => { const w = acknowledgements.get(epoch); acknowledgements.delete(epoch); w?.reject(bridgeError()) }, WAIT) }) })
    change({ epoch, kind: provider ? 'app' : 'guest', options: state.options, visitor: provider ? undefined : saved ?? 'new' }); return promise
  }
  const show = (value: boolean) => { if (opened !== value) { opened = value; emit(value ? 'open' : 'close') } }
  const api: WidgetAPI = {
    init: value => { if (value.slug !== slug) throw bridgeError('VALIDATION_ERROR'); publish({ ...state, options: { ...state.options, ...appearance(value, win.document) } }) },
    identify: value => identify(value), logout: () => identify(), open: () => show(true), close: () => show(false), toggle: () => show(!opened), on: hub.on, off: hub.off,
  }
  return {
    api, channel, getSnapshot: () => state,
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } },
    announce() { if (win.parent !== win) win.parent.postMessage({ type: MSG.ready, v: 1, channel }, '*'); else native?.(JSON.stringify({ v: 1, type: MSG.ready, slug })) },
    native: native !== null,
    start() {
      active = true; if (!replayed) previous = win.Superstep; win.Superstep = api; win.addEventListener('message', listen)
      if (widget && state.kind === 'pending') fallback = setTimeout(() => { if (state.kind === 'pending' && !host) change({ ...state, kind: 'guest', visitor: saved ?? 'new' }) }, 2000)
      if (!replayed) {
        replayed = true
        const queue: Command[] = Array.isArray(previous) ? previous : previous && 'q' in previous && Array.isArray(previous.q) ? previous.q : []
        for (const command of queue.slice(0,100)) { if (!Array.isArray(command)) continue; const [key,...args] = command; if (!['init','open','close','toggle','identify','logout','on','off'].includes(key)) continue
          try { const result = (api[key] as (...values: unknown[]) => unknown)(...args); if (result instanceof Promise) void result.catch(() => {}) } catch { /* bad queued command */ } }
      }
      return () => {
        active = false; win.removeEventListener('message', listen); clearTimeout(fallback)
        queueMicrotask(() => { if (active) return; rejectRequests(); localProvider = undefined; for (const w of acknowledgements.values()) { clearTimeout(w.timer); w.reject(bridgeError()) } acknowledgements.clear(); if (win.Superstep === api) win.Superstep = previous })
      }
    },
    async getToken(epoch: number) {
      if (epoch !== state.epoch || state.kind !== 'app') throw bridgeError()
      if (native && typeof localProvider === 'string' && issued) {
        // The token from the native app was used once; ask the app for a fresh one instead of reusing a possibly expired token.
        const value = await new Promise<string>((resolve, reject) => {
          if (nativeWait) { nativeWait.waiters.push({ resolve, reject }); return }
          nativeWait = { waiters: [{ resolve, reject }], timer: setTimeout(dropNative, WAIT) }
          native(JSON.stringify({ v: 1, type: MSG.request, id: `native-${++sequence}`, slug }))
        })
        if (epoch !== state.epoch) throw bridgeError(); return value
      }
      if (localProvider) {
        issued = true
        try { const value = await resolveToken(localProvider); if (epoch !== state.epoch) throw bridgeError(); return value } catch (error) { throw bridgeError(failureCode(error)) }
      }
      if (!host) throw bridgeError('CHAT_TOKEN_REQUIRED')
      const id = `request-${++sequence}`
      return new Promise<string>((resolve, reject) => { requests.set(id, { resolve, reject, timer: setTimeout(() => { requests.delete(id); reject(bridgeError()) }, WAIT) }); post({ type: MSG.request, id }) })
    },
    keep(token: string) { if (state.kind !== 'guest' || !visitorToken(token)) return; saved = token
      if (host) post({ type: MSG.save, token }); else try { win.localStorage.setItem(storageKey(slug), token) } catch { /* blocked storage */ } },
    complete: finish, emit,
  }
}
export type FrameBridge = ReturnType<typeof createFrameBridge>
