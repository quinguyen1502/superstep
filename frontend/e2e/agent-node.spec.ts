import { test, expect, type Page } from '@playwright/test'
import { apiToken, N } from './helpers'
import { expectRowAligned } from './helpers/alignment'
// TASK-0118: configure an Agent node (tools from two sources, approval settings), see the validator's errors, run it with
// the offline mock and read its rounds in the trace. Approving a tool call during the run comes with TASK-0117.
const shot = async (page: Page, name: string, sel = '#config-panel') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const T = {
  vi: { password: 'Mật khẩu', urlMissing: /chưa có URL/, round: 'Vòng 1', calls: 'gọi lookup_order', up: 'Đưa http_request lên', down: 'Đưa http_request xuống' },
  en: { password: 'Password', urlMissing: /URL is missing/, round: 'Round 1', calls: 'calls lookup_order', up: 'Move http_request up', down: 'Move http_request down' },
}
const AGENT = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }, { name: 'steps', type: 'list' }],
  nodes: [N('start', 'start', 40), N('ag', 'agent', 300, { label: 'Helper', model: 'gpt-4o-mini', prompt: 'Help the customer: {{state.message}}', output_field: 'answer', max_rounds: 5, tools: [] }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'ag' }, { id: 'e2', source: 'ag', target: 'end' }] })

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', viewport: { width: 1440, height: 1000 } })
  test(`agent node: tools, validation, mock run with rounds (${lang})`, async ({ page }) => {
    await page.goto('/login'); await page.getByLabel(T[lang].password, { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }
    const wid = (await (await page.request.post('/api/workflows', { headers: H, data: AGENT(`Agent e2e ${lang} ${Date.now() % 100000}`) })).json()).data.id
    await page.goto(`/workflows/${wid}${lang === 'en' ? '?theme=dark' : ''}`)  // screenshots in both themes
    await page.locator('.react-flow__node[data-id="ag"]').click()
    await expect(page.locator('#agent-settings')).toBeVisible()
    await expect(page.locator('#agent-no-tools')).toBeVisible()

    // a built-in function: picking it names the tool and copies its description
    await page.locator('#agent-add-tool').click(); await page.locator('#agent-add-builtin').click()
    await page.locator('#agent-tool-0-function').click(); await page.getByRole('option', { name: 'lookup_order' }).click()
    await expect(page.locator('#agent-tool-0-name')).toHaveValue('lookup_order')
    await expect(page.locator('#agent-tool-0-description')).not.toHaveValue('')
    // an HTTP tool without a URL: saving reports it; the approval switch shows the approval settings
    await page.locator('#agent-add-tool').click(); await page.locator('#agent-add-http').click()
    await expect(page.getByTestId('agent-tool')).toHaveCount(2)
    await page.locator('#agent-tool-1-approval').click()
    await expect(page.locator('#human-approval')).toBeVisible(); await expect(page.locator('#human-deadline')).toBeVisible()
    await page.locator('#agent-tool-1-add-param').click()
    const param = page.getByTestId('agent-param').first()
    await expectRowAligned([param.getByRole('textbox').first(), param.getByRole('combobox'), param.getByRole('button').first()], { label: 'parameter row' })
    await shot(page, `agent-settings-${lang}`)
    await page.locator('#save-btn').click()
    await expect(page.getByText(T[lang].urlMissing)).toBeVisible()  // in the UI language since TASK-0132
    await page.locator('#agent-tool-1-url').click(); await page.keyboard.type('https://example.com/refund')
    await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
    const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
    const tools = saved.nodes.find((n: { id: string }) => n.id === 'ag').data.tools
    expect(tools.map((t: { name: string; source: string; approval?: boolean }) => [t.name, t.source, !!t.approval])).toEqual([['lookup_order', 'builtin', false], ['http_request', 'http', true]])
    // moving a tool moves its card's own state (the parameter rows) with it
    await page.locator('#agent-tool-1').getByRole('button', { name: T[lang].up }).click()
    await expect(page.locator('#agent-tool-0-name')).toHaveValue('http_request')
    await expect(page.locator('#agent-tool-0-params').getByTestId('agent-param')).toHaveCount(1)
    await expect(page.locator('#agent-tool-1-params')).toHaveCount(0)
    await page.locator('#agent-tool-0').getByRole('button', { name: T[lang].down }).click()
    await expect(page.locator('#agent-tool-1-name')).toHaveValue('http_request')

    // the offline mock calls the closest tool once, then answers: a round on the trace with the tool call
    await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "Where is order B200?"}')
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    const model = page.locator('.trace-row[data-span="ag/__model#1"]')
    await expect(model.getByTestId('span-round')).toHaveText(T[lang].round)
    await expect(model.getByTestId('span-agent')).toHaveText(T[lang].calls)
    await expect(page.locator('.trace-row[data-span="ag/__tool#1"]').getByTestId('span-agent')).toContainText('lookup_order → ')
    await shot(page, `agent-trace-${lang}`, '#trace-timeline')
    await page.locator('.trace-row[data-span="ag/__tool#1"]').click()
    await expect(page.locator('#trace-detail')).not.toContainText('agent:ag')  // the conversation stays hidden
    await shot(page, `agent-trace-detail-${lang}`, '#trace-detail')
  })
})
