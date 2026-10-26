import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// TASK-0119: the Support agent template's test cases pass with the mock model (one approves the refund, one rejects
// it), and the Tests panel adds a "tool called" check for an Agent node and its tool.

async function pick(page: Page, trigger: ReturnType<Page['locator']>, option: string) {
  await trigger.click(); await page.getByRole('option', { name: option, exact: true }).click()
}

test('agent tests: template cases pass, and a "tool called" check is added', async ({ page }) => {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  const H = { Authorization: `Bearer ${await apiToken(page)}` }
  const wid = (await (await page.request.post('/api/templates/builtin-support-agent/use', { headers: H, data: {} })).json()).data.id
  // without a knowledge base to pick here, the policy search tool goes; the cases never call it
  const wf = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
  for (const n of wf.nodes) if (n.type === 'agent') n.data.tools = n.data.tools.filter((t: { source: string }) => t.source !== 'knowledge')
  expect((await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).success).toBe(true)

  await page.goto(`/workflows/${wid}`)
  await page.locator('#tests-tab').click()
  await expect(page.getByTestId('test-row')).toHaveCount(3)
  await page.locator('#tests-mock').click()
  await page.locator('#tests-run-all').click()
  await expect(page.locator('#tests-summary')).toContainText('3 đạt, 0 không đạt', { timeout: 60_000 })

  // a new case: the Agent node is answered like a Human node, and its tool is checked by name
  await page.locator('#tests-add').click()
  const dlg = page.locator('#test-dialog')
  await dlg.locator('#test-name').fill('Tra đơn hàng A100')
  await dlg.locator('#test-input').fill('{"message": "Where is my order A100?"}')
  await expect(dlg.getByTestId('answers-node')).toContainText('Support agent')
  await dlg.getByTestId('check-add').click()
  const check = dlg.getByTestId('check-edit').nth(1)
  await pick(page, check.getByTestId('check-kind'), 'Gọi công cụ')
  await pick(page, check.getByTestId('check-agent'), 'Support agent')
  await pick(page, check.getByTestId('check-tool'), 'lookup_order')
  await expect(check.getByTestId('check-called')).toContainText('đã gọi')
  await dlg.locator('#test-save').click()
  await expect(dlg).toHaveCount(0)
  const cases = (await (await page.request.get(`/api/workflows/${wid}/tests`, { headers: H })).json()).data.items
  expect(cases.find((c: { name: string }) => c.name === 'Tra đơn hàng A100').checks[1]).toEqual({ kind: 'tool', node: 'agent', tool: 'lookup_order', called: true })

  await page.locator('#tests-run-all').click()
  await expect(page.locator('#tests-summary')).toContainText('4 đạt, 0 không đạt', { timeout: 60_000 })
  await page.getByTestId('test-row').filter({ hasText: 'Tra đơn hàng A100' }).click()
  await expect(page.getByTestId('check-row').nth(1)).toContainText('“Support agent” đã gọi lookup_order')

  // the Code tab: both languages have the Agent node's steps (TypeScript since TASK-0125)
  await page.locator('#code-tab').click()
  await page.locator('#code-export-language').click(); await page.locator('#code-export-language-python').click()
  await expect(page.locator('#code-file')).toHaveText(/^support_agent.*\.py$/, { timeout: 30_000 })
  await page.locator('#code-export-language').click(); await page.locator('#code-export-language-typescript').click()
  await expect(page.locator('#code-file')).toHaveText(/^support_agent.*\.ts$/, { timeout: 30_000 })
  await expect(page.locator('#code-download')).toBeEnabled()
})
