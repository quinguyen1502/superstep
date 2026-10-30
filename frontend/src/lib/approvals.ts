/** Approval channels API types (TASK-0022). */
import type { TFunction } from 'i18next'
import type { AiOpinion } from '@/lib/auto-approval'

// link_based: e-mail / Teams, answered on the studio's /approve page; target_required false: the connection is the destination (TASK-0047)
export type ChannelKind = { kind: string; fields: string[]; optional: string[]; link_based?: boolean; target_required?: boolean }
export type Channel = { id: string; kind: string; scope: 'user' | 'org'; name: string | null; team_id: string | null; hint: string; created: number; editable: boolean
  callback_url: string | null; callback_path: string; shared_callback_url: string | null; shared_callback_path: string | null
  // chat triggers (TASK-0074): null when the platform cannot start runs; missing_scopes null = unknown until the next Test
  chat: { missing_scopes: string[] | null; events_path: string | null; events_url: string | null } | null }
export type Channels = { kinds: ChannelKind[]; channels: Channel[]; public_url: string | null; is_admin: boolean; org_usable?: boolean }

/** "Slack · Acme (org)" — what a connection is called in selects and cards. */
export function channelLabel(t: TFunction, c: Channel) {
  return [t(`approvals.kind.${c.kind}`), c.name, t(`approvals.scope.${c.scope}`)].filter(Boolean).join(' · ')
}

/** A waiting step in the Approvals inbox (TASK-0065): the request only, never the run's state or trace (DEC-0043). */
export type InboxItem = { run_id: string; workflow_id: string | null; workflow_name: string | null; node: string; label: string | null; prompt: string | null
  channel: string | null; mine: boolean; owner_email: string | null; waiting_since: number; due_at: number | null; can_open: boolean
  ai?: AiOpinion | null }  // the AI's opinion in suggest mode (TASK-0188)

export const INBOX_POLL_MS = 30_000
