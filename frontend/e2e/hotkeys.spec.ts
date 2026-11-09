import { test, expect } from '@playwright/test'
import { login, SIMPLE } from './helpers'
// keyboard shortcuts in the editor and the cheat sheet.

test('save, run, delete with the keyboard; typing is safe; cheat sheet lists every shortcut', async ({ page }) => {
  const H = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: SIMPLE(`Keys ${Date.now()}`) })).json()).data.id
  await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  // Mod+S saves from inside the name field (no browser dialog)
  const renamed = `Keys renamed ${Date.now()}`
  await page.locator('header input').first().fill(renamed); await page.keyboard.press('ControlOrMeta+s')
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data.name).toBe(renamed)
  // Delete inside a text field edits text, not the graph
  await page.locator('.react-flow__node[data-id="reply"]').click()
  const label = page.locator('aside').last().locator('input').first(); await label.click(); await label.press('End'); await label.press('Backspace')
  await expect(page.locator('.react-flow__node')).toHaveCount(3)
  // Start/End are protected; a selected LLM node goes
  await page.locator('.react-flow__node[data-id="start"]').click(); await page.keyboard.press('Delete')
  await expect(page.locator('.react-flow__node[data-id="start"]')).toHaveCount(1)
  await page.locator('.react-flow__node[data-id="reply"]').click(); await page.keyboard.press('Delete')
  await expect(page.locator('.react-flow__node[data-id="reply"]')).toHaveCount(0)
  await expect(page.locator('.react-flow__edge')).toHaveCount(0)
  // Mod+Enter runs (start → end directly is invalid without edges; the run still starts and reports)
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('ControlOrMeta+Enter')
  await expect(page.locator('#run-tab')).toHaveAttribute('data-state', 'active')
  // ? opens the cheat sheet
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('Shift+?')
  const sheet = page.locator('#shortcut-cheatsheet'); await expect(sheet).toBeVisible()
  await expect(sheet.getByTestId('shortcut-row')).toHaveCount(19)
  await expect(sheet).toContainText(/Ctrl|⌘/); await expect(sheet).toContainText('Lưu workflow')
  await page.keyboard.press('Escape'); await expect(sheet).toHaveCount(0)
})
