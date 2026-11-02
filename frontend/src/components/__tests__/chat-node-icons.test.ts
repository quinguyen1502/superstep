import { expect, it } from 'vitest'
import { NODE_ICONS } from '@superstep/react/node-icons'
import { META } from '@/components/editor/meta'

it('preserves every Studio node icon in shared chat steps, including synthetic exits', () => {
  for (const [type, metadata] of Object.entries(META)) expect(NODE_ICONS[type], type).toBe(metadata.icon)
})
