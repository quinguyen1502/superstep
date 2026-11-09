/** Knowledge bases: API types shared by the settings section and the Retriever node settings. */
export type KbFile = { id: string; filename: string; size: number; chunks: number; created: number }
export type KnowledgeBase = { id: string; name: string; description: string | null; model: string; credential_id: string | null
  embedder: string | null; dims?: number | null; documents: number; chunks: number; created: number; files?: KbFile[] }
export type KbHit = { text: string; score: number; document_id: string; filename: string; index: number }
export const KB_ACCEPT = '.txt,.md,.pdf'
export const fmtBytes = (n: number) => n < 1024 ? `${n} B` : n < 1024 ** 2 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 ** 2).toFixed(1)} MB`
