import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
// TASK-0121: every node's Config has the same tabs in the same order (Settings · Data · Execution). A tab the node does
// not use is disabled in place, the chosen tab is kept across nodes, and a tab that needs attention shows a dot.
const WF = (name: string) => ({ name,
  state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }, { name: 'steps', type: 'list' }],
  nodes: [N('start', 'start', 40),
    N('ag', 'agent', 280, { label: 'Helper', model: 'gpt-4o-mini', prompt: 'Help: {{state.message}}', output_field: 'answer',
      tools: [{ source: 'builtin', function: 'get_weather', name: 'get_weather', description: 'Weather' }] }),
    N('llm', 'llm', 520, { label: 'Draft', model: 'gpt-4o-mini', prompt: 'Draft {{state.message}}' }),
    N('route', 'condition', 760, { field: 'answer' }), N('end', 'end', 1000)],
  edges: [{ id: 'e1', source: 'start', target: 'ag' }, { id: 'e2', source: 'ag', target: 'llm' }, { id: 'e3', source: 'llm', target: 'route' }, { id: 'e4', source: 'route', target: 'end' }] })

const pick = (page: Page, id: string) => page.locator(`.react-flow__node[data-id="${id}"]`).click()
const tab = (page: Page, k: string) => page.locator(`#config-tab-${k}`)

test('Config tabs: same order for every node, kept across nodes, disabled in place, issue dot', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 960 })
  const H = await login(page); const wid = await newWorkflow(page, H, WF(`Tabs ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)

  await pick(page, 'ag')
  await expect(page.locator('#config-tabs [role=tab]')).toHaveText(['Cài đặt', 'Dữ liệu', 'Thực thi'])
  await expect(tab(page, 'settings')).toHaveAttribute('data-state', 'active')
  await expect(page.locator('#agent-settings')).toBeVisible(); await expect(page.locator('#agent-output')).toHaveCount(0)
  await tab(page, 'data').click()
  await expect(page.locator('#agent-output')).toBeVisible(); await expect(page.locator('#agent-steps-field')).toBeVisible()
  await expect(page.locator('#node-input-message')).toBeVisible()
  await tab(page, 'execution').click()
  await expect(page.locator('#agent-max-rounds')).toBeVisible(); await expect(page.locator('#node-retry-attempts')).toBeVisible()

  // another node opens on the same tab; the LLM without an output field marks Data
  await pick(page, 'llm')
  await expect(tab(page, 'execution')).toHaveAttribute('data-state', 'active')
  await expect(page.locator('#node-timeout')).toBeVisible()
  await expect(tab(page, 'data').getByTestId('config-tab-issue')).toBeVisible()
  await expect(tab(page, 'settings').getByTestId('config-tab-issue')).toHaveCount(0)

  // Condition has no execution settings: the tab stays, disabled, and Settings shows; the choice is still Execution
  await pick(page, 'route')
  await expect(page.locator('#config-tabs [role=tab]')).toHaveCount(3)
  await expect(tab(page, 'execution')).toBeDisabled()
  await expect(tab(page, 'settings')).toHaveAttribute('data-state', 'active')
  await pick(page, 'llm'); await expect(tab(page, 'execution')).toHaveAttribute('data-state', 'active')

  // Start has nothing to set beyond its label
  await pick(page, 'start')
  for (const k of ['settings', 'data', 'execution']) await expect(tab(page, k)).toBeDisabled()
  await expect(page.locator('#config-nothing')).toBeVisible()

  // a Data choice is saved like before
  await pick(page, 'llm'); await tab(page, 'data').click()
  await page.locator('#config-pane-data').getByRole('combobox').first().click(); await page.getByRole('option', { name: 'answer', exact: true }).click()
  await expect(tab(page, 'data').getByTestId('config-tab-issue')).toHaveCount(0)
})
