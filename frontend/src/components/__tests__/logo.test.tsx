import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Logo, LogoMark } from '@/components/logo'

const html = (el: React.ReactElement) => renderToStaticMarkup(el)

describe('Logo',  => {
  it('draws the Step-up mark with theme tokens only, no hard-coded colours', () => {
    const out = html(<LogoMark />)
    expect(out).toContain('fill-primary'); expect(out).toContain('stroke-primary-foreground'); expect(out).toContain('fill-brand-accent')
    expect(out).not.toMatch(/#[0-9a-f]{3,8}/i)
  })
  it('mono variant uses currentColor', () => {
    const out = html(<LogoMark mono />)
    expect(out).toContain('stroke-current'); expect(out).toContain('fill-current'); expect(out).not.toContain('fill-primary')
  })
  it('shows the product name, or keeps it for screen readers only', () => {
    expect(html(<Logo />)).toContain('>Superstep<')
    expect(html(<Logo showName={false} />)).toContain('sr-only')
  })
})
