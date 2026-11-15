import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { vt } from './catalog'
// Editor polish: right-click on the canvas adds a node or a note where you clicked; the node palette and the state
// schema scroll on their own, so a long node list never hides the schema.

test('right-click the canvas to add a node; the state schema stays in view', async ({ page }) => {
  const H = await login(page)
  const wf = SIMPLE(`Canvas menu ${Date.now()}`)
  wf.state.push(...Array.from({ length: 10 }, (_, i) => ({ name: `field_${i}`, type: 'string' })))
  const wid = await newWorkflow(page, H, wf)
  await page.goto(`/workflows/${wid}`); const nodes = page.locator('.react-flow__node')
  await expect(nodes).toHaveCount(3)

  // Each tab uses the whole panel; the schema action remains in view.
  await expect(page.locator('#palette-nodes')).toBeInViewport()
  await page.locator('#palette-state-tab').click()
  await expect(page.locator('#palette-state').getByRole('button', { name: vt('editor.addField') })).toBeInViewport()

  await page.locator('#palette-nodes-tab').click()
  const pane = page.locator('.react-flow__pane'); const box = (await pane.boundingBox())!
  await pane.click({ button: 'right', position: { x: 80, y: box.height - 80 } })
  await page.locator('#pane-insert').hover(); await page.locator('#pane-insert-llm').click()
  await expect(nodes).toHaveCount(4)
  await expect(page.locator('.react-flow__node.selected')).toHaveAttribute('data-id', /^llm_/)
  await page.keyboard.press('ControlOrMeta+z'); await expect(nodes).toHaveCount(3)

  await pane.click({ button: 'right', position: { x: 80, y: box.height - 80 } })
  await page.locator('#add-note').click()
  await expect(page.locator('.react-flow__node-note')).toHaveCount(1)
})
