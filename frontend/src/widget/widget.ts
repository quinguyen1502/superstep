/** The chat widget (TASK-0143, REQ-0074, DEC-0067 decision 7): one script tag on another site draws a bubble that opens
 *  the published chat page in an iframe.
 *
 *    <script src="https://studio.example.com/c/widget.js" data-slug="help" data-position="right" data-open="false" async></script>
 *
 *  A browser may block the chat page's cookie inside the frame (Safari), so the widget keeps the visitor's token in the
 *  host page's localStorage and hands it to the frame with postMessage; the frame sends it to the API as X-Chat-Visitor
 *  and posts back a new one when it gets one. The widget only talks to the studio origin it was loaded from; the frame
 *  only accepts tokens from the sites in the chat's embed_origins. Plain DOM and inline styles: no dependency, nothing
 *  from the host page's CSS. Built on its own to dist/c/widget.js (vite.widget.config.ts). */

import { MSG } from './protocol'

export { MSG }
export type WidgetOptions = { slug: string; origin: string; position: 'left' | 'right'; open: boolean; vi: boolean }
type Store = Pick<Storage, 'getItem' | 'setItem'>

export const storageKey = (slug: string) => `superstep-chat:${slug}`
export const frameUrl = (o: WidgetOptions) => `${o.origin}/c/${encodeURIComponent(o.slug)}?embed=1&widget=1`

/** The options of a widget script tag, or null when it has no data-slug. */
export function optionsOf(script: HTMLScriptElement, lang = navigator.language): WidgetOptions | null {
  const slug = script.dataset.slug?.trim()
  if (!slug) return null
  return { slug, origin: new URL(script.src, location.href).origin, position: script.dataset.position === 'left' ? 'left' : 'right',
    open: script.dataset.open === 'true', vi: lang.toLowerCase().startsWith('vi') }
}

/** The host side of the handshake: what to post back to the frame for a message, or null. Saves a token the frame sends. */
export function answer(e: { origin: string; data: unknown }, o: WidgetOptions, store: Store): Record<string, unknown> | null {
  if (e.origin !== o.origin || !e.data || typeof e.data !== 'object') return null
  const d = e.data as { type?: string; token?: unknown }
  if (d.type === MSG.ready) {
    let token: string | null = null
    try { token = store.getItem(storageKey(o.slug)) } catch { /* storage blocked: the frame gets a new visitor */ }
    return { type: MSG.token, token }
  }
  if (d.type === MSG.save && typeof d.token === 'string' && d.token.length < 200) {
    try { store.setItem(storageKey(o.slug), d.token) } catch { /* storage blocked */ }
  }
  return null
}

const CHAT = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>'
const CLOSE = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>'

/** Draws the bubble and the (hidden) frame, and answers the frame's messages. Returns the bubble button. */
export function mount(o: WidgetOptions, doc: Document = document, store: Store = localStorage): HTMLButtonElement {
  const side = o.position === 'left' ? 'left' : 'right'
  const panel = doc.createElement('div')
  panel.id = 'superstep-chat-panel'
  panel.style.cssText = `position:fixed;${side}:16px;bottom:88px;width:min(400px,calc(100vw - 32px));height:min(640px,calc(100vh - 120px));` +
    'border-radius:12px;overflow:hidden;box-shadow:0 12px 32px rgba(0,0,0,.24);z-index:2147483000;display:none;background:#fff'
  const frame = doc.createElement('iframe')
  frame.src = frameUrl(o); frame.title = 'Chat'
  frame.style.cssText = 'width:100%;height:100%;border:0;display:block'
  frame.setAttribute('allow', 'clipboard-write')
  panel.appendChild(frame)
  const button = doc.createElement('button')
  button.id = 'superstep-chat-button'; button.type = 'button'
  button.style.cssText = `position:fixed;${side}:16px;bottom:16px;width:56px;height:56px;border-radius:9999px;border:0;cursor:pointer;` +
    'display:flex;align-items:center;justify-content:center;background:#18181b;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.24);z-index:2147483001'
  const show = (open: boolean) => {
    panel.style.display = open ? 'block' : 'none'
    button.innerHTML = open ? CLOSE : CHAT
    button.setAttribute('aria-expanded', String(open))
    button.setAttribute('aria-label', open ? (o.vi ? 'Đóng chat' : 'Close chat') : (o.vi ? 'Mở chat' : 'Open chat'))
  }
  button.addEventListener('click', () => show(panel.style.display === 'none'))
  doc.defaultView?.addEventListener('message', e => {
    if (e.source !== frame.contentWindow) return
    const reply = answer(e, o, store)
    if (reply) frame.contentWindow?.postMessage(reply, o.origin)
  })
  show(o.open)
  doc.body.append(panel, button)
  return button
}

const script = typeof document !== 'undefined' ? document.currentScript : null
if (script instanceof HTMLScriptElement) {
  const o = optionsOf(script)
  if (o) { if (document.body) mount(o); else document.addEventListener('DOMContentLoaded', () => mount(o)) }
}
