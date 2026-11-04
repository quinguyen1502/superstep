import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { createInstance } from 'i18next'
import { I18nextProvider } from 'react-i18next'
import { ChatConfirmation, ChatLogo, ChatMarkdown, ChatThread, ChatPresentationProvider } from '../src/index'

const i18n = createInstance()
await i18n.init({ lng: 'en', resources: { en: { translation: { chat: { waitingReviewer: 'Waiting for review', openApprovals: 'Open approvals' }, errors: { CHAT_NOT_PUBLISHED: 'Chat unavailable from the host language' } } } } })
const render = (node: React.ReactNode) => renderToStaticMarkup(<I18nextProvider i18n={i18n}>{node}</I18nextProvider>)

describe('presentation without a Studio application', () => {
  it('renders a logo without a router, API or browser globals', () => {
    const html = render(<ChatLogo title="Portal" />)
    expect(html).toContain('data-logo="initial"')
    expect(html).toContain('>P</span>')
  })
  it('sanitises markdown without importing Studio state', () => {
    const html = render(<ChatMarkdown text={'**Answer** [link](javascript:alert(1)) <script>bad()</script>\n\n![remote](https://example.test/tracker.png)'} />)
    expect(html).toContain('<strong>Answer</strong>')
    expect(html).not.toContain('href="javascript:')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('<img')
  })
  it('uses the host i18next instance for coded errors', () => {
    const html = render(<ChatThread turns={[{ id: 'failed', role: 'assistant', text: 'Server fallback', status: 'error', code: 'CHAT_NOT_PUBLISHED', created: 1 }]}
      mode="none" events={[]} trace={{ spans: [] }} pending={null} running={false} />)
    expect(html).toContain('Chat unavailable from the host language')
    expect(html).not.toContain('Server fallback')
  })
  it('uses rendered server errors when events lack translation arguments', () => {
    i18n.addResource('en', 'translation', 'errors.MCP_ARGUMENT_TYPE', 'Argument {{name}} must be of type {{type}}')
    const html = render(<ChatThread turns={[{ id: 'argument-failed', role: 'assistant', text: 'Argument values must be of type array', status: 'error', code: 'MCP_ARGUMENT_TYPE', created: 1 }]}
      mode="none" events={[]} trace={{ spans: [] }} pending={null} running={false} />)
    expect(html).toContain('Argument values must be of type array')
    expect(html).not.toContain('{{name}}')
    expect(html).not.toContain('{{type}}')
  })
  it('leaves reviewer navigation with the host', () => {
    const turn = { id: 'turn', role: 'assistant' as const, text: 'Review', status: 'waiting', answered_by: 'reviewer' as const, created: 1 }
    const alone = render(<ChatConfirmation turn={turn} busy={false} onAnswer={() => {}} />)
    expect(alone).toContain('Waiting for review')
    expect(alone).not.toContain('href=')
    const hosted = render(<ChatPresentationProvider value={{ reviewerLink: label => <a href="/my-reviews">{label}</a> }}>
      <ChatConfirmation turn={turn} busy={false} onAnswer={() => {}} />
    </ChatPresentationProvider>)
    expect(hosted).toContain('href="/my-reviews"')
    expect(hosted).toContain('Open approvals')
  })
})
