import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import { vt, vin, vtHead } from './catalog'
// workflow tests. Add a test case with a Human answer and a check, Run all, see it pass; change the check,
// see it fail with the expected and actual values; the test runs show under History > Test runs only.
const APPROVAL = {
  name: `Tests e2e ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 260, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve {{state.message}}?', output_field: 'decision' } },
    { id: 'route', type: 'condition', position: { x: 500, y: 150 }, data: { label: 'Approved?', field: 'decision', default: 'rejected' } },
    { id: 'e', type: 'end', position: { x: 740, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'route' },
    { id: '3', source: 'route', target: 'e', label: 'approved' }, { id: '4', source: 'route', target: 'e', label: 'rejected' }],
}

async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel(vt('auth.password'), { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return apiToken(page)
}

async function pick(page: Page, trigger: ReturnType<Page['locator']>, option: string) {
  await trigger.click(); await page.getByRole('option', { name: option, exact: true }).click()
}

test('workflow tests: add a case, run all, see pass and fail with expected and actual', async ({ page }) => {
  const token = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: APPROVAL })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('#tests-tab').click()
  await expect(page.locator('#tests-panel')).toContainText(vt('tests.empty'))

  await page.locator('#tests-add').click()
  const dlg = page.locator('#test-dialog')
  await dlg.locator('#test-name').fill(vt('templates.builtin.builtin-refund-approval.name'))
  await dlg.locator('#test-input').fill('{"message": "order A100"}')
  await dlg.getByTestId('answer-add').click()  // Approve by default
  await dlg.getByTestId('check-add').click()
  const check = dlg.getByTestId('check-edit').nth(1)
  await pick(page, check.getByTestId('check-field'), 'decision')
  await check.getByTestId('check-value').fill('approved')
  await dlg.locator('#test-save').click()
  await expect(dlg).toHaveCount(0)

  await page.locator('#tests-run-all').click()
  const row = page.getByTestId('test-row').filter({ hasText: vt('templates.builtin.builtin-refund-approval.name') })
  await expect(row.getByTestId('test-status')).toHaveText(vt('tests.status.passed'), { timeout: 30_000 })
  await expect(page.locator('#tests-summary')).toContainText(vt('tests.summary', { passed: '1', failed: '0', version: '1' }))
  await expect(page.getByTestId('check-row')).toHaveCount(2)

  // the same case expecting "rejected" fails, and shows what it got
  await page.getByTestId('test-edit').click()
  await page.locator('#test-dialog').getByTestId('check-value').fill('rejected')
  await page.locator('#test-save').click()
  await page.locator('#tests-run-all').click()
  await expect(page.getByTestId('result-status')).toHaveText(vt('tests.status.failed'), { timeout: 30_000 })
  const failed = page.getByTestId('check-row').nth(1)
  await expect(failed).toContainText('rejected'); await expect(failed).toContainText('approved')

  // test runs stay out of the history unless asked for, and open in the trace
  await page.locator('#run-tab').click(); await page.locator('#history-all').click()
  await expect(page.getByTestId('history-row')).toHaveCount(0)
  await page.locator('#history-tests').click()
  await expect(page.getByTestId('history-row')).toHaveCount(2)
  await expect(page.getByTestId('history-source').first()).toHaveText('Test')
  await page.keyboard.press('Escape')
  await page.locator('#tests-tab').click()
  await page.getByTestId('result-open-run').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok')
})

// save a case from a run, change the graph so it fails, see Regression against v1, run against v1.
test('workflow tests: save as test case from a run, regression against the previous version, run against a version', async ({ page }) => {
  const token = await login(page); const H = { Authorization: `Bearer ${token}` }
  const wf = { ...APPROVAL, name: `Regression e2e ${Date.now()}` }
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order A100"}')
  await page.locator('#run-btn').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  await page.locator('#human-approve').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })

  await page.locator('#trace-save-test').click()
  const dlg = page.locator('#test-dialog'); await expect(dlg.locator('#test-name')).toHaveValue(/^Run /)
  await expect(dlg.getByTestId('answer-kind')).toHaveText(vt('approve.approve'))  // the answer the run was given
  await dlg.locator('#test-name').fill(vin('workflowTests.fromRun')); await dlg.locator('#test-save').click(); await expect(dlg).toHaveCount(0)
  await expect(page.locator('#tests-panel')).toBeVisible()
  await expect(page.getByTestId('test-row').filter({ hasText: vin('workflowTests.fromRun') })).toHaveClass(/bg-accent/)  // the new case is selected
  await page.locator('#tests-run-all').click()
  await expect(page.getByTestId('result-status')).toHaveText(vt('tests.status.passed'), { timeout: 30_000 })
  await expect(page.locator('#tests-no-baseline')).toBeVisible()

  // version 2 writes the answer to another field: the case now fails, marked as a regression against v1
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
  saved.nodes.find((n: { id: string }) => n.id === 'ask').data.output_field = 'message'
  await page.request.post('/api/workflows', { headers: H, data: saved })
  await page.reload(); await page.locator('#tests-tab').click(); await page.locator('#tests-run-all').click()
  await expect(page.getByTestId('result-status')).toHaveText(vt('tests.status.failed'), { timeout: 30_000 })
  await expect(page.getByTestId('result-change')).toHaveText(vt('tests.change.regression'))
  await expect(page.locator('#tests-compare')).toContainText(vt('tests.comparedWith', { version: 1 }).replace(/:$/, '')); await expect(page.getByTestId('compare-regression')).toContainText('1')

  // run against v1 again: it passes there, and the history lists the three suite runs
  await page.locator('#tests-run-version').click(); await page.getByTestId('run-version').filter({ hasText: 'v1' }).click()
  await expect(page.getByTestId('result-status')).toHaveText(vt('tests.status.passed'), { timeout: 30_000 })
  await expect(page.locator('#tests-summary')).toContainText('trên v1')
  await page.locator('#tests-history').click(); await expect(page.getByTestId('suite-row')).toHaveCount(3)
})

// a workflow made from a built-in template comes with its test cases, and they pass with the mock model.
test('workflow tests: a built-in template brings test cases that pass offline', async ({ page }) => {
  const token = await login(page)
  const wid = (await (await page.request.post('/api/templates/builtin-purchase-request/use', { headers: { Authorization: `Bearer ${token}` }, data: { name: `Purchase e2e ${Date.now()}` } })).json()).data.id
  await page.goto(`/workflows/${wid}`); await page.locator('#tests-tab').click()
  await expect(page.getByTestId('test-row')).toHaveCount(3)
  await page.locator('#tests-mock').click(); await page.locator('#tests-run-all').click()
  await expect(page.locator('#tests-summary')).toContainText(vtHead('tests.summary', { passed: 3, failed: 0 }), { timeout: 60_000 })
})
