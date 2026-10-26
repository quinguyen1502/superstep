import { test, expect, type Page } from '@playwright/test'
import { apiToken, N } from './helpers'
// REQ-0073: an Agent node calls another workflow as a tool. TASK-0135: the parent waits for its child run, the child's
// approval is in the Approvals inbox with both workflow names, and answering it finishes both runs.
const shot = async (page: Page, name: string, sel = 'body') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const T = {
  vi: { password: 'Mật khẩu', waiting: 'Đang chờ một workflow khác', calledBy: 'Được gọi bởi' },
  en: { password: 'Password', waiting: 'Waiting for another workflow', calledBy: 'Called by' },
}
const STATE = [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }, { name: 'steps', type: 'list' }]
const DESK = (name: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('ask', 'human', 300, { label: 'Refund approval', prompt: 'Refund for {{state.message}}?', output_field: 'answer' }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ask' }, { id: 'e2', source: 'ask', target: 'end' }] })
const TEAM = (name: string, desk: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('ag', 'agent', 300, { label: 'Supervisor', model: 'gpt-4o-mini', prompt: 'Help the customer: {{state.message}}', output_field: 'answer',
    steps_field: 'steps', max_rounds: 5, tools: [{ name: 'refund_desk', description: 'Questions about refunds', source: 'workflow', workflow_id: desk, inputs: ['message'], outputs: ['answer'] }] }),
  N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ag' }, { id: 'e2', source: 'ag', target: 'end' }] })

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', viewport: { width: 1440, height: 1000 } })
  test(`workflow tool: the parent waits, the child's approval finishes both (${lang})`, async ({ page }) => {
    await page.goto('/login'); await page.getByLabel(T[lang].password, { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }
    const n = Date.now() % 100000
    const desk = (await (await page.request.post('/api/workflows', { headers: H, data: DESK(`Refund desk ${lang} ${n}`) })).json()).data.id
    const team = (await (await page.request.post('/api/workflows', { headers: H, data: TEAM(`Support team ${lang} ${n}`, desk) })).json()).data.id
    await page.goto(`/workflows/${team}${lang === 'en' ? '?theme=dark' : ''}`)
    await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order B200"}')
    await page.locator('#run-btn').click()
    // the parent waits for its child: no answer box, the child's workflow and a link to its run
    await expect(page.locator('#child-wait-panel')).toContainText(T[lang].waiting, { timeout: 30_000 })
    await expect(page.locator('#child-wait-panel')).toContainText(`Refund desk ${lang} ${n}`)
    await expect(page.locator('#human-panel')).toHaveCount(0)
    await expect(page.locator('#trace-summary')).toContainText(T[lang].waiting)
    await page.reload(); await page.locator('#run-tab').click()  // the history now knows the child is waiting for an approval
    await page.locator('#history-all').click(); await page.getByTestId('history-row').first().click()
    await expect(page.locator('#child-wait-approval')).toBeVisible({ timeout: 15_000 })
    await shot(page, `workflow-tool-parent-waiting-${lang}`, '#run-logs-panel')

    // the Approvals inbox lists the child's question with both workflow names
    await page.goto('/approvals')
    const row = page.locator('[data-testid=inbox-row]', { hasText: `Support team ${lang} ${n} › Refund desk ${lang} ${n}` })
    await expect(row).toBeVisible()
    await shot(page, `workflow-tool-inbox-${lang}`, `[data-testid=inbox-row][data-run="${await row.getAttribute('data-run')}"]`)
    await row.getByTestId('answer-approve').click()
    await expect(row).toHaveCount(0)

    // the child finishes, then the parent: back on the supervisor, its run moves on by itself
    await page.goto(`/workflows/${team}${lang === 'en' ? '?theme=dark' : ''}`)
    await page.locator('#run-tab').click(); await page.locator('#history-all').click(); await page.getByTestId('history-row').first().click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    await shot(page, `workflow-tool-parent-done-${lang}`, '#run-logs-panel')

    // the child run says who called it
    await page.goto(`/workflows/${desk}${lang === 'en' ? '?theme=dark' : ''}`)
    await page.locator('#run-tab').click(); await page.locator('#history-all').click()
    await expect(page.getByTestId('history-source').first()).toBeVisible(); await page.getByTestId('history-row').first().click()
    await expect(page.locator('#trace-called-by')).toContainText(`${T[lang].calledBy} Support team ${lang} ${n}`)
    await shot(page, `workflow-tool-child-called-by-${lang}`, '#run-logs-panel')
    await page.locator('#trace-open-parent').click()
    await expect(page).toHaveURL(new RegExp(`/workflows/${team}\\?run=`))
  })
})
