import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { ChatMarkdown } from '@/components/chat/chat-markdown'

const html = (text: string) => renderToStaticMarkup(<ChatMarkdown text={text} />)

describe('ChatMarkdown',  => {
  it('renders GitHub-flavoured Markdown', () => {
    const out = html('**bold** and a list:\n\n- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |')
    expect(out).toContain('class="typeset typeset-chat"'); expect(out).toContain('<strong>bold</strong>'); expect(out).toContain('<li>one</li>'); expect(out).toContain('<table')
  })
  it('drops raw HTML, scripts, unsafe links and remote images', () => {
    const out = html('<script>alert(1)</script>\n\nhi <b onclick="x()">b</b> [x](javascript:alert(1)) ![pic](https://evil.test/p.png)')
    expect(out).not.toContain('<script'); expect(out).not.toContain('onclick'); expect(out).not.toContain('javascript:')
    expect(out).not.toContain('<img'); expect(out).toContain('[pic]')
  })
  it('opens links in a new tab without the opener', () => {
    expect(html('[docs](https://example.com)')).toContain('rel="noopener noreferrer nofollow"')
  })
  it('puts fenced code in a Code Block', () => {
    const out = html('```python\nprint(1)\n```')
    expect(out).toContain('data-slot="code-block"'); expect(out).toContain('python'); expect(out).toContain('print(1)')
  })
})
