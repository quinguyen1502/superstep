// TASK-0188: AI review settings (owner-only auto, rules, defaults) and the AI's opinion in the Approvals inbox, en and vi.
import { afterEach, describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import i18n from '@/lib/i18n'
import { AutoApprovalSettings } from '@/components/auto-approval-settings'
import { AiOpinionNote } from '@/components/approvals/ai-review-panel'
import { TooltipProvider } from '@/components/ui/tooltip'
import { pct, type AutoPolicy } from '@/lib/auto-approval'

const creds = [{ id: 'c1', name: 'OpenAI', provider: 'openai', hint: '…1234' }]
const render = (value: AutoPolicy | undefined, canAuto: boolean) => renderToStaticMarkup(<TooltipProvider>
  <AutoApprovalSettings idp="human" value={value} creds={creds} canAuto={canAuto} onChange={() => {}} /></TooltipProvider>)

afterEach(() => i18n.changeLanguage('en'))

describe('AI review settings', () => {
  it('is off by default and shows only the mode', () => {
    const out = render(undefined, true)
    expect(out).toContain('id="human-auto-mode"'); expect(out).not.toContain('id="human-auto-credential"')
  })
  it('tells editors that only the owner or an admin may answer automatically', () => {
    expect(render({ mode: 'suggest' }, false)).toContain('id="human-auto-owner-only"')
    expect(render({ mode: 'suggest' }, true)).not.toContain('id="human-auto-owner-only"')
  })
  it('shows the judge, limits and rules when on', () => {
    const out = render({ mode: 'auto', min_confidence: 0.8, max_per_day: 50, rules: [{ field: 'args.amount', op: 'gt', value: 100, effect: 'human' }] }, true)
    for (const id of ['human-auto-credential', 'human-auto-instructions', 'human-auto-min', 'human-auto-cap', 'human-auto-notify', 'human-auto-add-rule']) expect(out).toContain(`id="${id}"`)
    expect(out).toContain('args.amount'); expect(out.match(/data-testid="auto-rule"/g)).toHaveLength(1)
  })
  it('has no notify switch in suggest mode', () => { expect(render({ mode: 'suggest' }, true)).not.toContain('id="human-auto-notify"') })
  it('renders in vi', async () => {
    await i18n.changeLanguage('vi'); expect(render({ mode: 'suggest' }, false)).toContain('Chỉ chủ workflow hoặc quản trị viên')
  })
})

describe('AI opinion in the inbox', () => {
  it('shows the decision, confidence and reason', () => {
    const out = renderToStaticMarkup(<AiOpinionNote ai={{ decision: 'approve', confidence: 0.92, reason: 'Small refund.' }} />)
    expect(out).toContain('Suggests approve'); expect(out).toContain('92%'); expect(out).toContain('Small refund.')
  })
  it('formats rates', () => { expect(pct(null)).toBeNull(); expect(pct(0.834)).toBe('83%') })
})
