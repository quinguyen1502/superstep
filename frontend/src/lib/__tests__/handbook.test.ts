import { describe, expect, it } from 'vitest'
import { HANDBOOK_URL, handbookUrl } from '@/lib/handbook'

describe('handbookUrl', () => {
  it('builds English page links', () => {
    expect(handbookUrl('operate/expose-local', 'en')).toBe(`${HANDBOOK_URL}operate/expose-local/`)
  })
  it('uses the Vietnamese site and anchors', () => {
    expect(handbookUrl('/operate/channels.md', 'vi', 'whatsapp-cloud-api')).toBe(`${HANDBOOK_URL}vi/operate/channels/#whatsapp-cloud-api`)
  })
  it('falls back to English for unknown languages', () => {
    expect(handbookUrl('operate/channels', undefined, 'slack')).toBe('https://quinguyen1502.github.io/superstep/operate/channels/#slack')
  })
})
