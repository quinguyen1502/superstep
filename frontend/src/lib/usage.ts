/** Admin usage API types (GET /api/admin/usage, /api/admin/usage/health) and the Usage page's number formatting. */
export type UsageWindow = '24h' | '7d' | '30d'
export type UsageSort = 'runs' | 'cost'
export const USAGE_WINDOWS: UsageWindow[] = ['24h', '7d', '30d']
export const SERIES_STATUSES = ['ok', 'error', 'timeout', 'cancelled', 'other'] as const
export type SeriesStatus = typeof SERIES_STATUSES[number]

export type UsageTotals = {
  runs: number; by_status: Record<string, number>; success_rate: number | null; tokens_in: number; tokens_out: number
  cost_usd: number; unpriced_runs: number; unpriced_share: number | null
}
export type UsageBucket = { start: number } & Record<SeriesStatus, number>
export type UsageWorkflow = {
  workflow_id: string | null; name: string | null; runs: number; errors: number; error_rate: number | null
  tokens_in: number; tokens_out: number; cost_usd: number; unpriced_runs: number
}
export type UsageModelKind = 'llm' | 'embedding' | 'review'
export type UsageModel = {
  kind: UsageModelKind; model: string; provider: string; runs: number; calls: number; errors: number
  tokens_in: number; tokens_out: number; cost_usd: number; unpriced_rows: number; avg_duration_ms: number | null
}
export type UsageUser = {
  user_id: string | null; email: string | null; deleted: boolean; runs: number; tokens_in: number; tokens_out: number
  cost_usd: number; unpriced_runs: number
}
export type UsageTeam = {
  team_id: string; name: string | null; members: number; runs: number; tokens_in: number; tokens_out: number
  cost_usd: number; unpriced_runs: number
}
export type UsageSummary = {
  window: UsageWindow; bucket: 'hour' | 'day'; bucket_seconds: number; since: number; until: number
  totals: UsageTotals; series: UsageBucket[]; top_workflows: UsageWorkflow[]; grafana_url: string | null
  models: UsageModel[]; models_since: number | null; users: UsageUser[]; teams: UsageTeam[]; teams_shared_members: number
}
export type ChannelRefusal = { code: string; kind: string; count: number }
export type UsageHealth = {
  approvals: { waiting: number; oldest_age_s: number | null; expired: number }
  webhooks: { failed: number; retrying: number }
  schedules: { overdue: number; disabled: number; disabled_list: { id: string; workflow_id: string; name: string; note: string | null }[] }
  channels: { refused: ChannelRefusal[]; started: number; refused_total: number; refusal_share: number | null }
}

export type ModelSort = 'cost' | 'tokens' | 'calls'
export const MODEL_SORTS: ModelSort[] = ['cost', 'tokens', 'calls']

/** Model rows ordered by cost, tokens or calls (largest first), then by model name. */
export function sortModels(rows: UsageModel[], by: ModelSort): UsageModel[] {
  const key = (m: UsageModel) => by === 'cost' ? m.cost_usd : by === 'tokens' ? m.tokens_in + m.tokens_out : m.calls
  return [...rows].sort((a, b) => key(b) - key(a) || a.model.localeCompare(b.model))
}

/** Whole numbers in the user's locale. */
export const fmtCount = (n: number, lang?: string) => new Intl.NumberFormat(lang).format(n)

/** USD with up to 4 decimals below 1 USD and 2 above; "at least" is the caller's prefix when some runs have no price. */
export function fmtUsd(v: number, lang?: string): string {
  return new Intl.NumberFormat(lang, { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: Math.abs(v) < 1 ? 4 : 2 }).format(v)
}

/** A 0..1 share as a percentage with at most one decimal; an em dash when unknown. */
export function fmtShare(v: number | null | undefined, lang?: string): string {
  return v === null || v === undefined ? '—' : new Intl.NumberFormat(lang, { style: 'percent', maximumFractionDigits: 1 }).format(v)
}

/** Seconds as the largest whole unit: 45 s, 12 min, 3 h, 2 d. */
export function fmtAge(s: number | null | undefined): { n: number; unit: 's' | 'min' | 'h' | 'd' } | null {
  if (s === null || s === undefined) return null
  if (s < 60) return { n: Math.round(s), unit: 's' }
  if (s < 3600) return { n: Math.floor(s / 60), unit: 'min' }
  if (s < 86400) return { n: Math.floor(s / 3600), unit: 'h' }
  return { n: Math.floor(s / 86400), unit: 'd' }
}

/** Total runs of one bucket. */
export const bucketTotal = (b: UsageBucket) => SERIES_STATUSES.reduce((sum, k) => sum + (b[k] || 0), 0)
