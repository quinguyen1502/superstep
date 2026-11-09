import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { confirmDelete } from './confirm'
// command palette (Mod+K): fuzzy search, actions with shortcuts, add node in view, jump to node, open workflow, settings.

test('palette in the editor: add node, jump to node, run an action, open a workflow', async ({ page }) => {
  const H = await login(page); const stamp = Date.now()
  const wid = await newWorkflow(page, H, SIMPLE(`Palette ${stamp}`)); await newWorkflow(page, H, SIMPLE(`Palette other ${stamp}`))
  await page.goto(`/workflows/${wid}`); const nodes = page.locator('.react-flow__node'); await expect(nodes).toHaveCount(3)
  const input = page.getByTestId('palette-input'), items = page.getByTestId('palette-item')

  // fuzzy: "retr" finds the Retriever node type; Enter adds it in view, selected, as one undo step
  await page.keyboard.press('ControlOrMeta+k'); await expect(input).toBeFocused()
  await input.fill('retriever'); await expect(items.first()).toHaveAttribute('data-id', 'add:retriever'); await page.keyboard.press('Enter')
  await expect(page.getByTestId('command-palette')).toHaveCount(0); await expect(nodes).toHaveCount(4)
  await expect(page.locator('.react-flow__node.selected')).toHaveCount(1)
  await expect(page.locator('.react-flow__node.selected')).toBeInViewport()
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('ControlOrMeta+z'); await expect(nodes).toHaveCount(3)

  // jump to node by label; actions show their shortcut and run (cheat sheet)
  await page.keyboard.press('ControlOrMeta+k'); await input.fill('Reply')
  await page.locator('[data-testid=palette-item][data-id="node:reply"]').click(); await expect(page.getByTestId('command-palette')).toHaveCount(0)
  await expect(page.locator('.react-flow__node[data-id="reply"]')).toHaveClass(/selected/)
  await page.keyboard.press('ControlOrMeta+k'); await input.fill('cheat')
  const cheat = page.locator('[data-testid=palette-item][data-id="action:cheatsheet"]'); await expect(cheat.locator('kbd').first()).toBeVisible()
  await cheat.click(); await expect(page.locator('#shortcut-cheatsheet')).toBeVisible(); await page.keyboard.press('Escape')
  await page.keyboard.press('ControlOrMeta+k'); await input.fill('stop')
  await expect(page.locator('[data-testid=palette-item][data-id="action:stop"]')).toHaveAttribute('data-disabled', 'true')  // nothing running

  // open another workflow, then a settings page; Mod+K works while typing in a field
  await input.fill(`other ${stamp}`); await page.keyboard.press('Enter')
  await expect(page).not.toHaveURL(new RegExp(wid)); await expect(nodes).toHaveCount(3)
  await page.locator('.react-flow__node[data-id="reply"]').click(); await page.locator('aside').last().locator('input').first().focus()
  await page.keyboard.press('ControlOrMeta+k'); await input.fill('mcp'); await page.locator('[data-testid=palette-item][data-id="nav:settings:mcp"]').click()
  await expect(page).toHaveURL(/\/settings\/mcp$/)
})

test('palette on the workflow list: new workflow opens the template gallery; no match message', async ({ page }) => {
  await login(page)
  await page.keyboard.press('ControlOrMeta+k'); const input = page.getByTestId('palette-input'); await expect(input).toBeVisible()
  await expect(page.locator('[data-testid=palette-item][data-id^="action:"]')).toHaveCount(0)  // editor actions only in the editor
  await input.fill('zzqxv-nothing'); await expect(page.getByTestId('palette-item')).toHaveCount(0)
  await input.fill('templ'); await page.locator('[data-testid=palette-item][data-id="nav:new"]').click()
  await expect(page.locator('#template-gallery')).toBeVisible()
})

test('editor header: primary actions only; ⋯ menu with sections, shortcuts, palette entry and delete', async ({ page }) => {
  const H = await login(page); const name = `Menu ${Date.now()}`; const wid = await newWorkflow(page, H, SIMPLE(name))
  await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(3)
  for (const id of ['#save-btn', '#run-btn', '#undo-btn', '#redo-btn', '#more-btn']) await expect(page.locator(id)).toBeVisible()
  for (const id of ['#share-btn', '#versions-btn', '#api-btn', '#layout-btn']) await expect(page.locator(id)).toHaveCount(0)
  await page.locator('#more-btn').click(); const menu = page.locator('#more-menu')
  await expect(menu.locator('[role=separator]')).toHaveCount(3)
  await expect(page.locator('#layout-btn [data-slot=dropdown-menu-shortcut]')).toHaveText(/Shift\+L|⇧L/i)
  await expect(page.locator('#palette-btn [data-slot=dropdown-menu-shortcut]')).toHaveText(/Ctrl\+K|⌘K/i)
  await expect(menu.getByTestId('more-item').last()).toHaveAttribute('id', 'delete-wf-btn')
  await expect(page.locator('#delete-wf-btn')).toHaveAttribute('data-variant', 'destructive')
  await page.locator('#palette-btn').click(); await expect(page.getByTestId('palette-input')).toBeVisible(); await page.keyboard.press('Escape')
  await expect(page.getByTestId('command-palette')).toHaveCount(0)
  // the same action is in the palette (single source)
  await page.keyboard.press('ControlOrMeta+k'); await page.getByTestId('palette-input').fill('versions')
  await expect(page.locator('[data-testid=palette-item][data-id="action:versions"]')).toBeVisible(); await page.keyboard.press('Escape')
  await expect(page.getByTestId('command-palette')).toHaveCount(0)
  await page.locator('#more-btn').click(); await page.locator('#json-btn').click(); await expect(page.getByRole('dialog')).toContainText('"nodes"'); await page.keyboard.press('Escape')
  await page.locator('#more-btn').click(); await page.locator('#delete-wf-btn').click()
  await confirmDelete(page, name); await expect(page).toHaveURL(/\/workflows$/)
})
