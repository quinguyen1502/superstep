import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
// drag the palette, config and run-panel borders; sizes stay after a reload and in another
// workflow; minimums hold; the header stays 56px; a node drag on the canvas moves the node, not a panel.

const box = async (page: Page, sel: string) => (await page.locator(sel).first().boundingBox())!
const w = async (page: Page, sel: string) => Math.round((await box(page, sel)).width)
const h = async (page: Page, sel: string) => Math.round((await box(page, sel)).height)
async function drag(page: Page, sel: string, dx: number, dy: number) {
  const b = await box(page, sel); const x = b.x + b.width / 2, y = b.y + b.height / 2
  await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + dx, y + dy, { steps: 10 }); await page.mouse.up()
}
const sizes = async (page: Page) => ({ left: await w(page, '#panel-left'), right: await w(page, '#panel-right'), bottom: await h(page, '#panel-bottom') })
const near = (a: number, b: number) => expect(Math.abs(a - b)).toBeLessThanOrEqual(3)

test('drag the three borders, keep the sizes, respect the minimums', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 })
  const H = await login(page)
  const a = await newWorkflow(page, H, SIMPLE(`Resize A ${Date.now()}`)), b = await newWorkflow(page, H, SIMPLE(`Resize B ${Date.now()}`))
  await page.goto(`/workflows/${a}`); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  let s = await sizes(page); near(s.left, 250); near(s.right, 320); near(s.bottom, 300); expect(await h(page, 'header')).toBe(56)

  await drag(page, '#resize-left', 100, 0); await drag(page, '#resize-right', -80, 0); await drag(page, '#resize-bottom', 0, -60)
  s = await sizes(page); near(s.left, 350); near(s.right, 400); near(s.bottom, 360); expect(await h(page, 'header')).toBe(56)

  const node = '.react-flow__node[data-id="reply"]'; const before = await box(page, node)
  await drag(page, node, 60, 40)
  const after = await box(page, node); expect(after.x - before.x).toBeGreaterThan(40); expect(after.y - before.y).toBeGreaterThan(25)
  expect(await sizes(page)).toEqual(s)

  await page.reload(); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  const r = await sizes(page); near(r.left, 350); near(r.right, 400); near(r.bottom, 360)
  await page.goto(`/workflows/${b}`); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  const o = await sizes(page); near(o.left, 350); near(o.right, 400); near(o.bottom, 360)

  await drag(page, '#resize-left', -1000, 0); await drag(page, '#resize-bottom', 0, 1000)
  s = await sizes(page); near(s.left, 180); near(s.bottom, 140)
  await drag(page, '#resize-right', -3000, 0); await drag(page, '#resize-bottom', 0, -3000)
  expect(await w(page, '#panel-canvas')).toBeGreaterThanOrEqual(278); expect(await h(page, '#panel-main')).toBeGreaterThanOrEqual(158)
  expect(await h(page, 'header')).toBe(56)
  expect(JSON.parse(await page.evaluate(() => localStorage.getItem('lgs.editorPanels') || 'null'))).toMatchObject({ left: 180 })
})
