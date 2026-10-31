// TASK-0205 (DEC-0076): the CLI sign-in page asks for the code from the terminal; a code in the link is not used.
import { afterEach, describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/lib/i18n'
import { CliAuthorizePage } from '@/pages/CliAuthorize'

const render = (url: string) => renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><CliAuthorizePage /></MemoryRouter>)

afterEach(() => i18n.changeLanguage('en'))

describe('CLI sign-in page', () => {
  it('ignores a code in the link and waits for the typed one', () => {
    const out = render('/cli/authorize?code=abcd1234')
    expect(out).toMatch(/<input[^>]*id="cli-code"[^>]*value=""/); expect(out).not.toContain('abcd1234')
    expect(out).toMatch(/<button[^>]*id="cli-approve"[^>]*disabled/)
    expect(out).toContain('id="cli-warning"')
  })
  it('warns in Vietnamese too', async () => {
    await i18n.changeLanguage('vi')
    expect(render('/cli/authorize')).toContain('Không bao giờ nhập mã do người khác gửi cho bạn.')
  })
})
