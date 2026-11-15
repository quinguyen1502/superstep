import { test, expect } from '@playwright/test'
import { login, SIMPLE } from './helpers'
// undo / redo in the editor.

test('delete → undo → redo, coalesced typing, one step per drag, unsaved marker', async ({ page }) => {
  const H = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: SIMPLE(`Undo ${Date.now()}`) })).json()).data.id
  await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  const undo = page.locator('#undo-btn'), redo = page.locator('#redo-btn'), reply = page.locator('.react-flow__node[data-id="reply"]')
  await expect(undo).toBeDisabled(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  // delete → undo → redo (keyboard and buttons)
  await reply.click(); await page.keyboard.press('Delete'); await expect(reply).toHaveCount(0)
  await expect(page.locator('#unsaved-badge')).toBeVisible()
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('ControlOrMeta+z'); await expect(reply).toHaveCount(1)
  await expect(page.locator('.react-flow__edge')).toHaveCount(2); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  await redo.click(); await expect(reply).toHaveCount(0)
  await page.keyboard.press('ControlOrMeta+Shift+z'); await expect(reply).toHaveCount(0)  // nothing more to redo
  await undo.click(); await expect(reply).toHaveCount(1); await expect(redo).toBeEnabled()
  // typing a label is one step; text-field Ctrl+Z stays native (no graph undo)
  await reply.click(); const label = page.locator('aside').last().locator('input').first()
  await label.fill(''); await label.pressSequentially('Answer bot', { delay: 20 }); await expect(reply).toContainText('Answer bot')
  await page.locator('.react-flow__pane').click(); await undo.click(); await expect(reply).toContainText('Reply'); await expect(undo).toBeDisabled()
  // a drag is one step
  const box = (await reply.boundingBox())!
  await page.mouse.move(box.x + 30, box.y + 20); await page.mouse.down()
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + 30 + i * 20, box.y + 20 + i * 10)
  await page.mouse.up(); const moved = (await reply.boundingBox())!; expect(moved.x).toBeGreaterThan(box.x + 100)
  await undo.click(); await expect.poll(async () => Math.round((await reply.boundingBox())!.x)).toBe(Math.round(box.x)); await expect(undo).toBeDisabled()
})
