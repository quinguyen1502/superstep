/** Plain-JS host API. The iframe owns React; the bubble uses the canonical shadcn tokens. */
import css from './styles.css?inline'
import { labels, tokens } from './assets.generated'
import { MSG, EVENTS, appearance, bridgeError, channelId, epochId, errorCode, failureCode, resolveToken, eventHub, payload, storageKey, userToken, visitorToken,
  type Appearance, type Command, type TokenProvider, type WidgetAPI } from './protocol'
export { MSG, storageKey }
export type { WidgetAPI, InitOptions } from './protocol'
export type WidgetOptions = { slug: string; origin: string; position: 'left' | 'right'; open: boolean; vi: boolean } & Appearance
export type Store = Pick<Storage, 'getItem' | 'setItem'>
export const frameUrl = (o: WidgetOptions) => `${o.origin}/c/${encodeURIComponent(o.slug)}?embed=1&widget=1`
const safeStore = (win: Window): Store | undefined => { try { return win.localStorage } catch { return undefined } }
const read = (store: Store | undefined, slug: string) => { try { const value = store?.getItem(storageKey(slug)); return visitorToken(value) ? value : null } catch { return null } }
const save = (store: Store | undefined, slug: string, value: unknown) => { if (visitorToken(value)) try { store?.setItem(storageKey(slug), value) } catch { /* blocked storage: identity lasts for this page */ } }
export function optionsOf(script: HTMLScriptElement, lang = navigator.language): WidgetOptions | null {
  const slug = script.dataset.slug?.trim(); if (!slug) return null
  const a = appearance({ ...script.dataset, language: script.dataset.language ?? script.dataset.lang }, script.ownerDocument)
  const vi = a.language ? a.language === 'vi' : lang.toLowerCase().startsWith('vi')
  return { slug, origin: new URL(script.src, script.ownerDocument.location.href).origin, position: a.position ?? 'right', open: script.dataset.open === 'true', vi, ...a }
}
/** Cached old frames get anonymous tokens only; JWTs require bridge v1's channel/epoch handshake. */
export function answer(e: { origin: string; data: unknown }, o: WidgetOptions, store?: Store): Record<string, unknown> | null {
  if (e.origin !== o.origin || !e.data || typeof e.data !== 'object') return null
  const d = e.data as { type?: string; token?: unknown }
  if (d.type === MSG.ready) return { type: MSG.token, token: read(store, o.slug) }
  if (d.type === MSG.save) save(store, o.slug, d.token)
  return null
}
const CHAT = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>'
const CLOSE = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m18 6-12 12M6 6l12 12"/></svg>'
const WAIT = 10000
export function createWidget(win: Window, defaultOrigin: string, store = safeStore(win)) {
  const doc = win.document, hub = eventHub()
  let opts: WidgetOptions | null = null, root: HTMLDivElement | null = null, panel: HTMLDivElement | null = null, frame: HTMLIFrameElement | null = null, button: HTMLButtonElement | null = null
  let channel = '', epoch = 0, provider: TokenProvider | undefined, opened = false, attempt = 0
  const acknowledgements = new Map<number, { resolve: () => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>()
  const emitError = (code: string) => hub.emit('error', { slug: opts?.slug ?? '', code: errorCode(code) })
  const settle = (key: number, code?: string) => { const wait = acknowledgements.get(key); if (!wait) return; clearTimeout(wait.timer); acknowledgements.delete(key); if (code) wait.reject(bridgeError(code)); else wait.resolve() }
  const rejectPending = () => { for (const key of acknowledgements.keys()) settle(key, 'HTTP_ERROR') }
  const send = (data: object) => { if (channel && frame?.contentWindow && opts) frame.contentWindow.postMessage({ v: 1, channel, epoch, ...data }, opts.origin) }
  const token = resolveToken
  const synchronize = async () => {
    if (!opts || !channel) return
    const mine = epoch, myChannel = channel, myAttempt = ++attempt, current = provider
    send({ type: MSG.configure, options: { language: opts.language ?? (opts.vi ? 'vi' : 'en'), color: opts.color, logo: opts.logo, position: opts.position } })
    if (!current) { send({ type: MSG.identity, visitor: read(store, opts.slug) }); return }
    send({ type: MSG.identity, pending: true })
    try { const value = await token(current); if (mine === epoch && myChannel === channel && myAttempt === attempt) send({ type: MSG.identity, token: value }) }
    catch (error) { if (mine === epoch && myChannel === channel && myAttempt === attempt) send({ type: MSG.identity, error: failureCode(error) }) }
  }
  const paint = () => {
    if (!opts || !root || !panel || !button || !frame) return
    root.dataset.position = opts.position; panel.style.display = opened ? 'block' : 'none'
    const lang = opts.language ?? (opts.vi ? 'vi' : 'en'); frame.title = labels[lang].frame
    button.replaceChildren()
    if (!opened && opts.logo) { const image = doc.createElement('img'); image.src = opts.logo; image.alt = ''; button.append(image) }
    else button.innerHTML = opened ? CLOSE : CHAT
    button.setAttribute('aria-expanded', String(opened)); button.setAttribute('aria-label', labels[lang][opened ? 'close' : 'open'])
    for (const [key, value] of Object.entries(tokens)) root.style.setProperty(key, value)
    if (opts.color) root.style.setProperty('--ss-widget-primary', opts.color)
  }
  const show = (value: boolean) => { if (opened === value) return; opened = value; paint(); if (opts) hub.emit(value ? 'open' : 'close', { slug: opts.slug }) }
  const listen = (e: MessageEvent) => {
    if (!opts || e.source !== frame?.contentWindow || e.origin !== opts.origin || !e.data || typeof e.data !== 'object') return
    const d = e.data
    if (d.type === MSG.ready) {
      if (d.v === 1 && channelId(d.channel)) { if (channel !== d.channel) { channel = d.channel; void synchronize() } }
      else if (!provider) { const reply = answer(e, opts, store); if (reply) frame?.contentWindow?.postMessage(reply, opts.origin) }
      return
    }
    if (!channel) { if (!provider) answer(e, opts, store); return }
    if (d.v !== 1 || d.channel !== channel || !epochId(d.epoch) || d.epoch !== epoch) return
    if (d.type === MSG.save && !provider) save(store, opts.slug, d.token)
    else if (d.type === MSG.request && provider && channelId(d.id)) {
      const mine = epoch, myChannel = channel, current = provider
      void token(current).then(value => { if (mine === epoch && myChannel === channel) send({ type: MSG.response, id: d.id, token: value }) }, error => { if (mine === epoch && myChannel === channel) send({ type: MSG.response, id: d.id, error: failureCode(error) }) })
    } else if (d.type === MSG.ack) settle(epoch, d.error ? errorCode(d.error) : undefined)
    else if (d.type === MSG.event && EVENTS.includes(d.event)) { const data = payload(d.data, opts.slug); if (data) hub.emit(d.event, data) }
  }
  win.addEventListener('message', listen)
  const identify = (value?: TokenProvider) => {
    if (value !== undefined && typeof value !== 'function' && !userToken(value)) return Promise.reject(bridgeError('CHAT_TOKEN_INVALID'))
    rejectPending(); provider = value; epoch++; attempt++
    const result = new Promise<void>((resolve, reject) => { const key = epoch; acknowledgements.set(key, { resolve, reject, timer: setTimeout(() => { settle(key, 'HTTP_ERROR'); emitError('HTTP_ERROR') }, WAIT) }) })
    void synchronize(); return result
  }
  const api: WidgetAPI = {
    init(options) {
      if (!options || typeof options.slug !== 'string' || !/^[\w-]{1,200}$/.test(options.slug)) throw bridgeError('VALIDATION_ERROR')
      let origin: URL
      try { origin = new URL(options.baseUrl ?? opts?.origin ?? defaultOrigin) } catch { throw bridgeError('VALIDATION_ERROR') }
      if (!['http:','https:'].includes(origin.protocol) || origin.username || origin.password || origin.search || origin.hash || origin.pathname !== '/') throw bridgeError('VALIDATION_ERROR')
      const reset = !opts || opts.slug !== options.slug || opts.origin !== origin.origin
      if (reset) {
        if (opts) { rejectPending(); provider = undefined; epoch++; attempt++ }
        channel = ''; root?.remove(); root = doc.createElement('div'); root.id = 'superstep-chat-widget'
        const style = doc.createElement('style'); style.textContent = css
        panel = doc.createElement('div'); panel.id = 'superstep-chat-panel'
        frame = doc.createElement('iframe'); frame.setAttribute('allow','clipboard-write'); panel.append(frame)
        button = doc.createElement('button'); button.id = 'superstep-chat-button'; button.type = 'button'; button.setAttribute('aria-controls', panel.id)
        button.addEventListener('click', () => show(!opened)); root.append(style, panel, button)
        if (doc.body) doc.body.append(root); else doc.addEventListener('DOMContentLoaded', () => { if (root && !root.isConnected) doc.body.append(root) }, { once: true })
      }
      const a = appearance(options, doc), vi = (a.language ?? win.navigator.language).toLowerCase().startsWith('vi')
      opts = { ...(reset ? {} : opts), slug: options.slug, origin: origin.origin, position: a.position ?? opts?.position ?? 'right', open: !!options.open, vi, ...a }
      if (options.open !== undefined || reset) opened = !!options.open
      paint(); if (reset) frame!.src = frameUrl(opts); else if (channel) send({ type: MSG.configure, options: a })
    },
    open: () => show(true), close: () => show(false), toggle: () => show(!opened), identify: value => identify(value), logout: () => identify(), on: hub.on, off: hub.off,
  }
  return { api, dispose() { rejectPending(); provider = undefined; epoch++; attempt++; win.removeEventListener('message', listen); root?.remove(); root = null; frame = null; channel = '' }, get button() { return button } }
}
/** Compatibility helper for the original bubble API. */
export function mount(o: WidgetOptions, doc: Document = document, store?: Store): HTMLButtonElement {
  const widget = createWidget(doc.defaultView!, o.origin, store)
  widget.api.init({ ...o, baseUrl: o.origin, language: o.language ?? (o.vi ? 'vi' : 'en') }); return widget.button!
}
export function installWidget(win: Window, script: HTMLScriptElement) {
  const previous = win.Superstep
  if (previous && !Array.isArray(previous) && 'init' in previous && (previous as WidgetAPI & { version?: number }).version === 1) return previous as WidgetAPI
  const queue: Command[] = Array.isArray(previous) ? previous : previous && 'q' in previous && Array.isArray(previous.q) ? previous.q : []
  const widget = createWidget(win, new URL(script.src, win.location.href).origin), api = widget.api as WidgetAPI & { version: number }
  api.version = 1; win.Superstep = api
  const o = optionsOf(script); if (o) api.init({ ...o, baseUrl: o.origin })
  for (const command of queue.slice(0,100)) {
    if (!Array.isArray(command)) continue
    const [name, ...args] = command
    if (!['init','open','close','toggle','identify','logout','on','off'].includes(name)) continue
    try { const result = (api[name] as (...values: unknown[]) => unknown)(...args); if (result instanceof Promise) void result.catch(() => {}) } catch { /* invalid queued commands do not prevent later commands */ }
  }
  return api
}
const script = typeof document !== 'undefined' ? document.currentScript : null
if (script instanceof HTMLScriptElement) installWidget(window, script)
