/** Chat file transfers (TASK-0177): upload one file, and save one as a download with the chat's headers. */
import { api } from '@/lib/api'
import type { ChatAttachment } from '@/lib/chat'

export { downloadFile } from '@superstep/react/files'

/** Uploads one file to a chat's attachments (multipart, field `file`). */
export const uploadChatFile = <T = ChatAttachment>(path: string, file: File, headers?: Record<string, string>) => {
  const body = new FormData(); body.append('file', file)
  return api<T>(path, { method: 'POST', body, headers })
}
