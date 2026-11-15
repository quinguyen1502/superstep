/** My chat accounts: slot types, the slot list hook, and the slot key. */
import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'

export type Slot = { kind: string; team_id: string | null; team_name: string | null; available: boolean; external_id: string | null; verified: boolean; code_pending: boolean; code_expires: number | null }
export type Slots = { slots: Slot[] }

export function useSlots() {
  const [data, setData] = useState<Slots | null>(null); const [err, setErr] = useState('')
  const load = useCallback(() => api<Slots>('/api/approvals/identities').then(d => { setData(d); setErr('') }).catch(e => setErr(e.message)), [])
  useEffect(() => { load() }, [load])
  return { slots: data?.slots ?? null, setData, load, err }
}
export const slotKey = (s: Slot) => `${s.kind}:${s.team_id || ''}`
