/** LLM provider registry as served by GET /api/providers; one source of truth for the UI. */
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export type ProviderInfo = { id: string; label: string; default_base_url: string; default_model: string; key_required: boolean
  header_fields: string[]; settings_fields: string[]; supports_tools: boolean; streaming: boolean; local: boolean
  supports_embeddings: boolean; default_embedding_model: string; kind: 'chat' | 'decision' | 'email' }
export type ProbeResult = { ok: true; provider: string; base_url: string; models: string[]; latency_ms: number }

let cache: Promise<ProviderInfo[]> | null = null
export function useProviders() {
  const [items, setItems] = useState<ProviderInfo[]>([])
  useEffect(() => { (cache ??= api<ProviderInfo[]>('/api/providers').catch(e => { cache = null; throw e })).then(setItems).catch(() => {}) }, [])
  return items
}
export const probeProvider = (id: string, body: { api_key: string; base_url: string | null; headers: Record<string, string>; settings?: Record<string, unknown>; credential_id?: string }) =>
  api<ProbeResult>(`/api/providers/${id}/test`, { method: 'POST', json: body })
export const credentialModels = (cid: string) => api<ProbeResult>(`/api/credentials/${cid}/models`)
export type EmbeddingTest = { ok: true; model: string; dims: number; latency_ms: number }
export const testEmbedding = (cid: string, model: string) => api<EmbeddingTest>(`/api/credentials/${cid}/embeddings/test`, { method: 'POST', json: { model } })
