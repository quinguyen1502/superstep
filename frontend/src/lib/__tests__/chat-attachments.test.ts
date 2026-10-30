// TASK-0177: the composer's checks before an upload use the same codes and limits as the API.
import { describe, expect, it } from 'vitest'
import { acceptOf, attachmentKind, attachmentProblem, fileSize, type AttachmentLimits } from '@/lib/chat'

const limits: AttachmentLimits = { enabled: true, kinds: ['document'], max_files: 2, max_mb: 1 }

describe('chat attachments', () => {
  it('reads the kind from the name ending', () => {
    expect(attachmentKind('Report.PDF')).toBe('document')
    expect(attachmentKind('photo.jpeg')).toBe('image')
    expect(attachmentKind('run.exe')).toBeNull()
  })
  it('lists the accepted endings', () => {
    expect(acceptOf(['image'])).toBe('.png,.jpg,.jpeg,.webp')
  })
  it('refuses a kind the chat does not take, a large file and one too many', () => {
    expect(attachmentProblem({ name: 'a.png', size: 1 }, limits, 0)?.code).toBe('CHAT_ATTACHMENT_TYPE')
    expect(attachmentProblem({ name: 'a.pdf', size: 2 * 1024 * 1024 }, limits, 0)).toEqual({ code: 'CHAT_ATTACHMENT_TOO_LARGE', params: { max_mb: 1 } })
    expect(attachmentProblem({ name: 'a.pdf', size: 10 }, limits, 2)).toEqual({ code: 'CHAT_ATTACHMENT_TOO_MANY', params: { max: 2 } })
    expect(attachmentProblem({ name: 'a.md', size: 10 }, limits, 1)).toBeNull()
  })
  it('shows sizes for people', () => {
    expect(fileSize(512)).toBe('512 B'); expect(fileSize(2048)).toBe('2 KB'); expect(fileSize(3 * 1024 * 1024)).toBe('3.0 MB')
  })
})
