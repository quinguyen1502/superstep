import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { ChannelLogo } from '@/components/approvals/channel-logo'

const html = (el: React.ReactElement) => renderToStaticMarkup(el)

describe('ChannelLogo',  => {
  it('renders a brand mark for each chat channel and a theme icon for e-mail', () => {
    for (const k of ['slack', 'telegram', 'whatsapp', 'teams']) expect(html(<ChannelLogo kind={k} />)).toMatch(/fill="#/)
    expect(html(<ChannelLogo kind="email" />)).not.toMatch(/fill="#/)
    expect(html(<ChannelLogo kind="email" />)).toContain('text-muted-foreground')
  })
  it('falls back to a generic icon for an unknown kind', () => {
    const out = html(<ChannelLogo kind="fax" />)
    expect(out).toContain('data-channel-logo="fax"'); expect(out).toContain('text-muted-foreground')
  })
  it('is hidden next to a label and named when standalone', () => {
    expect(html(<ChannelLogo kind="slack" />)).toContain('aria-hidden="true"')
    const alone = html(<ChannelLogo kind="slack" standalone />)
    expect(alone).toContain('role="img"'); expect(alone).toContain('aria-label=')
  })
  it('gives each Teams logo its own gradient ids', () => {
    const out = html(<><ChannelLogo kind="teams" /><ChannelLogo kind="teams" /></>)
    const ids = [...out.matchAll(/id="([^"]+)a"/g)].map(m => m[1])
    expect(ids).toHaveLength(2); expect(ids[0]).not.toBe(ids[1])
  })
})
