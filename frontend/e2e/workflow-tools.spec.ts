import { test, expect, type Page } from '@playwright/test'
import { apiToken, N } from './helpers'
// REQ-0073: an Agent node calls another workflow as a tool. TASK-0135: the parent waits for its child run, the child's
// approval is in the Approvals inbox with both workflow names, and answering it finishes both runs. TASK-0136: the tool
// card in the editor, and the child's steps nested under the tool call in the trace. TASK-0137: the Support team template.
const shot = async (page: Page, name: string, sel = 'body') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const T = {
  vi: { password: 'Mật khẩu', waiting: 'Đang chờ một workflow khác', calledBy: 'Được gọi bởi' },
  en: { password: 'Password', waiting: 'Waiting for another workflow', calledBy: 'Called by' },
}
/** A canvas node's run mark (TASK-0147). */
const nodeStatus = (page: Page, id: string) => page.locator(`.react-flow__node[data-id="${id}"] [data-status]`)
const STATE = [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }, { name: 'steps', type: 'list' }]
const DESK = (name: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('ask', 'human', 300, { label: 'Refund approval', prompt: 'Refund for {{state.message}}?', output_field: 'answer' }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ask' }, { id: 'e2', source: 'ask', target: 'end' }] })
const ORDERS = (name: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('x', 'llm', 300, { label: 'Look up the order', model: 'gpt-4o-mini', prompt: 'Where is {{state.message}}?', output_field: 'answer' }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'x' }, { id: 'e2', source: 'x', target: 'end' }] })
const EMPTY_TEAM = (name: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('ag', 'agent', 300, { label: 'Supervisor', model: 'gpt-4o-mini', prompt: 'Help the customer: {{state.message}}', output_field: 'answer', steps_field: 'steps', max_rounds: 5, tools: [] }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ag' }, { id: 'e2', source: 'ag', target: 'end' }] })
const TEAM = (name: string, desk: string) => ({ name, state: STATE,
  nodes: [N('start', 'start', 40), N('ag', 'agent', 300, { label: 'Supervisor', model: 'gpt-4o-mini', prompt: 'Help the customer: {{state.message}}', output_field: 'answer',
    steps_field: 'steps', max_rounds: 5, tools: [{ name: 'refund_desk', description: 'Questions about refunds', source: 'workflow', workflow_id: desk, inputs: ['message'], outputs: ['answer'] }] }),
  N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ag' }, { id: 'e2', source: 'ag', target: 'end' }] })

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', viewport: { width: 1440, height: 1000 } })
  test(`workflow tool: set up in the editor, the child's steps under the call (${lang})`, async ({ page }) => {
    await page.goto('/login'); await page.getByLabel(T[lang].password, { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }
    const n = Date.now() % 100000; const orders = `Order desk ${lang} ${n}`
    const desk = (await (await page.request.post('/api/workflows', { headers: H, data: ORDERS(orders) })).json()).data.id
    const team = (await (await page.request.post('/api/workflows', { headers: H, data: EMPTY_TEAM(`Order team ${lang} ${n}`) })).json()).data.id
    await page.goto(`/workflows/${team}${lang === 'en' ? '?theme=dark' : ''}`)
    await page.locator('.react-flow__node[data-id="ag"]').click()
    await page.locator('#agent-add-tool').click(); await page.locator('#agent-add-workflow').click()
    await expect(page.locator('#agent-tool-0-workflow-required')).toBeVisible()
    await page.locator('#agent-tool-0-workflow').click(); await page.getByRole('option', { name: orders }).click()
    // picking the workflow names the tool and chooses message in, answer out
    await expect(page.locator('#agent-tool-0-name')).toHaveValue(orders.toLowerCase().replace(/ /g, '_'))
    await expect(page.getByTestId('workflow-tool-field')).toHaveCount(3)
    await expect(page.locator('#agent-tool-0-in-message')).toBeChecked(); await expect(page.locator('#agent-tool-0-out-answer')).toBeChecked()
    await expect(page.locator('#agent-tool-0-out-steps')).not.toBeChecked()
    await shot(page, `workflow-tool-card-${lang}`, '#agent-tool-0')
    await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
    const saved = (await (await page.request.get(`/api/workflows/${team}`, { headers: H })).json()).data
    expect(saved.nodes.find((x: { id: string }) => x.id === 'ag').data.tools[0]).toMatchObject({ source: 'workflow', workflow_id: desk, inputs: ['message'], outputs: ['answer'] })

    // a run with the mock: the parent waits for the child, then goes on; the child's steps show under the tool call
    await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order B200"}')
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    // the steps the parent took on the server after its child mark the canvas too, End included
    for (const id of ['start', 'ag', 'end']) await expect(nodeStatus(page, id)).toHaveAttribute('data-status', 'done')
    const nested = page.getByTestId('child-steps')
    await expect(nested).toBeVisible(); await expect(nested.getByTestId('child-step')).toContainText('Look up the order')
    await shot(page, `workflow-tool-nested-trace-${lang}`, '#run-logs-panel')
    await nested.getByRole('link').click()
    await expect(page).toHaveURL(new RegExp(`/workflows/${desk}\\?run=`))
    await expect(page.locator('#trace-called-by')).toContainText(`Order team ${lang} ${n}`)
  })

  test(`Support team template: a supervisor and its two desks (${lang})`, async ({ page }) => {
    await page.goto('/login'); await page.getByLabel(T[lang].password, { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    await page.locator('#new-wf').click()
    const card = page.locator('[data-id=builtin-support-team]')
    await expect(card).toBeVisible(); await shot(page, `workflow-tool-template-card-${lang}`, '[data-id=builtin-support-team]')
    await card.locator('button').first().click()
    await expect(page).toHaveURL(/\/workflows\/[^/]+$/); await expect(page.locator('#validation-errors')).toHaveCount(0)
    await page.locator('.react-flow__node[data-id="agent"]').click()
    await expect(page.getByTestId('agent-tool')).toHaveCount(2)
    await expect(page.locator('#agent-tool-0-workflow')).toContainText('Order desk')  // made with it: "Support team · Order desk"
    await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "Where is my order B200?"}')
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    // the steps the parent took on the server after its child mark the canvas too, End included
    for (const id of ['start', 'agent', 'end']) await expect(nodeStatus(page, id)).toHaveAttribute('data-status', 'done')
    await shot(page, `workflow-tool-template-canvas-${lang}`, '.react-flow')
    await expect(page.getByTestId('child-steps')).toContainText('lookup_order')
    await shot(page, `workflow-tool-template-run-${lang}`, '#run-logs-panel')
  })

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
    // the canvas shows the opened run (TASK-0147): the supervisor waits, the End node has not run
    await expect(nodeStatus(page, 'ag')).toHaveAttribute('data-status', 'waiting'); await expect(nodeStatus(page, 'end')).toHaveCount(0)
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
    // the steps the parent took on the server after its child mark the canvas too, End included
    for (const id of ['start', 'ag', 'end']) await expect(nodeStatus(page, id)).toHaveAttribute('data-status', 'done')
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
