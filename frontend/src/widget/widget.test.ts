// The chat widget: its options, the host side of the token handshake, and the bubble.
import { describe, expect, it } from 'vitest'
import { answer, frameUrl, mount, MSG, optionsOf, storageKey, type WidgetOptions } from './widget'
import { iframeSnippet, widgetSnippet } from '@/lib/chat'
import viCatalog from '@/locales/vi.json'

const O: WidgetOptions = { slug: 'help', origin: 'https://studio.example.com', position: 'right', open: false, vi: false }
const V1 = '0123456789abcdef.0123456789abcdef0123456789abcdef', V2 = 'abcdef0123456789.abcdef0123456789abcdef0123456789'
const store = (init: Record<string, string> = {}) => { const m = new Map(Object.entries(init))
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, v) }, m } }

describe('chat widget', () => {
  it('reads its options from the script tag', () => {
    const s = document.createElement('script'); s.src = 'https://studio.example.com/c/widget.js'; s.dataset.slug = 'help'; s.dataset.position = 'left'; s.dataset.open = 'true'
    expect(optionsOf(s, 'vi-VN')).toEqual({ slug: 'help', origin: 'https://studio.example.com', position: 'left', open: true, vi: true })
    expect(optionsOf(document.createElement('script'))).toBeNull()
    expect(frameUrl(O)).toBe('https://studio.example.com/c/help?embed=1&widget=1')
  })

  it('gives the stored token to the studio frame only, and keeps the one it sends', () => {
    const st = store({ [storageKey('help')]: V1 })
    expect(answer({ origin: O.origin, data: { type: MSG.ready } }, O, st)).toEqual({ type: MSG.token, token: V1 })
    expect(answer({ origin: 'https://evil.example', data: { type: MSG.ready } }, O, st)).toBeNull()
    expect(answer({ origin: O.origin, data: { type: MSG.save, token: V2 } }, O, st)).toBeNull()
    expect(st.m.get(storageKey('help'))).toBe(V2)
    answer({ origin: 'https://evil.example', data: { type: MSG.save, token: 'x' } }, O, st)
    expect(st.m.get(storageKey('help'))).toBe(V2)
    const blocked = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } }
    expect(answer({ origin: O.origin, data: { type: MSG.ready } }, O, blocked)).toEqual({ type: MSG.token, token: null })
  })

  it('draws a bubble that opens and closes the chat frame', () => {
    const b = mount({ ...O, vi: true }, document, store())
    const panel = document.getElementById('superstep-chat-panel')!
    expect(panel.querySelector('iframe')!.src).toBe(frameUrl(O))
    expect([panel.style.display, b.getAttribute('aria-expanded'), b.getAttribute('aria-label')]).toEqual(['none', 'false', viCatalog.chat.widget.open])
    b.click(); expect([panel.style.display, b.getAttribute('aria-label')]).toEqual(['block', viCatalog.chat.widget.close])
    b.click(); expect(panel.style.display).toBe('none')
  })

  it('snippets point at this studio', () => {
    expect(widgetSnippet('help', 'https://s.example')).toBe('<script src="https://s.example/c/widget.js" data-slug="help" async></script>')
    expect(iframeSnippet('help', 'https://s.example')).toContain('src="https://s.example/c/help?embed=1"')
  })
})
