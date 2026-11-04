import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// TASK-0041: `{{state.field}}` templates show as tags, `{{` suggests fields, the braces button inserts one, and the saved text is unchanged.
async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login'); await page.getByLabel('Email').fill(email); await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page, email, password)}` }
}
const n = (id: string, type: string, x: number, data: Record<string, unknown> = {}) => ({ id, type, position: { x, y: 120 }, data: { label: id, ...data } })
// CodeMirror ignores Enter for 75ms after the list opens (interactionDelay), so a picked option waits for that
async function pick(page: Page, label: string) {
  await expect(page.locator('.cm-tooltip-autocomplete li[aria-selected]')).toContainText(label); await page.waitForTimeout(150); await page.keyboard.press('Enter')
}
const WF = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }, { name: 'reply', type: 'string' }],
  nodes: [n('start', 'start', 40), n('ask', 'llm', 260, { model: 'gpt-4o-mini', prompt: 'Hi {{state.message}} {{state.ghost}}', output_field: 'answer' }),
    n('call', 'tool', 480, { mode: 'http', method: 'GET', url: '', body: '', output_field: 'reply' }), n('end', 'end', 700)],
  edges: [{ id: 'e1', source: 'start', target: 'ask' }, { id: 'e2', source: 'ask', target: 'call' }, { id: 'e3', source: 'call', target: 'end' }] })

test('template editor: tags, suggestions, insert menu, one-line URL, saved text, read-only viewer', async ({ page, browser }) => {
  const email = `tpl${Date.now()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  const auth = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: auth, data: WF(`Template ${Date.now()}`) })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click()
  const prompt = page.locator('#llm-prompt')
  await expect(prompt.locator('.template-tag[data-field="message"]')).toHaveAttribute('data-known', 'true')
  await expect(prompt.locator('.template-tag[data-field="ghost"]')).toHaveAttribute('data-known', 'false')  // not in the state schema

  // `{{` lists the state fields; Enter writes the whole reference
  await prompt.click(); await page.keyboard.press('ControlOrMeta+End'); await page.keyboard.type(' {{ans')
  await pick(page, 'answer')
  await expect(prompt.locator('.template-tag[data-field="answer"]')).toBeVisible()

  // the braces button inserts at the cursor; Backspace removes the whole tag
  // focus is back in the editor as soon as an item is picked: keys typed straight after go into the field, not to the canvas (TASK-0043)
  await page.locator('#llm-prompt-insert').click(); await page.getByRole('menuitem', { name: 'reply' }).click(); await page.keyboard.type('Z')
  await expect(prompt.locator('.template-tag[data-field="reply"]')).toBeVisible(); await expect(prompt).toContainText('replyZ')
  await page.keyboard.press('Backspace'); await page.keyboard.press('Backspace')
  await expect(prompt.locator('.template-tag[data-field="reply"]')).toHaveCount(0); await expect(page.locator('.react-flow__node[data-id="ask"]')).toBeVisible()

  // the URL stays on one line
  await page.locator('.react-flow__node[data-id="call"]').click(); await page.locator('#config-tab-settings').click()
  const url = page.locator('#http-url'); await url.click(); await page.keyboard.type('https://example.com/o/{{mes'); await pick(page, 'message')
  await page.keyboard.press('Enter'); await page.keyboard.type('x')
  await expect(url.locator('.cm-line')).toHaveCount(1); await expect(url.locator('.template-tag[data-field="message"]')).toBeVisible()

  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const nodes = (await (await page.request.get(`/api/workflows/${wid}`, { headers: auth })).json()).data.nodes
  const data = (id: string) => nodes.find((x: { id: string }) => x.id === id).data
  expect(data('ask').prompt).toBe('Hi {{state.message}} {{state.ghost}} {{state.answer}}')
  expect(data('call').url).toBe('https://example.com/o/{{state.message}} x')

  // a viewer sees the tags but cannot type or insert
  expect((await page.request.put(`/api/workflows/${wid}/shares`, { headers: auth, data: { email, role: 'viewer' } })).ok()).toBeTruthy()
  const ctx = await browser.newContext(); const other = await ctx.newPage(); await login(other, email, 'secret12')
  await other.goto(`/workflows/${wid}`); await expect(other.locator('#view-only')).toBeVisible()
  await other.locator('.react-flow__node[data-id="ask"]').click(); await other.locator('#config-tab-settings').click()
  await expect(other.locator('#llm-prompt')).toHaveAttribute('contenteditable', 'false')
  await expect(other.locator('#llm-prompt .template-tag[data-field="answer"]')).toBeVisible(); await expect(other.locator('#llm-prompt-insert')).toHaveCount(0)
  await ctx.close()
})
