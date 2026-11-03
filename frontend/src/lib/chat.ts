/** Studio settings and routes stay here; presentation helpers have one shared owner. */
import type { AttachmentLimits, ChatTurn, StepsMode } from '@superstep/react/chat'
export * from '@superstep/react/chat'

export const ACCESS = ['anonymous', 'signed_in', 'app'] as const
export type ChatAccess = string | string[]
export const accessModes = (access: ChatAccess): string[] => Array.isArray(access) ? access : [access]
export const MAX_SUGGESTIONS = 4
export const LOGO_MAX_KB = 256   // PNG, JPEG or WebP (TASK-0145); the server checks it again
export const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp']
export type AttachmentSettings = AttachmentLimits & { field: string }
export type ChatSettings = { enabled: boolean; slug: string; access: ChatAccess; input_field: string; reply_field: string
  messages_field: string; max_turns: number; steps: StepsMode; retention_days: number
  title: string; intro: string; suggestions: string[]; daily_limit: number; embed_origins: string[]
  logo: string   // the logo's hash, "" for none; a data: URL sets a new one, "" removes it (TASK-0145)
  attachments: AttachmentSettings; attachment_ceiling?: { max_mb: number; max_files: number } }   // the ceiling is read only
/** The published page's settings (GET /api/public/chat/{slug}, TASK-0140): what a visitor may know of the chat. */
export type PublicChatPage = { slug: string; title: string; intro: string; suggestions: string[]; access: ChatAccess
  steps_mode: StepsMode; signed_in: boolean; embed_origins: string[]; logo: string; attachments?: AttachmentLimits }
export type ChatSession = { id: string; workflow_id: string; channel: string; title?: string | null; last_run_id?: string | null
  created: number; updated: number; thumbs_down?: boolean; source_session_id?: string; source_turn_id?: string; source_action?: "edit" | "regenerate" }
export type RatingCounts = { up: number; down: number }
export type RatingTotals = { d7: RatingCounts; d30: RatingCounts }
/** The share of thumbs down, as a whole percent, or null when there are no ratings (DEC-0070). */
export const downShare = (c: RatingCounts): number | null => { const n = c.up + c.down; return n ? Math.round(100 * c.down / n) : null }
export type ChatSessionFull = ChatSession & { steps_mode: StepsMode; turns: ChatTurn[] }

/** The chat is published (DEC-0067): on, and open to more than studio users. */
export const published = (s: Pick<ChatSettings, 'enabled' | 'access'>) => s.enabled && ACCESS.some(a => accessModes(s.access).includes(a))
/** The page's address on this studio. */
export const pageUrl = (slug: string, origin = location.origin) => `${origin}/c/${slug}`
/** A chat's logo image (TASK-0145): the published one, or the builder's (published or not), or a new one not saved yet. */
export const publicLogoUrl = (slug: string, hash: string) => hash ? `/api/public/chat/${slug}/logo?v=${hash}` : undefined
export const logoUrl = (wid: string, logo: string) => !logo ? undefined : logo.startsWith('data:') ? logo : `/api/workflows/${wid}/chat/logo?v=${logo}`
/** The embed snippets (TASK-0143): the page in an iframe, or the widget's bubble that opens it and keeps the history. */
export const iframeSnippet = (slug: string, origin = location.origin) =>
  `<iframe src="${pageUrl(slug, origin)}?embed=1" title="Chat" style="width:100%;height:600px;border:0"></iframe>`
export const widgetSnippet = (slug: string, origin = location.origin) =>
  `<script src="${origin}/c/widget.js" data-slug="${slug}" async></script>`

/** How many answers a run has in the chat: the worker writes one each time the run settles (waiting, then done). */
export const answers = (turns: ChatTurn[], runId?: string) => runId ? turns.filter(t => t.role === 'assistant' && t.run_id === runId).length : 0
