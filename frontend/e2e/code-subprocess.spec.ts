import { test, expect } from '@playwright/test'
import { login, N, newWorkflow } from './helpers'
import { vt } from './catalog'
// with STUDIO_CODE_RUNTIME=subprocess every place says the code is not isolated: the canvas node, the Code
// config, the mode picker, the trace row, a run warning, run history, the admin card and the audit log.
// Run with E2E_CODE_RUNTIME=subprocess (playwright.config.ts passes it to the API); skips in the default Docker mode.
const WF = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'out', type: 'string' }],
  nodes: [N('s', 'start', 40), N('c', 'tool', 300, { label: 'Shout', mode: 'code', code: 'def main(state):\n    return state["message"].upper()\n', output_field: 'out' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'c' }, { id: '2', source: 'c', target: 'e' }] })

test('subprocess runtime: every surface warns that code is not isolated', async ({ page }) => {
  const H = await login(page)
  const rt = (await (await page.request.get('/api/meta/runtime', { headers: H })).json()).data
  test.skip(rt.code_runtime !== 'subprocess', 'needs E2E_CODE_RUNTIME=subprocess')
  const wid = await newWorkflow(page, H, WF(`Host ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await expect(page.locator('.react-flow__node[data-id="c"] [data-testid="node-unisolated"]')).toHaveText(vt('code.notIsolatedNode'))
  await page.locator('.react-flow__node[data-id="c"] [data-testid="node-unisolated"]').hover()
  await expect(page.getByRole('tooltip')).toContainText(vt('code.notIsolatedTip'))
  await page.locator('.react-flow__node[data-id="c"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#code-not-isolated')).toContainText(vt('code.notIsolated'))
  await page.locator('#tool-mode').click(); await expect(page.getByRole('option', { name: /^Code \(Python/ }).getByTestId('mode-unisolated')).toBeVisible(); await page.keyboard.press('Escape')

  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(page.locator('#trace-code-unisolated')).toBeVisible()
  await expect(page.locator('.trace-row[data-span="c#1"] [data-testid="span-unisolated"]')).toHaveText('runtime: subprocess')
  await page.locator('#history-all').click()
  await expect(page.locator('[data-testid="history-unisolated"]').first()).toBeVisible()

  await page.goto('/settings/users')
  await expect(page.locator('#code-runtime-value')).toContainText(vt('code.notIsolatedShort'))
  await expect(page.locator('#code-runtime-risk')).toBeVisible()
  const audit = (await (await page.request.get('/api/admin/audit?q=code_runtime', { headers: H })).json()).data.items
  expect(audit.some((x: { action: string }) => x.action === 'system.code_runtime_subprocess')).toBe(true)
})
