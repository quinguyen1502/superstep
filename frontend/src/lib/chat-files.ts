/** Chat file transfers (TASK-0177): upload one file, and save one as a download with the chat's headers. */
import { api } from '@/lib/api'
import type { ChatAttachment } from '@/lib/chat'

export async function downloadFile(url: string, name: string, headers?: Record<string, string>) {
  const r = await fetch(url, { headers: { 'X-Requested-With': 'studio', ...headers } })
  if (!r.ok) throw new Error(String(r.status))
  const href = URL.createObjectURL(await r.blob())
  const a = Object.assign(document.createElement('a'), { href, download: name }); document.body.append(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

/** Uploads one file to a chat's attachments (multipart, field `file`). */
export const uploadChatFile = <T = ChatAttachment>(path: string, file: File, headers?: Record<string, string>) => {
  const body = new FormData(); body.append('file', file)
  return api<T>(path, { method: 'POST', body, headers })
}
