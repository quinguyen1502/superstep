import { test, expect } from '@playwright/test'
import { login, newWorkflow, N, SIMPLE } from './helpers'
// copy / cut / paste / duplicate nodes, one undo step per paste, cross-workflow paste.

test('copy, paste, duplicate, cut and paste into another workflow', async ({ page }) => {
  const H = await login(page)
  const wf = SIMPLE(`Clip ${Date.now()}`)
  wf.nodes.splice(2, 0, N('fmt', 'llm', 430, { label: 'Format', model: 'gpt-4o-mini', prompt: 'x', output_field: 'answer' }))
  wf.edges = [{ id: 'e1', source: 'start', target: 'reply' }, { id: 'e2', source: 'reply', target: 'fmt' }, { id: 'e3', source: 'fmt', target: 'end' }]
  const wid = await newWorkflow(page, H, wf); const other = await newWorkflow(page, H, SIMPLE(`Clip target ${Date.now()}`))
  await page.goto(`/workflows/${wid}`); const nodes = page.locator('.react-flow__node'), edges = page.locator('.react-flow__edge')
  await expect(nodes).toHaveCount(4); await expect(edges).toHaveCount(3)

  // copy one node → paste twice (no id clash), undo is one step per paste
  await page.locator('.react-flow__node[data-id="reply"]').click()
  await page.keyboard.press('ControlOrMeta+c'); await expect(page.locator('#clip-notice')).toBeVisible()
  await page.keyboard.press('ControlOrMeta+v'); await expect(nodes).toHaveCount(5)
  await page.keyboard.press('ControlOrMeta+v'); await expect(nodes).toHaveCount(6)
  await expect(page.locator('.react-flow__node.selected')).toHaveCount(1)  // only the last paste is selected
  await page.keyboard.press('ControlOrMeta+z'); await expect(nodes).toHaveCount(5)
  await page.keyboard.press('ControlOrMeta+z'); await expect(nodes).toHaveCount(4)

  // Start/End are never copied; internal edges come along (reply → fmt), external ones do not
  await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.press('ControlOrMeta+d')
  await expect(nodes).toHaveCount(6); await expect(edges).toHaveCount(4)
  await page.keyboard.press('ControlOrMeta+z'); await expect(nodes).toHaveCount(4); await expect(edges).toHaveCount(3)

  // right-click a node for Duplicate
  await page.locator('.react-flow__pane').click(); await page.locator('.react-flow__node[data-id="fmt"]').click({ button: 'right' })
  await page.locator('#duplicate-node').click(); await expect(nodes).toHaveCount(5); await page.keyboard.press('ControlOrMeta+z')

  // cut two connected nodes, paste them into another workflow
  await page.locator('.react-flow__pane').click()
  await page.locator('.react-flow__node[data-id="reply"]').click(); await page.locator('.react-flow__node[data-id="fmt"]').click({ modifiers: ['ControlOrMeta'] })
  await page.keyboard.press('ControlOrMeta+x'); await expect(nodes).toHaveCount(2)
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  await page.goto(`/workflows/${other}`); await expect(nodes).toHaveCount(3)
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('ControlOrMeta+v')
  await expect(nodes).toHaveCount(5); await expect(edges).toHaveCount(3)
  await expect(page.locator('.react-flow__node', { hasText: 'Format' })).toHaveCount(1)
  await expect(page.locator('#unsaved-badge')).toBeVisible()
})

test('typing in a field keeps native copy/paste', async ({ page }) => {
  const H = await login(page); const wid = await newWorkflow(page, H, SIMPLE(`Clip input ${Date.now()}`))
  await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="reply"]').click()
  const label = page.locator('aside').last().locator('input').first()
  await label.focus(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.press('ControlOrMeta+c'); await page.keyboard.press('ControlOrMeta+v')
  await expect(page.locator('.react-flow__node')).toHaveCount(3)
})
