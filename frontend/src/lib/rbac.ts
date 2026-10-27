/** RBAC (TASK-0014): the signed-in user's role and permissions (GET /api/me), shared by every page. */
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export type Role = 'admin' | 'editor' | 'viewer'
export type Access = 'owner' | 'editor' | 'viewer'
export type Me = { id: string; email: string; role: Role; permissions: string[]; is_admin: boolean; created: number | null
  read_only?: boolean }  // read_only: the public demo's visitor, whose writes the API refuses
export type Share = { user_id: string; email: string; role: 'viewer' | 'editor'; created: number }
export type Shares = { owner: { id: string; email: string | null }; can_share: boolean; can_transfer: boolean; shares: Share[]; teams: TeamShare[] }
export type AdminUser = { id: string; email: string; role: Role; active: boolean; created: number | null; workflows: number }
export type RoleMatrix = { roles: { role: Role; permissions: string[] }[]; permissions: string[]; workflow_access: { access: Access; actions: string[] }[] }

let cached: Promise<Me> | null = null
export const loadMe = (fresh = false) => (!cached || fresh ? (cached = api<Me>('/api/me').catch(e => { cached = null; throw e })) : cached)

export function useMe(): Me | null {
  const [me, setMe] = useState<Me | null>(null)
  useEffect(() => { let live = true; loadMe().then(m => live && setMe(m)).catch(() => {}); return () => { live = false } }, [])
  return me
}

export const can = (me: Me | null, permission: string) => !!me?.permissions.includes(permission)
export const canEdit = (a?: Access | null) => a === 'owner' || a === 'editor'

// ---- TASK-0029 ----
export type TeamMember = { user_id: string; email: string; role: Role; active: boolean }
export type Team = { id: string; name: string; description: string | null; members: number; mine: boolean; member_list?: TeamMember[] }
export type Teams = { can_manage: boolean; teams: Team[] }
export type TeamShare = { team_id: string; name: string; role: 'viewer' | 'editor'; created: number }
export type AuditItem = { id: string; at: number; actor: string | null; action: string; target_type: string; target_id: string | null; target: string | null; details: Record<string, any> }
export type AuditPage = { items: AuditItem[]; total: number; limit: number; offset: number; categories: string[] }
export type Issue = { node_id: string; node: string; field: string; kind: 'credential' | 'knowledge_base' | 'mcp_server' | 'subgraph'; id: string; name: string | null; rebindable: boolean }
export type TransferPreview = { new_owner: string; issues: Issue[]; options: Record<string, { id: string; name: string }[]> }
export type Policy = { org_resources_roles: Role[]; default: Role[] }
