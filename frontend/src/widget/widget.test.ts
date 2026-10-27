// The chat widget (TASK-0143): its options, the host side of the token handshake, and the bubble.
import { describe, expect, it } from 'vitest'
import { answer, frameUrl, mount, MSG, optionsOf, storageKey, type WidgetOptions } from './widget'
import { iframeSnippet, widgetSnippet } from '@/lib/chat'

const O: WidgetOptions = { slug: 'help', origin: 'https://studio.example.com', position: 'right', open: false, vi: false }
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
    const st = store({ [storageKey('help')]: 'v1.sig' })
    expect(answer({ origin: O.origin, data: { type: MSG.ready } }, O, st)).toEqual({ type: MSG.token, token: 'v1.sig' })
    expect(answer({ origin: 'https://evil.example', data: { type: MSG.ready } }, O, st)).toBeNull()
    expect(answer({ origin: O.origin, data: { type: MSG.save, token: 'v2.sig' } }, O, st)).toBeNull()
    expect(st.m.get(storageKey('help'))).toBe('v2.sig')
    answer({ origin: 'https://evil.example', data: { type: MSG.save, token: 'x' } }, O, st)
    expect(st.m.get(storageKey('help'))).toBe('v2.sig')
    const blocked = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } }
    expect(answer({ origin: O.origin, data: { type: MSG.ready } }, O, blocked)).toEqual({ type: MSG.token, token: null })
  })

  it('draws a bubble that opens and closes the chat frame', () => {
    const b = mount({ ...O, vi: true }, document, store())
    const panel = document.getElementById('superstep-chat-panel')!
    expect(panel.querySelector('iframe')!.src).toBe(frameUrl(O))
    expect([panel.style.display, b.getAttribute('aria-expanded'), b.getAttribute('aria-label')]).toEqual(['none', 'false', 'Mở chat'])
    b.click(); expect([panel.style.display, b.getAttribute('aria-label')]).toEqual(['block', 'Đóng chat'])
    b.click(); expect(panel.style.display).toBe('none')
  })

  it('snippets point at this studio', () => {
    expect(widgetSnippet('help', 'https://s.example')).toBe('<script src="https://s.example/c/widget.js" data-slug="help" async></script>')
    expect(iframeSnippet('help', 'https://s.example')).toContain('src="https://s.example/c/help?embed=1"')
  })
})
