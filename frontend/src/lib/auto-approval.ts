/** AI review of approvals (TASK-0188, REQ-0081, DEC-0075): the `approval.auto` policy of a Human node or of an Agent's
 * tool approval, and the API shapes of the kill switches and counts. The server validates and runs it. */
export const AUTO_MODES = ['off', 'suggest', 'auto'] as const
export const RULE_OPS = ['equals', 'not_equals', 'contains', 'not_contains', 'matches', 'gt', 'lt', 'empty'] as const
export const RULE_EFFECTS = ['human', 'reject'] as const
export const DEFAULT_CAP = 50, MAX_CAP = 10000, DEFAULT_MIN = 0.8, MAX_RULES = 20
export type AutoMode = typeof AUTO_MODES[number]
export type AutoRule = { field: string; op: typeof RULE_OPS[number]; value?: string | number; effect: typeof RULE_EFFECTS[number] }
export type AutoPolicy = { mode?: AutoMode; rules?: AutoRule[]; max_per_day?: number; min_confidence?: number; notify?: boolean
  judge?: { credential_id?: string; model?: string; instructions?: string } }
export type AutoStats = { days: number; approved: number; rejected: number; escalated: number; suggested: number
  agreed: number; disagreed: number; agreement: number | null; today: number }
export type WorkflowAuto = { workflow_id: string; paused: boolean; org_paused: boolean; enabled: boolean; stats?: AutoStats; can_manage?: boolean }
export type ReviewedWorkflow = { workflow_id: string; name: string | null; modes: AutoMode[]; paused: boolean; stats: AutoStats | null }
export type AutoStatus = { enabled: boolean; org_paused: boolean; can_manage: boolean }
/** The AI's opinion on a waiting step (suggest mode), as the inbox returns it. */
export type AiOpinion = { decision: 'approve' | 'reject' | 'escalate' | string; confidence: number | null; reason: string | null }

/** "83%" or null when no person has answered after an opinion yet. */
export const pct = (x: number | null | undefined) => x == null ? null : `${Math.round(x * 100)}%`
