/** Tool node Code mode: what the server can run, read once from GET /api/meta/runtime. */
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export type CodeLanguageInfo = { id: 'python' | 'typescript'; available: boolean; problem: string | null; image: string; packages: string[]; starter: string }
export type CodeRuntime = {
  code_runtime: 'docker' | 'subprocess' | 'remote' | 'off'; available: boolean; problem: string | null; image: string; packages: string[]; starter: string
  limits: { memory: string; cpus: string; pids: number; seconds: number; source_kb: number }
  languages?: CodeLanguageInfo[]  // one entry per offered language; the top level is Python's
  demo?: boolean  // STUDIO_DEMO_MODE: off because this is the public demo
}

/** Why Code mode is off: the public demo, or the server setting. */
export const codeOffKey = (rt: CodeRuntime | null | undefined) => rt?.demo ? 'code.demoOff' : 'code.off'

/** The facts of one language; falls back to the top-level (Python) facts for servers from. */
export function languageInfo(rt: CodeRuntime | null, id: string): CodeLanguageInfo | null {
  if (!rt) return null
  return rt.languages?.find(l => l.id === id)
    ?? (id === 'python' ? { id: 'python', available: rt.available, problem: rt.problem, image: rt.image, packages: rt.packages, starter: rt.starter } : null)
}
export type CodeTestResult = { ok: boolean; value?: unknown; stdout?: string; traceback?: string; runtime?: string; duration_ms?: number
  error?: { code: string; message: string; details?: Record<string, unknown> } }

let cached: Promise<CodeRuntime> | null = null
export function loadCodeRuntime(): Promise<CodeRuntime> {
  cached ??= api<CodeRuntime>('/api/meta/runtime').catch(e => { cached = null; throw e })
  return cached
}

export function useCodeRuntime(): CodeRuntime | null {
  const [rt, setRt] = useState<CodeRuntime | null>(null)
  useEffect(() => { let live = true; loadCodeRuntime().then(r => { if (live) setRt(r) }).catch(() => {}); return () => { live = false } }, [])
  return rt
}
