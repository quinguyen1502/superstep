/** Only these facts may be shown to a chat visitor; observations and artifacts stay in Studio. */
export const BROWSER_STATUSES = ['confirmed', 'failed_before_effect', 'unknown', 'approval_required', 'challenge_required', 'expired', 'session_lost', 'stale_observation', 'policy_denied', 'cancelled', 'missing_input', 'dry_run'] as const
export type BrowserFacts = { operation?: string; status?: typeof BROWSER_STATUSES[number]; approval?: string }
export const browserStatus = (value?: string) => BROWSER_STATUSES.includes(value as typeof BROWSER_STATUSES[number]) ? value as typeof BROWSER_STATUSES[number] : undefined
