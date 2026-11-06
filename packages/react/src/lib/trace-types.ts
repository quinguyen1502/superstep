import type { BrowserFacts } from './browser.js'
/** Structural inputs supplied by a host; no Studio trace/state module is imported. */
export type RunEvent = { type: string; node?: string; iteration?: number; delta?: unknown }
export type Span = { node: string; label: string; type: string; status: string; duration?: number; input?: unknown; output?: unknown; error?: string
  browser?: BrowserFacts; agent?: { browser?: BrowserFacts; kind: string; tool?: string; child_run_id?: string; to_label?: string; to?: string } }
export type Trace = { spans: Span[] }
