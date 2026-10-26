import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
// TASK-0121: phones (below 768px). The pages never scroll sideways; the editor shows one pane at a time with a tab bar
// at the bottom (Canvas · Nodes · Config · Run, plus Chat while it is open).
const PHONE = { width: 375, height: 812 }
const noSideScroll = async (page: Page) =>
  expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

test('Workflow list and Settings fit a phone', async ({ page }) => {
  await page.setViewportSize(PHONE)
  await login(page)
  await expect(page.locator('#wf-search')).toBeInViewport({ ratio: 1 })
  await expect(page.locator('#new-wf')).toBeInViewport({ ratio: 1 })
  await noSideScroll(page)
  await page.goto('/settings/profile')
  await expect(page.locator('#settings-profile')).toBeVisible()
  await noSideScroll(page)
  await page.locator('#settings-nav-teams').scrollIntoViewIfNeeded(); await page.locator('#settings-nav-teams').click()
  await expect(page).toHaveURL(/\/settings\/teams$/)
})

test('Editor on a phone: tab bar, tap to add a node, Config for the selection, Run and Chat panes', async ({ page }) => {
  await page.setViewportSize(PHONE)
  const H = await login(page); const wid = await newWorkflow(page, H, SIMPLE(`Phone ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  const tab = (id: string) => page.locator(`#mobile-tab-${id}`)
  await expect(tab('canvas')).toHaveAttribute('data-state', 'active')
  for (const id of ['run-btn', 'save-btn', 'more-btn']) await expect(page.locator(`#${id}`)).toBeInViewport({ ratio: 1 })
  await expect(page.locator('#step-btn')).toBeHidden()
  await expect(page.locator('#config-panel')).toBeHidden()
  await noSideScroll(page)

  // a tap on a node marks the Config tab; Config shows that node
  await page.locator('.react-flow__node', { hasText: 'Reply' }).click()
  await expect(page.getByTestId('mobile-config-dot')).toBeVisible()
  await tab('config').click()
  await expect(page.locator('#config-panel')).toBeVisible()
  await expect(page.locator('#llm-prompt')).toBeVisible()

  // Run switches to the Run pane: input above the logs
  await page.locator('#run-btn').click()
  await expect(tab('run')).toHaveAttribute('data-state', 'active')
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  const input = await page.locator('#run-input').boundingBox(); const trace = await page.locator('#trace-summary').boundingBox()
  expect(trace!.y).toBeGreaterThan(input!.y + input!.height)

  // Nodes: a tap adds the node in the middle of the canvas, selected
  await tab('nodes').click()
  await expect(page.locator('#palette-tap-hint')).toBeVisible()
  await page.locator('[data-testid=palette-card][data-type=human]').click()
  await expect(tab('canvas')).toHaveAttribute('data-state', 'active')
  await expect(page.locator('.react-flow__node')).toHaveCount(4)
  await expect(page.locator('.react-flow__node.selected')).toHaveCount(1)
  await tab('config').click(); await expect(page.locator('#human-prompt')).toBeVisible()

  // Chat opens as its own pane and closes back to the canvas
  await page.locator('#chat-open').click()
  await expect(tab('chat')).toHaveAttribute('data-state', 'active')
  await page.locator('#chat-open').click()
  await expect(tab('chat')).toHaveCount(0)
  await expect(tab('canvas')).toHaveAttribute('data-state', 'active')
  await noSideScroll(page)
})

test('From 768px the editor keeps its side-by-side panels', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 })
  const H = await login(page); const wid = await newWorkflow(page, H, SIMPLE(`Tablet ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await expect(page.locator('#run-input')).toBeVisible()
  await expect(page.locator('#mobile-editor')).toHaveCount(0)
  await expect(page.locator('#step-btn')).toBeVisible()
})
