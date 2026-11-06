export type BrowserDetail = { operation?: string; status?: import('@superstep/react/chat').BrowserFacts['status']; approval?: string; sequence?: number; generation?: number; elapsed_ms?: number
  observation?: { origin?: string; page_generation?: number; text?: string; elements?: { role: string; text: string }[] }
  extracted?: Record<string, string>; artifact_id?: string }
export { BROWSER_STATUSES, browserStatus } from '@superstep/react/chat'
