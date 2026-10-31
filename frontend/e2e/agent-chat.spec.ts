import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
// TASK-0085 (REQ-0048 phase 1): the editor's Chat side panel. Multi-turn memory through the conversation field, a Human node
// answered by the person chatting (and one left to a reviewer), and the step visibility modes.
const STATE = [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }, { name: 'ok', type: 'string' }]
const ECHO = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: 'History:\n{{state.messages}}', output_field: 'reply' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
const ASK = (name: string, by: 'visitor' | 'reviewer') => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('ask', 'human', 260, { label: 'Confirm', prompt: 'Sure about {{state.message}}?', output_field: 'ok', answered_by: by }),
    N('bot', 'llm', 480, { label: 'Bot', model: 'gpt-4o-mini', prompt: 'Answer {{state.ok}}', output_field: 'reply' }), N('e', 'end', 700)],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'bot' }, { id: '3', source: 'bot', target: 'e' }] })

async function openChat(page: Page, wid: string) {
  await page.goto(`/workflows/${wid}`); await expect(page.locator('#chat-open')).toBeVisible()
  // the panel's open state is remembered in this browser, so open it only when it is closed
  if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
  await expect(page.locator('#chat-panel')).toBeVisible()
}
async function say(page: Page, text: string) {
  // the composer takes a message once the last one has settled (its saved answer read back): until then it shows Stop
  // and Enter does nothing, so a message typed while the reply is still being read would be lost (TASK-0209)
  await expect(page.locator('#chat-stop')).toHaveCount(0)
  await page.locator('#chat-input').fill(text); await page.keyboard.press('Enter')
  await expect(page.getByTestId('chat-mine').last()).toHaveText(text)
}
/** the chat's View as Select (Workflow builder / Chat visitor) */
const viewAs = async (page: Page, v: 'builder' | 'visitor') => { await page.locator('#chat-view').click(); await page.locator(`#chat-view-${v}`).click(); await expect(page.locator('[role=listbox], [role=menu]')).toHaveCount(0) }
const enable = (page: Page, H: Record<string, string>, wid: string, extra: Record<string, unknown> = {}) =>
  page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, ...extra } })

test('chat remembers the conversation across turns', async ({ page }) => {
  const H = await login(page); const wid = await newWorkflow(page, H, ECHO(`Chat ${Date.now()}`))
  await openChat(page, wid)
  await expect(page.locator('#chat-off')).toBeVisible()
  await page.locator('#chat-turn-on').click()
  await expect(page.locator('#chat-messages_field')).toContainText('messages')   // guessed from the state
  await page.locator('#chat-enabled').click(); await page.locator('#chat-settings-save').click()
  await expect(page.locator('#chat-settings')).toHaveCount(0)

  await say(page, 'hello one')
  await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  // the narrow panel picks sessions from a Select; fullscreen shows the session list
  await expect(page.locator('#chat-session-picker')).toContainText('hello one')
  await page.locator('#chat-fullscreen').click(); await expect(page.locator('#chat-side')).toHaveAttribute('data-fullscreen', 'true')
  await expect(page.getByTestId('chat-session').first()).toContainText('hello one')
  await say(page, 'and two')
  await expect(page.getByTestId('chat-answer')).toHaveCount(2, { timeout: 20_000 })
  const last = page.getByTestId('chat-answer').last()
  await expect(last).toHaveAttribute('data-status', 'ok'); await expect(last).toContainText('hello one'); await expect(last).toContainText('and two')

  // a new chat starts without memory; the old one stays in the list
  await page.locator('#chat-new').click(); await expect(page.locator('#chat-empty')).toBeVisible()
  await say(page, 'fresh start')
  await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  await expect(page.getByTestId('chat-answer').last()).not.toContainText('hello one')
  await expect(page.getByTestId('chat-session')).toHaveCount(2)
})

test('the person chatting answers a Human node in the chat; a reviewer step waits for Approvals', async ({ page }) => {
  const H = await login(page)
  const wid = await newWorkflow(page, H, ASK(`Ask ${Date.now()}`, 'visitor')); await enable(page, H, wid)
  await openChat(page, wid)
  await say(page, 'refund A1')
  await expect(page.locator('#chat-confirmation')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('chat-answer').last()).toContainText('Sure about refund A1?')
  await page.locator('#chat-approve').click()
  await expect(page.getByTestId('chat-mine').last()).toHaveText('approved')
  await expect(page.getByTestId('chat-answer').last()).toContainText('Answer approved', { timeout: 20_000 })
  await expect(page.locator('#chat-confirmation')).toHaveCount(0)
  await expect(page.locator('#chat-stop')).toHaveCount(0)   // settled: the saved thread keeps the answer (TASK-0209)
  await expect(page.getByTestId('chat-mine')).toHaveText(['refund A1', 'approved'])

  // a typed answer goes through the message box (Confirmation pattern + Prompt Input)
  await say(page, 'refund A2')
  await expect(page.locator('#chat-confirmation')).toBeVisible({ timeout: 20_000 })
  await say(page, 'only half')
  await expect(page.getByTestId('chat-answer').last()).toContainText('Answer only half', { timeout: 20_000 })

  // the node's "Answered by" option in the config panel
  await page.locator('.react-flow__node[data-id="ask"]').click()
  await expect(page.locator('#human-answered-by')).toContainText('Người chat')

  const rid = await newWorkflow(page, H, ASK(`Review ${Date.now()}`, 'reviewer')); await enable(page, H, rid)
  await openChat(page, rid)
  await say(page, 'refund B2')
  await expect(page.locator('#chat-waiting-reviewer')).toBeVisible({ timeout: 20_000 })
  await expect(page.locator('#chat-confirmation')).toHaveCount(0)
})

test('step visibility: builders see every step, visitors what the settings allow', async ({ page }) => {
  const H = await login(page); const wid = await newWorkflow(page, H, ECHO(`Steps ${Date.now()}`))
  await enable(page, H, wid, { steps: 'labels' })
  await openChat(page, wid)
  await say(page, 'hi')
  await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  const steps = page.getByTestId('chat-steps').last()
  await expect(steps).toHaveAttribute('data-mode', 'full'); await expect(steps.locator('[data-slot=trace-title]')).toHaveText(['Đã chạy Bot'])
  await steps.getByTestId('chat-step').click(); await expect(page.getByTestId('chat-step-detail')).toBeVisible()

  await viewAs(page, 'visitor')
  await expect(page.getByTestId('chat-steps').last()).toHaveAttribute('data-mode', 'labels')
  await expect(page.locator('[data-slot=trace-title]')).toHaveText(['Đã chạy Bot']); await expect(page.getByTestId('chat-step-detail')).toHaveCount(0)

  await enable(page, H, wid, { steps: 'none' })
  await viewAs(page, 'builder'); await viewAs(page, 'visitor')
  await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
  await expect(page.getByTestId('chat-steps')).toHaveCount(0)
})
