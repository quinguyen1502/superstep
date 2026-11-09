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
export type UsageSummary = {
  window: UsageWindow; bucket: 'hour' | 'day'; bucket_seconds: number; since: number; until: number
  totals: UsageTotals; series: UsageBucket[]; top_workflows: UsageWorkflow[]; grafana_url: string | null
}
export type UsageHealth = {
  approvals: { waiting: number; oldest_age_s: number | null; expired: number }
  webhooks: { failed: number; retrying: number }
  schedules: { overdue: number; disabled: number; disabled_list: { id: string; workflow_id: string; name: string; note: string | null }[] }
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
