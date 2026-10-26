import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
// TASK-0049: For each node: the second edge drawn from it is labelled `done`, the panel offers list/item/index fields,
// and a run goes through the body once per item.
const WF = (name: string) => ({ name,
  state: [{ name: 'items', type: 'list' }, { name: 'item', type: 'string' }, { name: 'i', type: 'integer' }, { name: 'results', type: 'list', reducer: 'append' }],
  nodes: [N('s', 'start', 40), N('fe', 'foreach', 260, { label: 'Each order', items_field: 'items', item_field: 'item', index_field: 'i', max_items: 100 }),
    N('work', 'llm', 260, { label: 'Work', model: 'gpt-4o-mini', prompt: 'Item {{state.item}}', output_field: 'results' }, 300), N('e', 'end', 520)],
  edges: [{ id: '1', source: 's', target: 'fe' }, { id: '2', source: 'fe', target: 'work', label: 'each' }, { id: '3', source: 'work', target: 'fe' }] })

async function center(page: Page, sel: string) {
  const b = (await page.locator(sel).boundingBox())!; return { x: b.x + b.width / 2, y: b.y + b.height / 2 }
}

test('for each: connect done, configure, run once per item', async ({ page }) => {
  const H = await login(page)
  const wid = await newWorkflow(page, H, WF(`Loop ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)

  // the panel shows the loop fields
  await page.locator('.react-flow__node[data-id="fe"]').click()
  await expect(page.locator('#loop-hint')).toBeVisible()
  await page.locator('#config-tab-data').click(); await expect(page.locator('#loop-index')).toHaveText('i')  // TASK-0121 tabs
  await page.locator('#config-tab-execution').click(); await expect(page.locator('#loop-max')).toHaveValue('100')

  // draw the second edge: it becomes `done`
  const from = await center(page, '.react-flow__node[data-id="fe"] .react-flow__handle.source')
  const to = await center(page, '.react-flow__node[data-id="e"] .react-flow__handle.target')
  await page.mouse.move(from.x, from.y); await page.mouse.down(); await page.mouse.move(to.x, to.y, { steps: 12 }); await page.mouse.up()
  const done = page.locator('.react-flow__edge-text', { hasText: 'done' })
  await expect(done).toHaveCount(1)
  await done.click({ force: true })
  await expect(page.locator('#loop-edge')).toContainText('done')

  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
  expect(saved.edges.filter((e: { source: string }) => e.source === 'fe').map((e: { label: string }) => e.label).sort()).toEqual(['done', 'each'])

  // three items: the body runs three times, the fourth visit leaves the loop
  await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"items": ["A1", "B2", "C3"]}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  for (const k of ['work#1', 'work#2', 'work#3', 'fe#4']) await expect(page.locator(`.trace-row[data-span="${k}"]`)).toHaveCount(1)
  await expect(page.locator('.trace-row[data-span="work#4"]')).toHaveCount(0)
})
