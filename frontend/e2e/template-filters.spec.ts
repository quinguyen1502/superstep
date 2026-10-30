import { test, expect } from '@playwright/test'
import { login } from './helpers'
// TASK-0044: template paths and filters: `|` suggests filters, tags show the chain, a bad filter is marked and refused on save,
// double-click turns a tag back into text, and a run renders the result.
const WF = (name: string) => ({ name, state: [{ name: 'order', type: 'object' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 120 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 280, y: 120 }, data: { label: 'Ask', prompt: 'Refund {{state.order.id}}?', output_field: 'decision' } },
    { id: 'e', type: 'end', position: { x: 520, y: 120 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'e' }] })

test('template filters: suggestions, tags, bad filter, edit as text, rendered run', async ({ page }) => {
  const auth = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: auth, data: WF(`Filters ${Date.now()}`) })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click()
  const prompt = page.locator('#human-prompt')
  await expect(prompt.locator('.template-tag')).toHaveText('order.id')

  // `|` lists the filters; the tag shows the whole chain
  await prompt.click(); await page.keyboard.press('ControlOrMeta+End'); await page.keyboard.type(' {{state.order.note | def')
  await expect(page.locator('.cm-tooltip-autocomplete li[aria-selected]')).toContainText('default'); await page.waitForTimeout(150)  // interactionDelay
  await page.keyboard.press('Enter'); await page.keyboard.type('none'); await page.keyboard.press('End'); await page.keyboard.type(' | upper}}')
  await expect(prompt.locator('.template-tag').nth(1)).toHaveText('order.note | default("none") | upper')
  await expect(prompt.locator('.template-tag').nth(1)).toHaveAttribute('data-known', 'true')

  // an unknown filter is marked and the save reports it
  await page.keyboard.type(' {{state.order.id | shout}}')
  await expect(prompt.locator('.template-tag').nth(2)).toHaveAttribute('data-known', 'false')
  await page.locator('#save-btn').click()
  await expect(page.getByText("không có filter 'shout'").first()).toBeVisible()

  // double-click turns the tag back into text; fix it, leave, and it is a tag again
  await prompt.locator('.template-tag').nth(2).dblclick()
  await expect(prompt).toContainText('{{state.order.id | shout}}')
  for (let i = 0; i < 'shout'.length; i++) await page.keyboard.press('Backspace')
  await page.keyboard.type('trim'); await page.keyboard.press('ControlOrMeta+Home')
  await expect(prompt.locator('.template-tag')).toHaveCount(3); await expect(prompt.locator('.template-tag').nth(2)).toHaveText('order.id | trim')
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: auth })).json()).data
  expect(saved.nodes.find((n: { id: string }) => n.id === 'ask').data.prompt).toBe('Refund {{state.order.id}}? {{state.order.note | default("none") | upper}} {{state.order.id | trim}}')

  // the run renders paths and filters
  await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"order": {"id": " A7 "}}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#human-question')).toHaveText('Refund  A7 ? NONE A7', { timeout: 30_000 })
})
