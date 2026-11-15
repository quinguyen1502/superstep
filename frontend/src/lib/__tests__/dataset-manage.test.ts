import { describe, expect, it } from 'vitest'
import { canManageDataset, type DatasetSummary } from '../datasets'
import type { Me } from '../rbac'

const person = (id: string, role: Me['role'], permissions: string[]): Me => ({ id, email: `${id}@example.com`, role, permissions, is_admin: role === 'admin', created: 1 })
const admin = person('admin', 'admin', ['org.manage', 'resources.manage'])
const owner = person('owner', 'editor', ['resources.manage'])
const peer = person('peer', 'editor', ['resources.manage'])
const viewer = person('viewer', 'viewer', [])
const team: DatasetSummary = { id: 't', name: 'T', description: null, owner_id: null, team_id: 'support', team_owner_id: 'owner', revision: 1 }
const personal: DatasetSummary = { ...team, owner_id: 'peer', team_id: null, team_owner_id: null }

describe('canManageDataset', () => {
  it('lets the team owner and admins manage a team dataset', () => {
    expect([admin, owner, peer, viewer, null].map(me => canManageDataset(me, team))).toEqual([true, true, false, false, false])
  })
  it('lets only the owner manage a personal dataset', () => {
    expect([admin, owner, peer].map(me => canManageDataset(me, personal))).toEqual([false, false, true])
  })
})
