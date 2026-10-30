// TASK-0177: the composer's attach button follows the chat's settings; chips show the file; the settings section keeps
// the operator's ceiling.
import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import i18n from '@/lib/i18n'
import { ChatComposer, type ComposerFiles } from '@/components/chat/chat-composer'
import { AttachmentChip } from '@/components/chat/chat-attachments'
import { ChatAttachmentSettings } from '@/components/chat/chat-attachment-settings'
import { TooltipProvider } from '@/components/ui/tooltip'

const files = (enabled: boolean): ComposerFiles => ({ enabled, kinds: ['document', 'image'], max_files: 3, max_mb: 2,
  upload: () => Promise.reject(new Error('no')), remove: () => Promise.resolve() })
const composer = (f: ComposerFiles | null) => renderToStaticMarkup(<TooltipProvider>
  <ChatComposer disabled={false} running={false} onSend={() => {}} onStop={() => {}} files={f} /></TooltipProvider>)

describe('chat attachments UI', () => {
  it('has no attach button when attachments are off', () => {
    expect(composer(null)).not.toContain('id="chat-attach"')
    expect(composer(files(false))).not.toContain('id="chat-attach"')
  })
  it('has an attach button and a file input with the accepted endings when on', () => {
    const out = composer(files(true))
    expect(out).toContain('id="chat-attach"'); expect(out).toContain('accept=".pdf,.txt,.md,.csv,.png,.jpg,.jpeg,.webp"')
  })
  it('shows a chip with the name, the size and a thumbnail', () => {
    const out = renderToStaticMarkup(<AttachmentChip name="photo.png" size={2048} kind="image" preview="blob:x" />)
    expect(out).toContain('photo.png'); expect(out).toContain('2 KB'); expect(out).toContain('src="blob:x"')
    expect(renderToStaticMarkup(<AttachmentChip name="a.pdf" size={10} kind="document" />)).not.toContain('<img')
  })
  it('shows the limits and the server ceiling in settings, in en and vi', async () => {
    const value = { enabled: true, kinds: ['document' as const], max_files: 2, max_mb: 4, field: 'files' }
    const html = () => renderToStaticMarkup(<ChatAttachmentSettings value={value} ceiling={{ max_files: 8, max_mb: 20 }} lists={['files']} bad="attachments.max_mb" onChange={() => {}} />)
    await i18n.changeLanguage('en'); const en = html()
    expect(en).toContain('At most 20 on this server.'); expect(en).toMatch(/id="chat-attachments\.max_mb"[^>]*aria-invalid="true"/)
    expect(en).toContain('id="chat-attachments-kind-image"')
    await i18n.changeLanguage('vi'); expect(html()).toContain('Máy chủ này cho phép tối đa 8.')
    await i18n.changeLanguage('en')
    expect(renderToStaticMarkup(<ChatAttachmentSettings value={{ ...value, enabled: false }} lists={[]} bad="" onChange={() => {}} />)).not.toContain('chat-attachments-kind')
  })
})
