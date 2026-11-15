import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
// auto-layout (Shift+L / toolbar), LR and TB, no overlaps, one undo step.

const boxes = (page: Page) => page.locator('.react-flow__node').evaluateAll(els => els.map(e => { const r = e.getBoundingClientRect(); return { id: e.getAttribute('data-id')!, x: r.x, y: r.y, w: r.width, h: r.height } }))
const overlap = (b: { x: number; y: number; w: number; h: number }[]) => b.some((a, i) => b.slice(i + 1).some(c => a.x < c.x + c.w && c.x < a.x + a.w && a.y < c.y + c.h && c.y < a.y + a.h))

test('tidy up a pile of nodes left→right and top→bottom, undo in one step', async ({ page }) => {
  const H = await login(page)
  const llm = (id: string) => N(id, 'llm', 200, { model: 'gpt-4o-mini', prompt: 'x', output_field: 'answer' }, 200)
  const wid = await newWorkflow(page, H, { name: `Layout ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 200, {}, 200), llm('a'), llm('b'), llm('c'), N('end', 'end', 200, {}, 200)],
    edges: [{ id: 'e1', source: 'start', target: 'a' }, { id: 'e2', source: 'a', target: 'b' }, { id: 'e3', source: 'a', target: 'c' }, { id: 'e4', source: 'b', target: 'end' }, { id: 'e5', source: 'c', target: 'end' }] })
  await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(5)
  expect(overlap(await boxes(page))).toBe(true)
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('Shift+L'); await page.waitForTimeout(500)
  let b = Object.fromEntries((await boxes(page)).map(x => [x.id, x]))
  expect(overlap(Object.values(b))).toBe(false); expect(b.start.x).toBeLessThan(b.a.x); expect(b.a.x).toBeLessThan(b.end.x)
  await expect(page.locator('#unsaved-badge')).toBeVisible()
  await page.keyboard.press('ControlOrMeta+z'); await page.waitForTimeout(300); expect(overlap(await boxes(page))).toBe(true)
  await page.locator('#more-btn').click(); await page.locator('#layout-tb').click(); await page.waitForTimeout(500)
  b = Object.fromEntries((await boxes(page)).map(x => [x.id, x]))
  expect(overlap(Object.values(b))).toBe(false); expect(b.start.y).toBeLessThan(b.a.y); expect(b.a.y).toBeLessThan(b.end.y)
  await page.keyboard.press('ControlOrMeta+z'); await page.waitForTimeout(300)
  await page.locator('#more-btn').click(); await page.locator('#layout-btn').click(); await page.waitForTimeout(500)  // remembers TB
  b = Object.fromEntries((await boxes(page)).map(x => [x.id, x])); expect(b.start.y).toBeLessThan(b.end.y)
})
